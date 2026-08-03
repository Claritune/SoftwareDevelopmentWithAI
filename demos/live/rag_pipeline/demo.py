"""
RAG Pipeline Demo — Alice in Wonderland
========================================
Step-by-step walkthrough of a full RAG pipeline:
  1. Load & inspect the source text
  2. Chunk the text
  3. Embed the chunks
  4. Store embeddings in ChromaDB
  5. Semantic search + RAG answer

Run: uv run python demo.py
"""

import sys
import textwrap
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

# ── Config ──────────────────────────────────────────────────────────────────
BOOK_PATH      = Path("./books/alice.txt")
CHROMA_DIR     = "./chroma_db_alice"
COLLECTION     = "alice_in_wonderland"
CHUNK_SIZE     = 500
CHUNK_OVERLAP  = 80
EMBED_MODEL    = "nomic-embed-text"
LLM_MODEL      = "llama3.1:8b"
OLLAMA_URL     = "http://localhost:11434"
TOP_K          = 4
DEMO_CHUNKS    = 3   # how many chunk examples to print
DEMO_EMBEDS    = 2   # how many embedding examples to print
EMBED_PREVIEW  = 8   # how many dimensions to show per embedding


# ── Helpers ──────────────────────────────────────────────────────────────────

def pause(label: str = ""):
    sep = "─" * 60
    print(f"\n{sep}")
    if label:
        print(f"  Next: {label}")
    print(sep)
    input("  Press ENTER to continue…\n")


def header(title: str):
    width = 60
    print("\n" + "═" * width)
    print(f"  {title}")
    print("═" * width)


def wrap(text: str, width: int = 72, indent: int = 4) -> str:
    prefix = " " * indent
    return textwrap.fill(text, width=width, initial_indent=prefix,
                         subsequent_indent=prefix)


# ── Embeddings ───────────────────────────────────────────────────────────────

class OllamaEmbeddings(Embeddings):
    def __init__(self, model: str = EMBED_MODEL, base_url: str = OLLAMA_URL):
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
            print(f"    embedding chunk {i}/{len(texts)} …", end="\r", flush=True)
            results.append(self._embed_one(text))
        print(f"    {len(texts)} chunks embedded.          ")
        return results

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)


# ── Steps ────────────────────────────────────────────────────────────────────

def step1_load(path: Path) -> str:
    header("STEP 1 — Load the source text")
    print(f"  File : {path}")
    text = path.read_text(encoding="utf-8", errors="ignore")
    chars = len(text)
    words = len(text.split())
    lines = text.count("\n")
    print(f"  Size : {chars:,} characters  |  {words:,} words  |  {lines:,} lines")
    print("\n  First 400 characters:")
    print("  " + "·" * 56)
    for line in text[:400].splitlines():
        print(f"  {line}")
    print("  " + "·" * 56)
    return text


def step2_chunk(text: str) -> list[Document]:
    header("STEP 2 — Split into chunks")
    print(f"  Strategy : RecursiveCharacterTextSplitter")
    print(f"  chunk_size={CHUNK_SIZE}  |  chunk_overlap={CHUNK_OVERLAP}")

    doc = Document(page_content=text, metadata={"source": str(BOOK_PATH)})
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    chunks = splitter.split_documents([doc])

    print(f"\n  Total chunks produced : {len(chunks)}")
    print(f"  Avg chunk length      : {sum(len(c.page_content) for c in chunks)//len(chunks)} chars")

    print(f"\n  ── Sample chunks (showing {DEMO_CHUNKS}) ──")
    for i in [0, len(chunks)//2, len(chunks)-1][:DEMO_CHUNKS]:
        ch = chunks[i]
        print(f"\n  Chunk #{i+1}  ({len(ch.page_content)} chars)")
        print("  " + "·" * 56)
        print(wrap(ch.page_content[:300]))
        if len(ch.page_content) > 300:
            print("    [… truncated …]")
        print("  " + "·" * 56)

    return chunks


def step3_embed(chunks: list[Document]) -> tuple[OllamaEmbeddings, list[list[float]]]:
    header("STEP 3 — Generate embeddings")
    print(f"  Model : {EMBED_MODEL}  (via Ollama at {OLLAMA_URL})")
    print(f"  Each chunk → a vector of floats (semantic fingerprint)")
    print(f"\n  Embedding {len(chunks)} chunks — this may take a minute…\n")

    emb_fn = OllamaEmbeddings()
    texts = [c.page_content for c in chunks]
    vectors = emb_fn.embed_documents(texts)

    dims = len(vectors[0])
    print(f"\n  Vector dimensions : {dims}")
    print(f"\n  ── Sample embeddings (showing {DEMO_EMBEDS} chunks) ──")
    for i in range(min(DEMO_EMBEDS, len(vectors))):
        v = vectors[i]
        preview = ", ".join(f"{x:.4f}" for x in v[:EMBED_PREVIEW])
        print(f"\n  Chunk #{i+1} → [{preview}, …]  ({dims} dims total)")
        print(f"    Text preview: \"{chunks[i].page_content[:80].strip()}…\"")

    return emb_fn, vectors


def step4_store(chunks: list[Document], emb_fn: OllamaEmbeddings):
    header("STEP 4 — Store embeddings in ChromaDB")
    print(f"  Directory  : {CHROMA_DIR}")
    print(f"  Collection : {COLLECTION}")
    print(f"  Documents  : {len(chunks)}")

    # fresh collection for this demo
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    existing = [c.name for c in client.list_collections()]
    if COLLECTION in existing:
        client.delete_collection(COLLECTION)
        print("  (Cleared existing collection for a fresh demo run)")

    vectorstore = Chroma(
        client=client,
        collection_name=COLLECTION,
        embedding_function=emb_fn,
    )

    BATCH = 500
    print(f"\n  Writing in batches of {BATCH}…")
    for start in range(0, len(chunks), BATCH):
        batch = chunks[start:start + BATCH]
        vectorstore.add_documents(batch)
        end = min(start + BATCH, len(chunks))
        print(f"    stored {end}/{len(chunks)}", end="\r", flush=True)
    print(f"    {len(chunks)}/{len(chunks)} chunks stored.          ")

    count = vectorstore._collection.count()
    print(f"\n  ChromaDB now holds {count} vectors.")
    return vectorstore


def step5_rag(vectorstore: Chroma, emb_fn: OllamaEmbeddings):
    header("STEP 5 — Semantic Search + RAG Answer")

    query = "What did the Mad Hatter say about time at the tea party?"
    print(f"  Query: \"{query}\"")

    # ── Pure vector search ──
    print("\n  [Vector search — top retrieved chunks]\n")
    results = vectorstore.similarity_search(query, k=TOP_K)
    for i, doc in enumerate(results, 1):
        preview = doc.page_content[:200].replace("\n", " ").strip()
        print(f"  Chunk {i}: \"{preview}…\"\n")

    pause("now send those chunks + question to the LLM")

    # ── RAG chain ──
    header("STEP 5b — LLM answer from retrieved context")
    print(f"  Model : {LLM_MODEL}")
    print("  Generating answer…\n")

    prompt = ChatPromptTemplate.from_template(
        "Use ONLY the context below to answer the question.\n\n"
        "Context:\n{context}\n\n"
        "Question: {question}"
    )
    llm = ChatOllama(model=LLM_MODEL, temperature=0)
    retriever = vectorstore.as_retriever(search_kwargs={"k": TOP_K})

    chain = (
        RunnableParallel(context=retriever, question=RunnablePassthrough())
        | RunnablePassthrough.assign(
            result=(
                RunnablePassthrough.assign(
                    context=lambda x: "\n\n".join(d.page_content for d in x["context"])
                )
                | prompt
                | llm
                | StrOutputParser()
            )
        )
    )

    response = chain.invoke(query)
    print(f"  Answer:\n")
    for line in response["result"].splitlines():
        print(f"    {line}")
    sources = list({d.metadata.get("source", "?") for d in response["context"]})
    print(f"\n  Sources: {sources}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "█" * 60)
    print("  RAG PIPELINE DEMO — Alice in Wonderland")
    print("  Full local stack: Ollama + ChromaDB")
    print("█" * 60)
    print("""
  Steps:
    1. Load source text
    2. Split into chunks
    3. Generate embeddings
    4. Store in ChromaDB
    5. Semantic search + LLM answer

  Prerequisites:
    ollama pull nomic-embed-text
    ollama pull llama3.1:8b
""")

    if not BOOK_PATH.exists():
        sys.exit(f"Book not found: {BOOK_PATH}")

    pause("Step 1 — Load")
    text = step1_load(BOOK_PATH)

    pause("Step 2 — Chunk")
    chunks = step2_chunk(text)

    pause("Step 3 — Embed (calls Ollama, takes ~1–2 min)")
    emb_fn, _ = step3_embed(chunks)

    pause("Step 4 — Store in ChromaDB")
    vectorstore = step4_store(chunks, emb_fn)

    pause("Step 5 — Search & Answer")
    step5_rag(vectorstore, emb_fn)

    print("\n" + "═" * 60)
    print("  Demo complete.")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    main()
