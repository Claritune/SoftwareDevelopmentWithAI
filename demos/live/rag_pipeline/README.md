# RAG Demo: Local Vector Search with ChromaDB + Ollama

Fully local RAG pipeline — no external APIs, no costs, full data privacy.

## How it works

```
books/**/*.txt  →  chunk  →  embed (nomic-embed-text)  →  ChromaDB (local)
                                                                  ↓
question  →  retrieve top-K chunks  →  llama3.1:8b  →  answer + sources
```

## Prerequisites

### 1. Python dependencies

```bash
uv sync
# or: pip install -r requirements.txt
```

### 2. Ollama — install and pull models

```bash
# Install Ollama: https://ollama.com
ollama serve                    # start Ollama (runs in background on port 11434)
ollama pull llama3.1:8b         # LLM for answering questions (~4.7 GB)
ollama pull nomic-embed-text    # embeddings model (~274 MB)
```

Verify Ollama is running:
```bash
ollama list   # should show both models
```

### 3. Add books

Drop `.txt` files into the `books/` folder (any depth of subfolders is fine):
```
books/
  fiction/
    war_and_peace.txt
  science/
    origin_of_species.txt
```

### 4. ChromaDB — nothing to start

There is **no separate ChromaDB server to run**. This demo uses ChromaDB in
embedded (persistent-client) mode: it runs in-process inside the Python scripts
and stores everything on disk at `./chroma_db`. Installing the Python
dependencies (step 1) is all the setup ChromaDB needs — the DB is created
automatically the first time you run the ingest step below.

## Running the demo

### Step 1 — Ingest (run once)

Loads all `.txt` files from `books/` and nested subfolders, chunks them, embeds them, and saves to a local ChromaDB at `./chroma_db`.

```bash
uv run python rag_pipeline.py
# or: python rag_pipeline.py
```

Expected output:
```
Loaded N documents from ./books
Created M chunks from N documents
Using Ollama embeddings (nomic-embed-text)
Vector store created at ./chroma_db
...
```

This step can take a while for large collections. Run it only once — the DB persists on disk.

### Step 2 — Interactive Q&A (for live demo)

Loads the existing ChromaDB and opens a question-answering REPL:

```bash
uv run python interactive.py
# or: python interactive.py
```

```
Q: What does the author say about human nature?
A: ...
   Sources: books/fiction/war_and_peace.txt

Q: quit
```

**REPL commands:**
- `:k N` — change number of retrieved chunks (default 4)
- `:model NAME` — swap LLM on the fly (e.g. `:model mistral`)
- `quit` — exit

**Optional flags:**
```bash
python interactive.py --model llama3.1:8b --k 6
```

## Files

| File | Purpose |
|------|---------|
| `rag_pipeline.py` | Full pipeline: load → chunk → embed → store → search → generate |
| `interactive.py` | Interactive REPL for querying an existing ChromaDB collection |
| `books/` | Place `.txt` files here (nested subfolders supported) |
| `chroma_db/` | Local vector DB created on first ingest (gitignored) |
