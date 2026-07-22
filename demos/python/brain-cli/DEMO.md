# BrainCLI — Subagent Demo Script

## Prerequisites

```bash
cd demos/python/brain-cli
uv pip install -e ".[dev]"
# Set OPENAI_API_KEY in .env
brain --help
```

Create some seed notes to have data to work with:

```bash
brain create "Conway's Law" \
  --content "Organizations design systems that mirror their communication structures. Mel Conway proposed this in 1967. See also [[Reverse Conway Maneuver]]." \
  --tag architecture --tag organization

brain create "Reverse Conway Maneuver" \
  --content "Intentionally structuring teams to produce a desired architecture. Based on [[Conway's Law]]. Used extensively at companies like Spotify and Netflix." \
  --tag architecture --tag teams

brain create "Python Type Hints" \
  --content "Python supports gradual typing through type hints (PEP 484). Tools like mypy and pyright provide static type checking. See [[Pydantic]] for runtime validation." \
  --tag python --tag typing

brain create "Pydantic" \
  --content "Data validation library for Python using type hints. V2 is a complete rewrite in Rust. Used by FastAPI, LangChain, and many other frameworks. See [[Python Type Hints]]." \
  --tag python --tag libraries

brain create "LangChain" \
  --content "Framework for building LLM applications. Key concepts: chains, agents, tools, memory. Built by Harrison Chase at the company LangChain Inc. Uses [[Pydantic]] for data models." \
  --tag ai --tag python --tag libraries --extract
```

Verify the vault works:
```bash
brain list
brain graph
brain search "Python"
brain search "framework for AI" --semantic
brain entities
```

## Agent Files

All agents are defined in `.claude/agents/`. Show the audience this directory before starting:

```
.claude/agents/
├── product-manager.md    # Role: specs features, writes user stories
├── qa.md                 # Role: writes tests, identifies edge cases
├── code-reviewer.md      # Role: reviews for quality and security
├── storage-dev.md        # Module: storage (notes, files, links)
├── search-dev.md         # Module: search (keyword + semantic)
├── entity-dev.md         # Module: entities (LLM extraction)
├── cli-dev.md            # Module: CLI layer (Typer commands)
└── pattern-enforcer.md   # Pattern: cross-module consistency
```

---

## Demo 1: Role-Based Agents

### Goal
Show how agents with different roles (PM, QA, Reviewer) produce fundamentally different output from the same codebase.

### Scenario: Add a "note summary" feature
The user wants `brain summarize <note_id>` — an LLM-generated summary of a note.

### Step 1: PM Agent defines the feature

Type in Claude Code:
```
@product-manager spec out a new "summarize" command: `brain summarize <note_id>`
that uses the LLM to generate a concise summary of a note. Consider edge cases
like short notes, notes with wiki-links, and whether summaries should be cached.
```

**What to show the audience**: The PM agent asks questions the developer wouldn't think of. It considers edge cases from a user perspective, not a technical one. It does NOT write code.

### Step 2: QA Agent writes tests first (TDD)

```
@qa write pytest tests for the new summarize command. Cover: summarizing an
existing note, a non-existent note, missing API key, and output format.
Write to tests/test_summarize.py. Mock the LLM calls.
```

**What to show the audience**: The QA agent writes tests *before* the implementation exists. Tests define the contract. It does NOT touch production code.

### Step 3: Code Reviewer reviews the tests

```
@code-reviewer review tests/test_summarize.py
```

**What to show the audience**: Three different agents, three different perspectives on the same feature. PM thinks about users, QA thinks about correctness, Reviewer thinks about quality. None of them step on each other's scope.

---

## Demo 2: Module-Specific Agents

### Goal
Show how agents scoped to specific modules produce better code than generic agents, because they follow module-specific rules.

### Scenario: Add tag-based search filtering

### Step 1: Without module rules (generic agent)

Type without any `@agent` prefix — just a plain request:
```
Add tag-based filtering to the search command in BrainCLI.
When searching, the user should be able to pass --tag to filter
results to only notes with that tag.
```

**Point out**: The generic agent might modify files across modules, mix concerns, or implement filtering logic directly in the CLI layer.

### Step 2: With module agents (scoped)

Undo the generic agent's changes, then use scoped agents:

First, the search module:
```
@search-dev add tag-based filtering. Both keyword_search and semantic_search
should accept an optional tags parameter. For keyword_search, filter the notes
list. For semantic_search, use ChromaDB metadata filtering.
```

Then, the CLI layer:
```
@cli-dev add a --tag option to the search command that passes through to
the search functions.
```

**What to show the audience**: Module-scoped agents stay in their lane. The search agent doesn't touch the CLI, the CLI agent doesn't implement search logic. Each reads its own rules file. Clean boundaries.

---

## Demo 3: Pattern-Enforcing Agents

### Goal
Show how a dedicated agent can detect and fix inconsistencies across modules.

### Scenario: Introduce an intentional inconsistency, then fix it

### Step 1: Create the inconsistency

Manually edit `src/brain_cli/entities/extractor.py` — change two things:

1. Change the datetime pattern in `models.py`:
```python
# In the Entity class, change:
extracted_at: datetime = Field(default_factory=datetime.now)
# To:
extracted_at: datetime = Field(default_factory=lambda: datetime.utcnow())
```

2. Change the JSON persistence in `extractor.py`:
```python
# Change _save to use manual dict construction instead of model_dump:
def _save(self) -> None:
    self._entities_path.parent.mkdir(parents=True, exist_ok=True)
    data = [{"name": e.name, "type": e.entity_type, "note": e.source_note_id} for e in self._entities]
    self._entities_path.write_text(json.dumps(data))
```

### Step 2: Run the Pattern Enforcer

```
@pattern-enforcer scan all Python files in src/brain_cli/ for pattern violations.
```

**What to show the audience**: The pattern enforcer reads `rules/patterns.md`, finds both violations (utcnow and manual serialization), reports them with file/line, and fixes them. Pattern agents are like automated code standards — they catch drift that humans miss after the 10th module.

---

## Demo 4: Parallel Execution

### Goal
Show agents working on independent modules simultaneously, with no conflicts.

### Scenario: Add an "export" feature to all three modules

Each module needs to support exporting its data:
- Storage: export all notes as a JSON array
- Search: export the search index stats
- Entities: export all entities as CSV

### Run three module agents in parallel

```
I need to add export functionality to all three modules. Run these in parallel:

1. @storage-dev add an export_notes() method to NoteStore that returns all
   notes as a list of dicts (using model_dump). Add a test.

2. @search-dev add a get_stats() method to SearchEngine that returns a dict
   with total_documents and collection_name. Add a test.

3. @entity-dev add an export_csv() method to EntityExtractor that returns
   entities as a CSV string (columns: name, type, source_note, extracted_at).
   Add a test.
```

Then wire them together:
```
@cli-dev add an "export" command with subcommands: notes, search-stats,
entities. Each calls the corresponding module method and prints the result.
```

**What to show the audience**: Three agents ran simultaneously, each in their own module, following their own rules, with no conflicts. This is the Reverse Conway Maneuver — agent structure mirrors architecture.

---

## Talking Points

### Why subagents over a single agent?

1. **Context focus** — A storage agent doesn't need to understand ChromaDB. A search agent doesn't need to parse YAML frontmatter. Smaller context = better output.

2. **Parallel execution** — Independent modules can be built simultaneously. A single agent is sequential.

3. **Rule enforcement** — Each agent gets module-specific rules. A generic agent needs to hold all rules in context.

4. **Blast radius** — If an agent produces bad code, it only affects one module. Other modules are untouched.

### The Reverse Conway Maneuver

"Organizations design systems that mirror their own communication structure" — Conway's Law.

The Reverse Conway Maneuver: structure your agents (teams) to mirror the architecture you want. If you want clean module boundaries, give each agent its own module. The agent structure *produces* the architecture.

### When NOT to use subagents

- Small changes that touch one file
- Bug fixes where the root cause is known
- Changes that span all modules (refactoring a shared model) — use a single agent with full context
