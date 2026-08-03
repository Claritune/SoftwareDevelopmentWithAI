# Agent Instructions

## Coding Preferences

- **TypeScript** with strict mode (`"strict": true` in `tsconfig.json`). Prefer explicit types at module boundaries; avoid `any`.
- **pnpm** for all dependency management (`pnpm install`, `pnpm add`, `pnpm run`). Do not use npm or yarn unless explicitly requested.
- **Test-first development (TDD)**: write failing tests before implementation, then implement the minimum code to pass, then refactor. Skip tests only when the user explicitly says so.

## Mem0 MCP — Persistent Memory

This project uses the **mem0** MCP server (configured in `.cursor/mcp.json`) for cross-session memory. Use it instead of Cursor rules for remembering preferences, conventions, and project context.

### Session start

Before asking the user to re-explain context, call `search_memories` for relevant project and user preferences.

### When to save

Call `add_memory` when you discover or confirm:

- User preferences and coding conventions
- Project architecture and tech stack choices
- Key decisions, debugging insights, and workflow patterns

When in doubt, save it — future sessions benefit from over-remembering.

### When to update

Call `update_memory` when prior context changes (e.g. switched package manager, new test framework).

### Scope

Memories are scoped to `MEM0_USER_ID` (`demo-user` in `.cursor/mcp.json`).

### Troubleshooting

The mem0 server itself works — Qdrant (`localhost:6333`) and Ollama (`localhost:11434`, models `bge-m3` + `qwen3:14b`) are the prerequisites.

If the agent cannot call mem0 tools:

1. **Enable the server in Cursor** — Settings → MCP → toggle **mem0** ON. New project MCP servers start as `disconnected` until manually enabled.
2. **Pre-warm the uvx cache** — first `git+https://...` install takes ~12s, but Cursor's MCP cold-start timeout is 10s. Run once from terminal before enabling:
   ```bash
   MEM0_PROVIDER=ollama MEM0_LLM_MODEL=llama3.1:8b MEM0_USER_ID=demo-user \
     /Users/bigromanov/.local/bin/uvx --from 'git+https://github.com/elvismdev/mem0-mcp-selfhosted.git@v0.3.2' \
     --with 'mcp[cli]>=1.23.0,<2' mem0-mcp-selfhosted
   ```
   (Ctrl+C after it starts — the cache is warm.)
3. **Verify manually** — send an MCP initialize + `tools/list` over stdio; you should see 11 tools including `add_memory` and `search_memories`.
