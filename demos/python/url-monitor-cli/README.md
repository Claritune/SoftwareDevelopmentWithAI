# URL Monitor

A Python CLI tool that monitors URLs for uptime, detects when sites go down or come back up, and prints notifications to stdout.

This repository is a **QRSPI demo**: it started as an empty directory and was built using a structured AI-assisted workflow — not by jumping straight to code.

## What it does

Given one or more URLs, the tool:

1. Performs HTTP health checks on a schedule
2. Tracks consecutive failures per URL
3. Announces **DOWN** and **UP** transitions to stdout
4. Logs every check to stderr or an optional log file
5. Runs in a foreground poll loop until you press Ctrl+C

A site is considered **down** after N consecutive failures (HTTP status ≥ 400 or connection timeout). N defaults to 3 and is configurable via `--failure-threshold`.

### Example (target behavior)

```bash
url-monitor https://example.com https://api.example.com/health \
  --failure-threshold 3 \
  --interval 30 \
  --timeout 10 \
  --log-file monitor.log
```

Stdout on transitions:

```
[2026-06-11T10:00:00Z] DOWN  https://example.com  (3 consecutive failures, last: HTTP 503)
[2026-06-11T10:02:00Z] UP    https://example.com  (HTTP 200, 142ms)
```

## Current status

| Phase | Status | Delivers |
|-------|--------|----------|
| **1 — Check URLs from CLI** | Done | Package skeleton, Pydantic config, HTTP checker, single-round CLI |
| **2 — Transition detection** | Planned | State machine, DOWN/UP stdout notifications |
| **3 — Continuous monitoring** | Planned | Poll loop, logging, graceful shutdown |

**Today (Phase 1)** the CLI performs a single check round and prints results to stderr:

```bash
pip install -e ".[dev]"
python -m url_monitor https://httpbin.org/status/200
url-monitor --help
```

## Quick start

**Requirements:** Python 3.11+

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Check a URL (single round, Phase 1)
python -m url_monitor https://example.com
```

### CLI options

| Flag | Default | Description |
|------|---------|-------------|
| `URLS` | *(required)* | One or more URLs to monitor |
| `--failure-threshold` | `3` | Consecutive failures before marking DOWN |
| `--interval` | `30` | Seconds between check rounds (Phase 3) |
| `--timeout` | `10` | HTTP request timeout in seconds |
| `--log-file` | *(none)* | Append check logs to this file (Phase 3) |

## Project layout

```
demo_url_monitor/
├── goal.md                 # Original one-line product goal
├── README.md
├── pyproject.toml
├── src/url_monitor/        # Application code
│   ├── cli.py              # Click entry point
│   ├── config.py           # Pydantic Settings
│   ├── checker.py          # HTTP health checks (httpx)
│   └── ...
├── tests/
├── .cursor/skills/         # QRSPI agent skills (Question → PR)
├── docs/rules/             # Coding conventions for the project
└── thoughts/qrspi/         # QRSPI workflow artifacts
    └── 2026-06-11-url-uptime-monitor/
        ├── task.md         # What we're building
        ├── questions.md    # Clarifying questions (greenfield)
        ├── answers.md      # User decisions
        ├── design.md       # Architecture and scope
        ├── structure.md    # Vertical implementation slices
        └── plan.md         # Tactical step-by-step plan
```

## Development methodology: QRSPI

This project was built with **QRSPI** — a phased workflow for AI-assisted development that forces alignment *before* code is written. Each phase produces a reviewable artifact; the agent does not silently make architectural decisions.

| Phase | Skill | Artifact | Purpose |
|-------|-------|----------|---------|
| **Q** — Question | `/question` | `questions.md`, `answers.md` | Surface ambiguities and get explicit user decisions |
| **R** — Research | `/research` | `research.md` | Document existing codebase patterns *(skipped for greenfield)* |
| **S** — Structure | `/structure` | `structure.md` | Break work into vertical, testable slices |
| **P** — Plan | `/plan` | `plan.md` | Tactical implementation details with verification steps |
| **I** — Implement | `/implement` | code + commits | Execute one phase at a time, verify, commit |

Design decisions are captured in `design.md` between Question and Structure.

### Why QRSPI for a greenfield project?

A naive prompt like *"build me a URL monitor"* causes an agent to silently choose Python, `requests`, a 60-second interval, stdout-only output, and no persistence. QRSPI turns those into **questions you answer explicitly**.

For this project, key decisions captured in `answers.md` include:

- **One-shot foreground loop** (not a background daemon) — runs until Ctrl+C
- **URLs via CLI arguments** (not a config file)
- **Stdout-only notifications** for v1
- **In-memory state + log output** (no database)
- **Sequential checks** (no asyncio concurrency yet)
- **Pure CLI** (FastAPI rules in `docs/rules/` are out of scope)

### Greenfield adaptation

The Question skill was extended to detect greenfield vs brownfield projects:

- **Greenfield** (no app code): clarifying questions about *what to build* → skip Research → go to Design
- **Brownfield** (existing codebase): neutral research questions about *what exists* → Research → Design

Agent skills live in `.cursor/skills/`. Duplicate prompts are in `docs/skills/`.

## Design decisions

Full detail is in `thoughts/qrspi/2026-06-11-url-uptime-monitor/design.md`. Summary:

- **Stack:** Python 3.11+, click, httpx (sync), pydantic-settings
- **Config:** Pydantic `BaseSettings` via `from_cli()` — no `os.getenv()` in app code
- **Failure criteria:** HTTP status ≥ 400 or connection/timeout error
- **Notifications:** stdout on DOWN/UP transitions only; routine checks go to logs
- **Out of scope:** Slack/email, SQLite, FastAPI, config files, concurrent checks

## Running the QRSPI workflow

Artifacts for this build are in `thoughts/qrspi/2026-06-11-url-uptime-monitor/`.

```bash
# From an empty project with goal.md:
/question goal.md          # Clarifying questions → answers.md
/design                    # Architecture → design.md
/structure                 # Vertical slices → structure.md
/plan                      # Implementation plan → plan.md
/implement                 # Build phase by phase
```

## License

Part of the [AICourseMaterials](https://github.com/) demos collection.
