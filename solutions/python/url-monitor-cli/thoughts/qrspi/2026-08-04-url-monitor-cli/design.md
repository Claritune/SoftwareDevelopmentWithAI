# Design Discussion

## Current State

Greenfield Python project. The repository contains only the goal document and QRSPI workflow artifacts. A C++ implementation (`url-monitor-cli-cpp`) exists as a reference for architecture and behavior, but this is an independent Python implementation.

**What exists today:**

| Artifact | Purpose |
|---|---|
| `goal.md` | One-line product goal: URL uptime monitor with scheduled checks and down/up notifications |
| C++ reference solution | Working `urlmon` binary with identical feature set — architecture to mirror |

There are no Python source files, no `pyproject.toml`, no tests, and no CI configuration.

## Desired End State

A Python 3.11+ package (`url-monitor`) installable via `pip install -e .` that:

1. Reads a YAML config file specifying URLs to monitor, a global check interval, and optional per-URL timeouts.
2. Runs as a foreground long-lived process, checking each URL sequentially on schedule.
3. Classifies each URL as **up** or **down** — **only HTTP 200 is success**; all other outcomes are down.
4. Persists last-known state and cumulative response statistics per URL in a JSON sidecar file.
5. Logs state transitions (down to up, up to down) to stdout with ISO 8601 timestamps.
6. Handles `SIGINT`/`SIGTERM` gracefully — finishes the current check, saves state, prints stats summary, exits cleanly.

**Verification checklist:**

- [ ] `url-monitor --config config/example.yaml` starts and enters the check loop
- [ ] HTTP 200 endpoints stay silent after baseline (no transition noise)
- [ ] Non-200 endpoints trigger a single `DOWN` notification
- [ ] Recovery to 200 triggers a single `UP` notification
- [ ] Restart with persisted state does not re-emit `DOWN`
- [ ] `url-monitor --stats --config config/example.yaml` prints per-URL counters
- [ ] Stats survive restarts
- [ ] `Ctrl+C` exits gracefully within ~200ms, saves state, prints summary
- [ ] `url-monitor --help` documents all flags

## Design Decisions

1. **Package layout**: `src/url_monitor/` with `__main__.py` as entry point. Installable via `pyproject.toml` with `[project.scripts]` entry.

2. **Modules** (mirrors C++ solution):
   - `config.py` — `argparse` CLI parsing + YAML config loading/validation
   - `checker.py` — `httpx`-based HTTP checking + status classification
   - `notifier.py` — stdout/stderr logging, transition emission, `iso8601_now()`
   - `state.py` — JSON sidecar load/save (atomic via `tempfile.mkstemp` + `os.replace`), state reconciliation
   - `stats.py` — per-URL counter accumulation + stats formatting
   - `monitor.py` — main check loop, signal handling, interruptible sleep

3. **Data types** (dataclasses):
   - `UrlSpec(url, timeout_seconds=10)`, `Config(check_interval_seconds, urls)`
   - `Status` enum: `Unknown`, `Up`, `Down`
   - `CheckResult(http_status, error, total_ms)`
   - `UrlStats(total_checks, up_checks, down_checks, http_status, errors)`
   - `UrlState(status, last_checked, stats)`, `StateStore(version, urls)`

4. **Classification rule**: `Up` only if `error is None and http_status == 200`. Everything else = `Down`.

5. **Signal handling**: Module-level `_shutdown_requested` boolean, set by `signal.signal(SIGINT/SIGTERM)` handler. Sleep implemented as 200ms slices checking the flag.

6. **Error key mapping**: `httpx` exceptions mapped to stable string keys (`connection_timeout`, `connection_refused`, `too_many_redirects`, etc.) via `_error_key()` in checker.

7. **State persistence**: JSON with `version` field, `urls` dict keyed by URL string. Atomic write via temp file + `os.replace()`. Missing file = empty store, corrupt file = warning + empty store.

8. **Stats format**: Matches C++ output with `errors` label instead of `curl`.

## What We're NOT Doing

- External notification channels (email, Slack, webhooks)
- Async HTTP via `httpx.AsyncClient` or `asyncio`
- Web dashboard or REST API
- Historical metrics or time-series storage
- Concurrent/parallel URL checks
- Per-URL check intervals
- Authentication or multi-user support
- Retry/backoff within a check cycle
- Config hot-reload
- Structured logging (JSON logs)

## Open Risks

| Risk | Mitigation |
|---|---|
| **`datetime.utcnow()` deprecated in 3.12+** | Known; use `datetime.now(timezone.utc)` if targeting 3.12+ strictly |
| **httpx connection overhead per check** | Reuse `httpx.Client` across checks within a cycle; close on shutdown |
| **False positives on flaky networks** | v1 accepts this; document single-check flip behavior |
| **Strict 200-only rule** | Document clearly; redirects are followed, so final 200 counts as up |
| **State file growth** | Counter keys are bounded (HTTP status codes + error types), so growth is limited |
| **Signal handling in Python** | `signal.signal()` only works in the main thread; fine for this single-threaded CLI |
