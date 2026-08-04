# Clarifying Questions

## Project Type
greenfield

## Goal Summary
Build a Python CLI tool that monitors a list of URLs for uptime, checks them on a schedule, and prints notifications when a site goes down or comes back up.

## Existing Constraints
- Python 3.11+ target runtime
- Mirrors the architecture of the existing C++ `urlmon` solution but uses Python-idiomatic libraries
- Must support `pip install -e .` development workflow via pyproject.toml

## Questions

### Scope

1. **Notification channels**: Should transitions be logged to stdout only, or do we need email/Slack/webhook support?
   - *Why it matters*: External notification channels require additional dependencies (e.g. `requests` for webhooks, `smtplib` for email), config schema extensions, and error handling for delivery failures.
   - *Default if unanswered*: Log state changes to stdout with ISO 8601 timestamps; no external integrations in v1.

2. **Concurrency model**: Should URL checks run sequentially or concurrently (e.g. via `asyncio` + `httpx.AsyncClient`)?
   - *Why it matters*: Async checks reduce total cycle time when monitoring many URLs with slow timeouts, but add complexity to signal handling, state management, and error propagation.
   - *Default if unanswered*: Sequential checks using `httpx.Client` (synchronous). Matches the C++ solution's model and simplifies state updates.

3. **Scope boundaries for v1**: What is explicitly out of scope?
   - *Why it matters*: Features like per-URL intervals, retry/backoff, config hot-reload, or a REST API each add significant design surface.
   - *Default if unanswered*: v1 covers sequential checks, state-change notifications, YAML config, JSON state persistence, graceful shutdown. Out of scope: web UI, async checks, retries, hot-reload, authentication.

### Technical

4. **HTTP library**: `httpx` (sync client, connection pooling, redirect support) vs. `requests` vs. `urllib3`?
   - *Why it matters*: `httpx` provides a modern API with built-in timeout objects and redirect control. `requests` is more widely used but lacks async support if we ever migrate. Library choice affects exception types in `checker.py`.
   - *Default if unanswered*: `httpx` with synchronous `Client`.

5. **Config format**: YAML via `pyyaml` vs. TOML via stdlib `tomllib` (3.11+)?
   - *Why it matters*: TOML is in the stdlib from 3.11, eliminating a dependency. YAML matches the C++ solution's config format and is more familiar for infrastructure tools.
   - *Default if unanswered*: YAML via `pyyaml`, matching the C++ solution.

6. **CLI parsing**: `argparse` (stdlib) vs. `click` vs. `typer`?
   - *Why it matters*: `click`/`typer` provide richer help formatting and subcommand support, but add dependencies for a simple flag-based CLI. `argparse` is zero-dependency.
   - *Default if unanswered*: `argparse` from stdlib.

7. **State file atomicity**: What approach for atomic writes on Python?
   - *Why it matters*: Python's `os.replace()` is atomic on POSIX. Combined with `tempfile.mkstemp()` in the same directory, this matches the C++ solution's tmp+rename pattern.
   - *Default if unanswered*: `tempfile.mkstemp()` + `os.replace()`.

### Output

8. **Notification format**: Should the output format match the C++ solution exactly?
   - *Why it matters*: Consistent format across implementations makes it easier to compare behavior and parse output with the same tools.
   - *Default if unanswered*: Match the C++ format: `<timestamp> <STATUS>  <url>  (<detail>)`.

9. **Stats output**: Same format as C++, with "errors" instead of "curl"?
   - *Why it matters*: Python uses `httpx` exceptions rather than curl error codes, so the error category label should reflect the library.
   - *Default if unanswered*: Same layout, `errors` label instead of `curl`.

### Testing

10. **Test framework**: `pytest` vs. `unittest`?
    - *Why it matters*: `pytest` is the de facto standard for Python projects, with cleaner assertion syntax and better fixture support. `unittest` is stdlib but more verbose.
    - *Default if unanswered*: `pytest`, listed as a dev dependency.

11. **Test scope**: Unit tests only, or also integration tests with mocked HTTP?
    - *Why it matters*: Mocked HTTP tests (via `respx` or `pytest-httpx`) would cover the `checker.py` module but add test dependencies and complexity.
    - *Default if unanswered*: Pure-logic unit tests only (classification, stats, state round-trip). Network behavior verified manually.

12. **Test coverage target**: Any minimum coverage requirement?
    - *Why it matters*: Setting a coverage floor (e.g. 80%) for the pure-logic modules ensures classification edge cases aren't missed.
    - *Default if unanswered*: No formal coverage target; focus on classification boundaries and stats accumulation.
