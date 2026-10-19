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
and stores everything on disk (`./chroma_db` or `./chroma_db_alice`). Installing the Python
dependencies (step 1) is all the setup ChromaDB needs — the DB is created
automatically the first time you run the ingest step below.

## Running the demo

All commands below must be run from this directory (`demos/live/rag_pipeline/`) —
the scripts use relative paths for `books/` and the ChromaDB folders.

For a visual, step-by-step explanation of what happens under the hood, open
[`demo-explanation.html`](demo-explanation.html) in a browser.

### Option A — Guided walkthrough (recommended for live demos)

`demo.py` walks through every stage of the pipeline on `books/alice.txt`,
pausing between steps (press ENTER to advance):

```bash
uv run python demo.py
```

1. **Load** — reads the book and prints its size and first lines
2. **Chunk** — splits it into ~500-char chunks (80-char overlap) and shows samples
3. **Embed** — turns every chunk into a 768-dim vector with `nomic-embed-text`
4. **Store** — writes the chunks + vectors into ChromaDB at `./chroma_db_alice`
5. **Search & answer** — retrieves the top 4 chunks for a sample question and
   has `llama3.1:8b` answer from them

The collection is rebuilt from scratch on every run, so it is safe to rehearse
repeatedly. A full run takes well under a minute on an Apple Silicon Mac.

### Option B — Ingest + interactive Q&A

#### Step 1 — Ingest (run once)

Loads all `.txt` files from `books/` and nested subfolders, chunks them, embeds them, and saves to a local ChromaDB at `./chroma_db`.

```bash
uv run python rag_pipeline.py              # up to 20 new files per run
uv run python rag_pipeline.py --all        # every new file
uv run python rag_pipeline.py --max-files 5
```

Expected output:
```
Files: 1 total | 0 already ingested | 1 to process
[1/1] alice.txt  (190 chunks)
    190 chunks embedded

Done. 1 files ingested this run.
Ingestion complete. Run interactive.py to query.
```

Already-ingested files are recorded in `chroma_db/.ingested_files.txt` and
skipped on later runs, so you can add books and re-run to ingest just the new
ones. Delete `chroma_db/` to start over.

#### Step 2 — Interactive Q&A

Loads the existing ChromaDB and opens a question-answering REPL (it exits with
a hint if you haven't ingested yet):

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
| `demo.py` | Guided, step-by-step walkthrough of the pipeline on Alice in Wonderland |
| `demo-explanation.html` | Visual documentation of how the demo works |
| `rag_pipeline.py` | Full pipeline: load → chunk → embed → store → search → generate |
| `interactive.py` | Interactive REPL for querying an existing ChromaDB collection |
| `books/` | Place `.txt` files here (nested subfolders supported) |
| `chroma_db/` | Local vector DB created by `rag_pipeline.py` (gitignored) |
| `chroma_db_alice/` | Local vector DB rebuilt by each `demo.py` run (gitignored) |
