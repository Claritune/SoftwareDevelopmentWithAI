# Agent Instructions — URL Monitor

This is a **pure Python CLI** for URL uptime monitoring, built as a **QRSPI demo**. Read this before making changes.

## Project goal

Monitor URLs in a foreground poll loop, detect DOWN/UP transitions, notify on stdout, log every check to stderr or a file. See `goal.md` and `thoughts/qrspi/2026-06-11-url-uptime-monitor/design.md` for full scope.

## Stack (do not change without explicit approval)

| Layer | Choice |
|-------|--------|
| Language | Python 3.11+ |
| CLI | `click` |
| HTTP | sync `httpx.Client` (not `requests`, not `AsyncClient`) |
| Config | `pydantic-settings` `BaseSettings` via `from_cli()` |
| Tests | `pytest`; mock HTTP with `httpx.MockTransport` |
| Package layout | `src/url_monitor/` |

**Not in scope:** FastAPI, asyncio concurrency, SQLite, config files, Slack/email, background daemons.

## Rules — configuration

1. **Never use `os.getenv()` or `os.environ` in application code.** All settings flow through `MonitorConfig` in `config.py`.
2. Merge CLI arguments into Pydantic via `from_cli()` — validate on startup, fail with exit code 1 on bad input.
3. Defaults: `--failure-threshold 3`, `--interval 30`, `--timeout 10`.

Source: `.cursor/rules/pydantic-settings.mdc`

## Rules — HTTP and I/O

1. Use **`httpx.Client`** (synchronous) for health checks in `checker.py`.
2. Follow redirects (`follow_redirects=True`).
3. A check **fails** when: HTTP status ≥ 400, or connection/timeout/DNS/SSL error.
4. **Sequential** URL checks only — simple `for url in urls` loop, no asyncio.
5. Do not add `requests`, `aiohttp`, or async event loops.

The FastAPI async rules in `docs/rules/fastapi/async_consistency.md` apply to **future web work only**, not this CLI.

## Rules — output channels

| Channel | Content |
|---------|---------|
| **stdout** | DOWN/UP transition notifications only (`notifier.py`) |
| **stderr** | Startup messages, shutdown messages, routine check logs (when no `--log-file`) |
| **log file** | Every check, append-only (`logger.py`, Phase 3) |

Do not print routine check results to stdout.

## Rules — state machine

Implement exactly as specified in `design.md`:

- States: `UNKNOWN` → `UP` / `DOWN`
- `consecutive_failures` increments on fail, resets on success
- Notify on: `UP→DOWN` (threshold reached), `DOWN→UP` (first success), `UNKNOWN→DOWN`
- Silent on: `UNKNOWN→UP` (log only)

## Rules — errors and exceptions

- FastAPI JSON error handlers (`docs/rules/fastapi/structured_error_response.md`) **do not apply** to this CLI.
- Use simple domain exceptions internally if needed; surface errors as log lines or CLI error messages.
- Exit code `0` on clean shutdown; `1` on startup/config errors.

## Rules — implementation workflow (QRSPI)

This project was developed with QRSPI. When extending it:

1. **Read artifacts first** — `thoughts/qrspi/2026-06-11-url-uptime-monitor/plan.md` is the source of truth for remaining work.
2. **One phase at a time** — implement Phase 2 before Phase 3; verify with `pytest` after each phase.
3. **Do not skip ahead** or refactor unrelated code.
4. **Greenfield changes** need clarifying questions (`/question`); brownfield changes need research (`/research`).
5. Agent skills live in `.cursor/skills/` — follow them when running QRSPI phases.

## Rules — testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

- Mock HTTP with `httpx.MockTransport` — no live network in unit tests.
- Use `click.testing.CliRunner` for CLI tests.
- Never let tests enter infinite poll loops — patch `time.sleep` or pre-set shutdown flags.

## Rules — commits and scope

- Only implement what `design.md` and `plan.md` describe.
- Do not add features from the "What We're NOT Doing" section in `design.md`.
- Do not introduce new dependencies without justification.
- Keep changes minimal and focused.

## Key files

| File | Purpose |
|------|---------|
| `src/url_monitor/cli.py` | Click entry point |
| `src/url_monitor/config.py` | Pydantic settings |
| `src/url_monitor/checker.py` | HTTP checks, `CheckResult` |
| `thoughts/qrspi/.../plan.md` | Implementation plan with verification checkboxes |
| `thoughts/qrspi/.../design.md` | Architecture and scope boundaries |
| `README.md` | Human-oriented project overview |

## Current status

- **Phase 1 done:** single-round CLI checks to stderr
- **Phase 2 planned:** state machine + stdout notifications
- **Phase 3 planned:** poll loop, logging, graceful shutdown

Pick up implementation from the first unchecked item in `plan.md`.
