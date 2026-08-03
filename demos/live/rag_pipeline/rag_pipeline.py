"""
RAG Pipeline: Local Vector Search with ChromaDB and Ollama
==========================================================
Fully local RAG — no external APIs, no costs, full data privacy.

Prerequisites:
  uv sync
  ollama pull llama3.1:8b
  ollama pull nomic-embed-text
"""

import argparse
from pathlib import Path

import httpx
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# --- Configuration ---
BOOKS_DIR = "./books"
CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "old_books"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 4
LLM_MODEL = "llama3.1:8b"
EMBEDDING_MODEL = "nomic-embed-text"
OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MAX_FILES = 20
CHROMA_BATCH_SIZE = 500


class OllamaEmbeddings(Embeddings):
    """
    Calls Ollama /api/embeddings one text at a time.
    Avoids the batch-decode error that encoder-only models (nomic-embed-text)
    trigger when Ollama receives a batch request.
    """

    def __init__(self, model: str = EMBEDDING_MODEL, base_url: str = OLLAMA_BASE_URL):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def _embed_one(self, text: str) -> list[float]:
        r = httpx.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model, "prompt": text},
            timeout=120.0,
        )
        r.raise_for_status()
        return r.json()["embedding"]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        results = []
        for i, text in enumerate(texts, 1):
            print(f"    chunk {i}/{len(texts)}", end="\r", flush=True)
            results.append(self._embed_one(text))
        print(f"    {len(texts)} chunks embedded   ")
        return results

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)


# --- Vectorstore ---

INGESTED_LOG = Path(CHROMA_DIR) / ".ingested_files.txt"


def get_or_create_vectorstore(embedding_fn: Embeddings) -> Chroma:
    Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_DIR,
        embedding_function=embedding_fn,
    )


def get_ingested_sources() -> set:
    if not INGESTED_LOG.exists():
        return set()
    return set(INGESTED_LOG.read_text().splitlines())


def mark_ingested(path: Path):
    with open(INGESTED_LOG, "a") as f:
        f.write(str(path) + "\n")


# --- Ingest ---

def ingest(directory: str, vectorstore: Chroma, max_files: int | None = DEFAULT_MAX_FILES):
    """Load, chunk, embed, and store docs — skipping already-ingested files."""
    all_paths = sorted(Path(directory).rglob("*.txt"))
    ingested = get_ingested_sources()
    pending = [p for p in all_paths if str(p) not in ingested]

    if max_files is not None:
        pending = pending[:max_files]

    print(f"Files: {len(all_paths)} total | {len(ingested)} already ingested | {len(pending)} to process")
    if not pending:
        print("Nothing new to ingest.")
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    for i, path in enumerate(pending, 1):
        text = path.read_text(encoding="utf-8", errors="ignore")
        doc = Document(page_content=text, metadata={"source": str(path)})
        chunks = splitter.split_documents([doc])
        print(f"[{i}/{len(pending)}] {path.name}  ({len(chunks)} chunks)")
        for start in range(0, len(chunks), CHROMA_BATCH_SIZE):
            vectorstore.add_documents(chunks[start : start + CHROMA_BATCH_SIZE])
        mark_ingested(path)

    print(f"\nDone. {len(pending)} files ingested this run.")


# --- RAG chain ---

_PROMPT = ChatPromptTemplate.from_template(
    "Use only the context below to answer the question.\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}"
)


def build_chain(vectorstore: Chroma, model: str = LLM_MODEL, k: int = TOP_K):
    llm = ChatOllama(model=model, temperature=0)
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    return (
        RunnableParallel(context=retriever, question=RunnablePassthrough())
        | RunnablePassthrough.assign(
            result=(
                RunnablePassthrough.assign(
                    context=lambda x: "\n\n".join(d.page_content for d in x["context"])
                )
                | _PROMPT
                | llm
                | StrOutputParser()
            )
        )
    )


def search_similar(vectorstore: Chroma, query: str, k: int = TOP_K):
    results = vectorstore.similarity_search(query, k=k)
    print(f"\nQuery: {query}")
    for i, doc in enumerate(results):
        print(f"--- Chunk {i+1} (from {doc.metadata.get('source', '?')}) ---")
        print(doc.page_content[:300])
        print()
    return results


def ask(chain, query: str):
    print(f"\nQuestion: {query}")
    print("-" * 60)
    response = chain.invoke(query)
    print(f"\nAnswer:\n{response['result']}")
    sources = [d.metadata.get("source", "unknown") for d in response["context"]]
    print(f"\nSources: {sources}")
    return response


# --- Main ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest books into local ChromaDB")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Process all files")
    group.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES,
                       help=f"Max files to ingest per run (default: {DEFAULT_MAX_FILES})")
    args = parser.parse_args()

    max_files = None if args.all else args.max_files

    embedding_fn = OllamaEmbeddings()
    vectorstore = get_or_create_vectorstore(embedding_fn)
    ingest(BOOKS_DIR, vectorstore, max_files=max_files)
    print("Ingestion complete. Run interactive.py to query.")
