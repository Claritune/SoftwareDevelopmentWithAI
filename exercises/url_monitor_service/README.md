# Exercise: URL Monitor API

Your task is to implement `goal.md` — a FastAPI-based URL monitoring service — using the **QRSPI methodology** and a properly configured agent environment (skills, rules, and hooks).

The completed CLI demo in the parent directory (`../`) shows how QRSPI was applied to a greenfield project. This exercise asks you to repeat the process for a **new, larger goal** with different architectural constraints (background tasks, SQLite, REST API, async concurrency).

## Before you start

1. **Read `goal.md`** in this folder — that is your product brief.
2. **Skim the CLI demo** (`../README.md`, `../thoughts/qrspi/`) to understand the domain, not to copy code.
3. **Create a fresh project directory** (recommended) or work in a new git branch — do not modify the CLI demo artifacts.

```bash
# Example: start clean
mkdir url-monitor-api && cd url-monitor-api
git init
cp /path/to/exercise/goal.md .
```

## Step 1 — Set up your agent environment

Before running `/question`, configure Cursor so the agent has the right guardrails. You need three things: **skills**, **rules**, and **hooks**.

### Skills (QRSPI workflow)

Copy the QRSPI skills from the CLI demo and adjust if needed:

```bash
mkdir -p .cursor/skills
cp -r ../.cursor/skills/question  .cursor/skills/
cp -r ../.cursor/skills/research  .cursor/skills/
cp -r ../.cursor/skills/design    .cursor/skills/
cp -r ../.cursor/skills/structure .cursor/skills/
cp -r ../.cursor/skills/plan      .cursor/skills/
cp -r ../.cursor/skills/implement .cursor/skills/
cp -r ../.cursor/skills/worktree  .cursor/skills/
cp -r ../.cursor/skills/pr        .cursor/skills/
```

Optional: copy `../docs/skills/` as human-readable reference prompts.

| Skill | Command | When to use |
|-------|---------|-------------|
| Question | `/question goal.md` | First — clarify requirements (greenfield) |
| Research | `/research` | After question — if extending existing code |
| Design | `/design` | Architecture and scope decisions |
| Structure | `/structure` | Vertical implementation slices |
| Plan | `/plan` | Tactical step-by-step plan |
| Implement | `/implement` | Build phase by phase |
| Worktree | `/worktree` | Optional isolated git branch |
| PR | `/pr` | Optional pull request |

### Rules (coding conventions)

This exercise is **FastAPI-based** — the CLI-specific choices do not apply. Add rules that constrain how the agent writes code:

```bash
mkdir -p .cursor/rules docs/rules/fastapi
cp ../.cursor/rules/pydantic-settings.mdc .cursor/rules/
cp ../docs/rules/fastapi/async_consistency.md docs/rules/fastapi/
cp ../docs/rules/fastapi/structured_error_response.md docs/rules/fastapi/
```

Consider adding rules specific to this exercise, for example:

| Rule file | Purpose |
|-----------|---------|
| `.cursor/rules/fastapi-lifespan.mdc` | Background scheduler starts/stops in app lifespan |
| `.cursor/rules/sqlite-persistence.mdc` | Repository pattern; migrations or schema init approach |
| `.cursor/rules/api-naming.mdc` | REST resource naming (`/monitors`, plural nouns, JSON shapes) |

Write these yourself or ask the agent to draft them during the Design phase — then commit them **before** Implement.

### Hooks (automation)

Add at least one Cursor hook that reinforces quality during development. Examples:

| Hook | Trigger | Action |
|------|---------|--------|
| **pytest on save** | After editing `src/**/*.py` | Run `uv run pytest tests/ -q` |
| **ruff check** | Before commit | Run linter and block if errors |
| **phase checkpoint** | After agent completes a turn | Remind to update `plan.md` checkboxes |

Create hooks via Cursor Settings → Hooks, or add scripts under `.cursor/hooks/`. Document your hooks in `AGENTS.md` so future sessions know they exist.

```bash
mkdir -p .cursor/hooks
# Example: see Cursor docs for hooks.json format
```

At minimum, create **`AGENTS.md`** at the project root summarizing stack choices, rules, and QRSPI artifact paths (copy and adapt from `../AGENTS.md`).

## Step 2 — Run QRSPI

Work through every phase. **Do not skip to code.**

```
/question goal.md     →  questions.md + answers.md
/design               →  design.md        (skip /research for greenfield)
/structure            →  structure.md
/plan                 →  plan.md
/implement            →  code, phase by phase
```

Artifacts go in `thoughts/qrspi/YYYY-MM-DD-url-monitor-api/` (or your chosen id).

### What to decide in the Question phase

The goal leaves intentional gaps. Your clarifying questions should resolve at least:

- Async stack: `asyncio` + `httpx.AsyncClient` + `aiosqlite` vs sync SQLite with thread pool?
- Scheduler: asyncio tasks, APScheduler, or FastAPI `BackgroundTasks` + custom loop?
- API shape: exact endpoint paths, pagination, JSON schemas
- Database schema: tables for monitors, checks, transitions
- How the background loop discovers new/changed monitors from SQLite

### What changes from the CLI demo

| CLI demo | This exercise |
|----------|-----------------|
| click CLI args | REST JSON bodies |
| In-memory state | SQLite persistence |
| Sequential checks | Concurrent async checks |
| Foreground poll loop | Background scheduler in app lifespan |
| stdout notifications | Stored transitions + API queries |
| Greenfield question skill | Same — still greenfield |

## Step 3 — Implement and verify

Follow `plan.md` one phase at a time. Suggested vertical slices (you may reorder during `/structure`):

1. **Project skeleton** — FastAPI app, Pydantic settings, SQLite schema, health endpoint
2. **Monitor CRUD** — REST API for URL configuration, persisted in SQLite
3. **HTTP checker** — async health check with httpx, unit tested
4. **Background scheduler** — poll enabled monitors, run checks concurrently
5. **Results API** — store and query check history and transitions
6. **Integration** — end-to-end test: create monitor → wait for checks → query status

Verification commands (use `uv` or `pip`):

```bash
uv sync --extra dev
uv run pytest tests/ -v
uv run uvicorn app.main:app --reload
# Open http://127.0.0.1:8000/docs
```

## Deliverables

When finished, your repository should contain:

- [ ] Working FastAPI service matching `goal.md`
- [ ] `thoughts/qrspi/<id>/` artifacts (task, questions, answers, design, structure, plan)
- [ ] `.cursor/skills/` — QRSPI skills
- [ ] `.cursor/rules/` and `docs/rules/` — coding conventions
- [ ] `.cursor/hooks/` — at least one automation hook (documented)
- [ ] `AGENTS.md` — agent instructions
- [ ] `README.md` — how to install, run, and test your service
- [ ] `pytest` suite passing
- [ ] `uv.lock` committed (if using uv)

## Evaluation checklist

| Criterion | Points to check |
|-----------|-----------------|
| QRSPI artifacts | All phases documented; decisions traceable |
| Agent environment | Skills, rules, hooks, AGENTS.md present |
| Background monitoring | Checks run without API calls triggering them |
| Concurrency | Multiple URLs checked without serial blocking |
| SQLite | Config and results survive restart |
| REST API | CRUD monitors, query status, query history |
| Tests | Automated coverage of API and checker |
| Rules followed | Pydantic settings, async httpx, structured errors |

## Getting help

- CLI demo walkthrough: `../README.md`
- QRSPI empty-project demo: `../../demo_qrspi_v2/qrspi-empty-project-demo.md`
- FastAPI rules: `../docs/rules/fastapi/`
- Do not read `../thoughts/qrspi/.../plan.md` for solutions — produce your own.

Good luck. Start with `/question goal.md`.
