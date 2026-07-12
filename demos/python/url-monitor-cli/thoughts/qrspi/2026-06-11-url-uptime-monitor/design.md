# Design Discussion

## Current State

Greenfield project — no application code, tests, or dependency manifest exist.

Documented constraints in the repo:

- **Configuration via Pydantic Settings** — no direct `os.getenv()`; settings validated through a `BaseSettings` class (`.cursor/rules/pydantic-settings.mdc:9-22`). Rule examples show FastAPI DI injection (`.cursor/rules/pydantic-settings.mdc:24`) — not applicable to a pure CLI, but the Settings class pattern still applies.
- **HTTP client preference** — `httpx.AsyncClient` over `requests` ( `docs/rules/fastapi/async_consistency.md:5`). Written for FastAPI async routes; this CLI is synchronous and sequential, so `httpx.Client` (sync) is the aligned choice.
- **FastAPI error handlers** — domain exceptions + `JSONResponse` handlers (`docs/rules/fastapi/structured_error_response.md:6-34`). FastAPI-specific; not applicable to a stdout CLI.
- **Async I/O conventions** — async routes, `aiofiles`, etc. (`docs/rules/fastapi/async_consistency.md:3-15`). Out of scope for v1 sequential CLI.

## Desired End State

A pure Python CLI that monitors one or more URLs in a **foreground poll loop**, detects status transitions, and prints notifications to stdout.

### Invocation

```bash
url-monitor https://example.com https://api.example.com/health \
  --failure-threshold 3 \
  --interval 30 \
  --timeout 10 \
  --log-file monitor.log
```

All flags have defaults; URLs are required positional arguments.

### Behavior

1. Start a poll loop. Check each URL **sequentially** every `--interval` seconds.
2. Per URL, perform an HTTP GET with `--timeout` seconds.
3. A single check **fails** if: HTTP status >= 400, or connection/timeout/DNS/SSL error (Option A).
4. Track consecutive failure count per URL in memory. When failures reach `--failure-threshold`, transition to **DOWN** and print a notification to stdout.
5. While DOWN, a successful check resets the consecutive counter. After one success, transition to **UP** and print a recovery notification to stdout.
6. Every check (pass or fail) is appended to the log file if `--log-file` is set; otherwise log to stderr.
7. Run until the user sends SIGINT/SIGTERM (Ctrl+C). Print a shutdown message and exit cleanly.

### Verification

- Point at a known-good URL → no DOWN notification; periodic check logs only.
- Point at a URL returning 404/500 → after 3 consecutive failures, stdout shows DOWN notification.
- Restore a working response → stdout shows UP notification.
- Ctrl+C → graceful exit, no orphaned state (in-memory only).
- `pytest` passes for checker logic, state transitions, and CLI argument parsing.

## Patterns to Follow

| Pattern | Apply? | Source |
|---------|--------|--------|
| Pydantic `BaseSettings` for CLI flags and defaults | **Yes** — adapt for CLI, not FastAPI DI | `.cursor/rules/pydantic-settings.mdc:14-22` |
| `httpx` for HTTP checks | **Yes** — sync `httpx.Client` | `docs/rules/fastapi/async_consistency.md:5` |
| No `os.getenv()` in application code | **Yes** | `.cursor/rules/pydantic-settings.mdc:9` |
| FastAPI async route conventions | **No** — pure sync CLI | `docs/rules/fastapi/async_consistency.md:3` |
| FastAPI structured JSON error responses | **No** — errors go to logs/stdout as text | `docs/rules/fastapi/structured_error_response.md:36` |
| Domain exception classes for internal errors | **Adapt** — simple exception types, no HTTP handlers | inspired by `structured_error_response.md:8-12` |

## Design Decisions

1. **Execution model**: Foreground poll loop until SIGINT (Q1 Option B). Reconciles "one-shot command" (single invocation, no background daemon) with up/down transition detection. Not a cron-installed daemon.

2. **Configuration source**: URLs as positional CLI args; all tuning via flags with defaults (Q2 accepted). Parsed into a Pydantic Settings/CLI model at startup.

3. **CLI defaults**:
   - `--failure-threshold`: 3
   - `--interval`: 30 seconds
   - `--timeout`: 10 seconds
   - `--log-file`: optional; logs to stderr if omitted

4. **Failure criteria** (Q3 Option A): HTTP status >= 400, or connection/timeout/DNS/SSL error. Status 3xx after redirects resolve to the final response status.

5. **State machine per URL**:
   - States: `UNKNOWN` → `UP` / `DOWN`
   - `consecutive_failures` counter increments on fail, resets to 0 on success
   - Transition `UP → DOWN`: when `consecutive_failures >= failure_threshold`
   - Transition `DOWN → UP`: on first success after being DOWN
   - `UNKNOWN → UP`: on first success (no notification — only log)
   - `UNKNOWN → DOWN`: after threshold consecutive failures (notify)

6. **Notifications (stdout)**: Human-readable lines on transitions only:
   ```
   [2026-06-11T10:00:00Z] DOWN  https://example.com  (3 consecutive failures, last: HTTP 503)
   [2026-06-11T10:02:00Z] UP    https://example.com  (HTTP 200, 142ms)
   ```
   Regular check results go to the log, not stdout.

7. **Concurrency**: Sequential URL checks within each round (per user answer). Simple `for url in urls` loop.

8. **HTTP client**: Synchronous `httpx.Client` — no asyncio, no event loop. Matches sequential design; honors httpx preference from repo rules.

9. **CLI framework**: `click` for argument parsing and `--help`. Integrates cleanly with a Pydantic settings layer for validation.

10. **Persistence**: In-memory state dict keyed by URL for the duration of the process. Append-only log file for audit trail. No SQLite, no cross-run state.

11. **Graceful shutdown**: Register SIGINT/SIGTERM handler; finish current check round if in progress, then exit with code 0.

12. **Exit codes**: 0 on clean shutdown; 1 on startup errors (no URLs provided, invalid flags).

## Project Structure

```
demo_url_monitor/
├── pyproject.toml              # deps: click, httpx, pydantic-settings
├── src/
│   └── url_monitor/
│       ├── __init__.py
│       ├── __main__.py         # python -m url_monitor entry
│       ├── cli.py              # click commands and flag definitions
│       ├── config.py           # Pydantic Settings for CLI options
│       ├── checker.py          # HTTP GET + failure classification
│       ├── state.py            # per-URL state machine + transition detection
│       ├── notifier.py         # stdout transition messages
│       ├── logger.py           # structured check logging (file or stderr)
│       └── monitor.py          # poll loop + signal handling
└── tests/
    ├── test_checker.py
    ├── test_state.py
    └── test_cli.py
```

## Data Flow

```
CLI args → config.py (validate)
  → monitor.py starts loop
    → for each URL (sequential):
        → checker.check(url, timeout) → CheckResult
        → state.update(url, result) → optional Transition
        → logger.log(result)
        → if Transition: notifier.notify(transition) → stdout
    → sleep(interval)
    → repeat until signal
```

### CheckResult (in checker.py)

| Field | Type | Description |
|-------|------|-------------|
| `url` | str | Target URL |
| `success` | bool | Check passed per failure criteria |
| `status_code` | int \| None | HTTP status if response received |
| `response_time_ms` | float \| None | Round-trip time |
| `error` | str \| None | Error message on connection/timeout failure |
| `timestamp` | datetime | UTC time of check |

## What We're NOT Doing

- Background daemon / systemd service installation
- Config files (YAML/JSON) — CLI args only for v1
- Slack, email, or webhook notifications
- SQLite or any database
- Concurrent / asyncio URL checks
- FastAPI or HTTP API layer
- Authentication headers or per-URL custom settings
- Historical analytics or web dashboard
- Cross-run state persistence (restarts begin fresh)
- Retry logic inside a single check (one GET per check)

## Open Risks

1. **Redirect handling**: `httpx` follows redirects by default. A 302 → 200 would count as success even if the original endpoint is misconfigured. Acceptable for v1; document behavior.

2. **Clock / sleep drift**: `time.sleep(interval)` after each full round means actual interval is `interval + check_duration`. Acceptable at 30s default; note in help text.

3. **Log file growth**: Unbounded append during long runs. No rotation in v1 — user manages disk space.

4. **"One-shot" naming**: The command runs until interrupted, which may surprise users expecting instant exit. Mitigate with clear help text: "Runs until Ctrl+C."

5. **Pydantic Settings + click integration**: Need a clean pattern to merge click args into Settings without `os.getenv()`. Straightforward but worth getting right in Step 1 of implementation.
