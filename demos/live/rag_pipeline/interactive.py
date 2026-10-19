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
import sys
from pathlib import Path

from langchain_chroma import Chroma
from rag_pipeline import (
    OllamaEmbeddings, build_chain,
    CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL, LLM_MODEL, TOP_K,
)


def load_existing_store(embedding_model: str = EMBEDDING_MODEL) -> Chroma:
    # Chroma() silently creates an empty store, so check before opening it
    if not Path(CHROMA_DIR).exists():
        sys.exit(f"No vector store at {CHROMA_DIR}. Run `python rag_pipeline.py` first.")

    embeddings = OllamaEmbeddings(model=embedding_model)
    store = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
    )
    count = store._collection.count()
    if count == 0:
        sys.exit(f"Collection '{COLLECTION_NAME}' is empty. Run `python rag_pipeline.py` first.")
    print(f"Loaded collection '{COLLECTION_NAME}' with {count} chunks")
    return store


def main():
    parser = argparse.ArgumentParser(description="Interactive RAG REPL")
    parser.add_argument("--model", default=LLM_MODEL, help="Ollama LLM model")
    parser.add_argument("--embedding-model", default=EMBEDDING_MODEL, help="Ollama embedding model")
    parser.add_argument("--k", type=int, default=TOP_K, help="Number of chunks to retrieve")
    args = parser.parse_args()
    if args.k < 1:
        parser.error("--k must be at least 1")

    store = load_existing_store(args.embedding_model)
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

        parts = query.split()
        if parts[0] == ":k":
            if len(parts) != 2 or not parts[1].isdigit() or int(parts[1]) < 1:
                print("  usage: :k N   (N is a whole number >= 1)")
                continue
            args.k = int(parts[1])
            chain = build_chain(store, model=args.model, k=args.k)
            print(f"  -> k set to {args.k}")
            continue
        if parts[0] == ":model":
            if len(parts) != 2:
                print("  usage: :model NAME   (e.g. :model mistral)")
                continue
            args.model = parts[1]
            chain = build_chain(store, model=args.model, k=args.k)
            print(f"  -> model set to {args.model}")
            continue

        try:
            response = chain.invoke(query)
        except KeyboardInterrupt:
            print("\n  (cancelled)\n")
            continue
        except Exception as e:  # Ollama down, model not pulled, etc. — keep the REPL alive
            print(f"\n  Error: {e}")
            print("  Is `ollama serve` running and the model pulled (`ollama list`)?\n")
            continue

        print(f"\nA: {response['result']}")
        sources = sorted({d.metadata.get("source", "unknown") for d in response["context"]})
        print(f"   Sources: {', '.join(sources)}\n")


if __name__ == "__main__":
    main()
