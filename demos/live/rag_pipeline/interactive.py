"""
Interactive RAG REPL
====================
Load an existing ChromaDB collection and ask questions interactively.
Ingest first with rag_pipeline.py, then query here.

Usage:
  python interactive.py
  python interactive.py --model mistral --k 6
"""

import argparse
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama
from rag_pipeline import OllamaEmbeddings, build_chain, _PROMPT, CHROMA_DIR, COLLECTION_NAME

EMBEDDING_MODEL = "nomic-embed-text"


def load_existing_store(embedding_model: str = EMBEDDING_MODEL) -> Chroma:
    embeddings = OllamaEmbeddings(model=embedding_model)
    store = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
    )
    count = store._collection.count()
    print(f"Loaded collection '{COLLECTION_NAME}' with {count} chunks")
    return store


def main():
    parser = argparse.ArgumentParser(description="Interactive RAG REPL")
    parser.add_argument("--model", default="llama3.1:8b", help="Ollama LLM model")
    parser.add_argument("--embedding-model", default=EMBEDDING_MODEL, help="Ollama embedding model")
    parser.add_argument("--k", type=int, default=4, help="Number of chunks to retrieve")
    args = parser.parse_args()

    store = load_existing_store(args.embedding_model)
    retriever = store.as_retriever(search_kwargs={"k": args.k})
    llm = ChatOllama(model=args.model, temperature=0)
    chain = build_chain(store, model=args.model, k=args.k)

    print(f"\nModel: {args.model} | Embeddings: {args.embedding_model} | k={args.k}")
    print("Type a question, or 'quit' to exit.")
    print("Commands: ':k N' to change k, ':model NAME' to swap LLM\n")

    while True:
        try:
            query = input("Q: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not query:
            continue
        if query.lower() in ("quit", "exit", "q"):
            break

        if query.startswith(":k "):
            args.k = int(query.split()[1])
            chain = build_chain(store, model=args.model, k=args.k)
            print(f"  -> k set to {args.k}")
            continue
        if query.startswith(":model "):
            args.model = query.split()[1]
            chain = build_chain(store, model=args.model, k=args.k)
            print(f"  -> model set to {args.model}")
            continue

        response = chain.invoke(query)
        print(f"\nA: {response['result']}")
        sources = set(d.metadata.get("source", "unknown") for d in response["context"])
        print(f"   Sources: {', '.join(sources)}\n")


if __name__ == "__main__":
    main()
