# Mem0 + Cursor MCP Demo

Fully local persistent memory for AI agents using Mem0, Ollama, and Qdrant.

## Quick Start

```bash
# Run the automated setup (starts Qdrant, pulls models, warms uvx cache)
./setup.sh

# Tear everything down after the demo
./setup.sh --cleanup
```

The script checks all prerequisites (Docker, Ollama, uvx) and handles errors.

---

## Manual Steps

### Step 1 — Start Qdrant in Docker

Single container, no compose file needed:

```bash
docker run -d --name qdrant \
  -p 6333:6333 -p 6334:6334 \
  -v qdrant_data:/qdrant/storage \
  qdrant/qdrant
```

Verify it's running:

```bash
curl http://localhost:6333/healthz
```

### Step 2 — Pull Ollama Models

Two models: one for LLM fact extraction, one for embeddings.

```bash
ollama pull llama3.1:8b
ollama pull bge-m3
```

Make sure Ollama is running:

```bash
ollama serve
```

### Step 3 — Configure Cursor MCP

The file `.cursor/mcp.json` is already configured in this project. For reference:

```json
{
  "mcpServers": {
    "mem0": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/elvismdev/mem0-mcp-selfhosted.git@v0.3.2",
        "--with",
        "mcp[cli]>=1.23.0,<2",
        "mem0-mcp-selfhosted"
      ],
      "env": {
        "MEM0_PROVIDER": "ollama",
        "MEM0_LLM_MODEL": "llama3.1:8b",
        "MEM0_USER_ID": "demo-user"
      }
    }
  }
}
```

### Step 4 — Restart Cursor

Close and reopen Cursor completely. MCP servers load at startup.

After restart: **Settings → Tools & MCP** — you should see `mem0` listed. First connection may take a moment while uvx downloads and installs the package.

---

## Demo Script

### Step 5 — Store Memories

Open a Cursor chat (`Cmd+L`) and send each of these one at a time:

```
Remember that I really love lasagna and pizza
```

```
Remember that I love Italian food in general
```

```
Remember that I do not like spinach
```

The agent calls `add_memory` for each. Mem0 extracts the atomic facts, embeds them, and stores them in Qdrant.

### Step 6 — Retrieve Memories (New Session)

**Close the chat.** Open a brand new chat and ask:

```
Would I like Spinach and Ricotta Cannelloni?
```

The agent calls `search_memories` and retrieves facts from the previous session. **This is the key demo moment** — without Mem0, the agent knows nothing about your preferences.

### Step 7 — Fact Update (Update Pipeline)

```
We've switched from pnpm to bun as our package manager. Update your memory.
```

Then verify:

```
What package manager do we use?
```

Should return **bun**, not pnpm. This shows the UPDATE operation from the two-phase extraction/update pipeline.

### Step 8 — Inspect Raw Memories

```
Show me all the memories you have stored.
```

This calls `get_memories` / `get_all_memories` and dumps the full list. Walk the audience through how messy conversational input was distilled into clean atomic facts.

---

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `add_memory` | Store new memories (LLM extracts facts) |
| `search_memories` | Semantic search over stored memories |
| `get_memories` | Retrieve all stored memories |
| `update_memory` | Update an existing memory by ID |
| `delete_memory` | Delete a specific memory by ID |
| `delete_all_memories` | Clear all stored memories |

---

## Talking Points

- **No full Mem0 server needed** — the MCP script imports `mem0ai` as a library
- **Same MCP pattern** from the MCP module, just a different server
- **Extraction runs on qwen3** in Ollama — show `ollama ps` to see the model loaded
- **Qdrant is a single Docker container** storing all the vectors
- **`add_memory` vs raw vector store** — `add_memory` uses LLM to extract atomic facts; raw vector store just embeds text as-is
- **`MEM0_PROVIDER=ollama`** is all it takes to go fully local — one config change
- Show `docker stats` to demonstrate resource usage during extraction

---

## Cleanup

```bash
./setup.sh --cleanup
```

Or manually:

```bash
docker stop qdrant && docker rm qdrant
docker volume rm qdrant_data
```
