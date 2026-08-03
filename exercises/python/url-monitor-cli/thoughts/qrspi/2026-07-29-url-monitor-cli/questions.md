# Clarifying Questions

## Project Type
greenfield

## Goal Summary
Build a Python CLI tool that monitors a list of URLs for uptime. It polls each
URL on a schedule and prints notifications when a site changes state — goes down
or comes back up. The deliverable is a small, terminal-run monitoring utility.

## Existing Constraints
No committed rules, conventions, or scaffolding (no `.cursor/rules/`, `docs/rules/`,
`src/`, or `pyproject.toml`). The exercise README states this is greenfield and
that implementation should target **Python 3.11+**.

Observed hint (not an enforced constraint): a leftover `.venv/` has a
`url-monitor 0.1.0` package installed declaring `click>=8.1`, `httpx>=0.27`,
`pydantic-settings>=2.0`, and `pytest>=8.0` as dev. Treat these as a suggested
stack to confirm or override, not a decision already made.

## Questions

1. **Runtime model**: Should the tool run as a long-lived foreground process that
   loops on the schedule until Ctrl-C, or as a one-shot "check once and exit"
   command (with scheduling delegated to cron/systemd)?
   - *Why it matters*: Determines whether we build an internal scheduler loop and
     signal handling, or a stateless single-pass command. This is the single
     biggest architectural fork.
   - *Default if unanswered*: Long-lived foreground process that loops every
     `--interval` seconds until interrupted.

2. **URL source**: Where do the monitored URLs come from — positional CLI
   arguments, a config file (e.g. YAML/JSON/TOML), or both?
   - *Why it matters*: Drives the config layer and argument parsing. A config file
     also implies per-URL overrides (timeouts, expected status) vs. flat globals.
   - *Default if unanswered*: URLs as positional CLI args, with global flags
     (`--interval`, `--timeout`, `--failure-threshold`) applying to all.

3. **Definition of "down"**: What counts as down — any single failed request, or
   N consecutive failures (`--failure-threshold`)? And is "failure" only
   connection errors/timeouts, or also non-2xx HTTP status codes?
   - *Why it matters*: Defines per-URL state tracking (consecutive-failure
     counters, state machine) and what triggers a DOWN/UP notification.
   - *Default if unanswered*: DOWN after N consecutive failures
     (`--failure-threshold`, default 3); a failure is any timeout, connection
     error, or non-2xx status.

4. **HTTP library and I/O model**: Which HTTP client, sync or async — `httpx`
   (sync), `httpx` (async), `requests`, or stdlib `urllib`? Should URLs be checked
   concurrently or sequentially within a cycle?
   - *Why it matters*: Async + concurrency matters for many URLs; sync sequential
     is simpler. Choice shapes the core check function and testing approach.
   - *Default if unanswered*: `httpx` synchronous, checking URLs sequentially per
     cycle (follows the venv hint; simplest to test).

5. **Notification channels & output format**: Are notifications stdout-only, or
   also delivered to a log file and/or external channels (Slack/email)? What is
   the exact line format for state-change events?
   - *Why it matters*: External channels add config, secrets, and dependencies.
     The line format is a user-facing contract that later steps depend on.
   - *Default if unanswered*: stdout only, with optional `--log-file` mirroring the
     same lines. Format like:
     `[2026-06-11T10:00:00Z] DOWN  https://example.com  (3 consecutive failures, last: HTTP 503)`.

6. **Notification trigger policy**: Should the tool print only on state
   *transitions* (down→up, up→down), or also emit per-check status each cycle
   (e.g. a periodic heartbeat/summary)?
   - *Why it matters*: Transition-only keeps output quiet and event-driven;
     per-check output changes the logging volume and the state model.
   - *Default if unanswered*: Print only on state transitions; optionally a
     `--verbose` flag for per-check lines.

7. **Testing & packaging**: How is this verified and installed — `pytest` unit
   tests with a mocked HTTP layer, and installed as a `pip`/`uv` package exposing
   a `url-monitor` console entry point?
   - *Why it matters*: Determines project layout (`src/` package + `pyproject.toml`
     with an entry point) and how the schedule/network are made testable
     (injecting a clock and HTTP client).
   - *Default if unanswered*: `pyproject.toml` with a `url-monitor` console script,
     `pytest` tests mocking HTTP and time so no real network/sleep is needed.
