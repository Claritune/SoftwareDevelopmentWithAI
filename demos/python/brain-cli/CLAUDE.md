# BrainCLI — Second Brain CLI

A CLI-based personal knowledge management system built with Python, LangChain, and OpenAI.

## Project Structure

```
src/brain_cli/
├── cli.py              # Typer CLI — the user-facing interface
├── models.py           # Shared Pydantic models (Note, Entity, SearchResult)
├── storage/store.py    # Note CRUD, markdown files, YAML frontmatter, link index
├── search/engine.py    # Keyword + semantic search (OpenAI embeddings, ChromaDB)
└── entities/extractor.py  # Entity extraction (gpt-4o-mini via LangChain)
```

## Tech Stack

- **CLI**: Typer + Rich
- **LLM**: OpenAI gpt-4o-mini via LangChain
- **Embeddings**: OpenAI text-embedding-3-small via langchain-openai
- **Vector Store**: ChromaDB (persistent, local)
- **Storage**: Markdown files with YAML frontmatter
- **Models**: Pydantic v2

## Key Design Decisions

- Notes are stored as `.md` files with YAML frontmatter — the vault directory is the source of truth
- Indexes (links, embeddings, entities) live in `.brain/` subdirectory and can be rebuilt from files
- Wiki-style `[[links]]` resolve by note title, not by ID
- Link index is rebuilt on every save to keep bidirectional links consistent
- LLM/embedding features degrade gracefully when OPENAI_API_KEY is not set

## Running

```bash
pip install -e .
brain --help
```

## Environment

Requires `OPENAI_API_KEY` in `.env` or environment for semantic search and entity extraction.

---

# Subagent Architecture

This project uses specialized agents defined in `.claude/agents/`. Each agent has a specific role, scope, and rules.

## Agent Inventory

### Role-Based Agents
| Agent | File | Purpose |
|-------|------|---------|
| Product Manager | `.claude/agents/product-manager.md` | Specs features, writes user stories, prioritizes work |
| QA Engineer | `.claude/agents/qa.md` | Writes pytest tests, identifies edge cases |
| Code Reviewer | `.claude/agents/code-reviewer.md` | Reviews code for quality, security, consistency |

### Module-Specific Agents
| Agent | File | Scope |
|-------|------|-------|
| Storage Dev | `.claude/agents/storage-dev.md` | `src/brain_cli/storage/`, `tests/test_storage.py` |
| Search Dev | `.claude/agents/search-dev.md` | `src/brain_cli/search/`, `tests/test_search.py` |
| Entity Dev | `.claude/agents/entity-dev.md` | `src/brain_cli/entities/`, `tests/test_entities.py` |
| CLI Dev | `.claude/agents/cli-dev.md` | `src/brain_cli/cli.py` |

### Pattern-Enforcing Agents
| Agent | File | Purpose |
|-------|------|---------|
| Pattern Enforcer | `.claude/agents/pattern-enforcer.md` | Detects and fixes cross-module inconsistencies |

## Rules Files

Each module has a rules file in `rules/` that its agent reads before making changes:
- `rules/storage.md` — storage invariants and patterns
- `rules/search.md` — search invariants and patterns
- `rules/entities.md` — entity extraction invariants and patterns
- `rules/cli.md` — CLI layer rules
- `rules/patterns.md` — cross-module canonical patterns (used by pattern enforcer)

## Parallel Execution Patterns

### Building multiple modules simultaneously
Launch storage-dev, search-dev, and entity-dev agents in parallel — each works only in its own scope, so there are no conflicts.

### QA + Review in parallel
After implementation, launch qa and code-reviewer agents simultaneously — one writes tests, the other reviews the code.
