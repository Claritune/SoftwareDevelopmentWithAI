# Clarifying Questions

## Project Type
greenfield

## Goal Summary

Build a CLI tool that monitors a list of URLs for uptime, checks them on a schedule, and sends notifications when a site goes down or comes back up.

## Existing Constraints

- Configuration must use `pydantic_settings.BaseSettings` — no direct `os.getenv()` (`.cursor/rules/pydantic-settings.mdc`)
- HTTP calls should use `httpx.AsyncClient`, not `requests` (`docs/rules/fastapi/async_consistency.md`)
- Async I/O conventions documented for FastAPI routes — may or may not apply to a CLI daemon (`docs/rules/fastapi/async_consistency.md`)
- Structured error responses via domain exceptions and handlers — FastAPI-specific (`docs/rules/fastapi/structured_error_response.md`)

## Questions

1. **Runtime model**: Should this run as a long-lived daemon that polls continuously, a one-shot command (e.g. `--check-now`), or both?
   - *Why it matters*: Daemon needs signal handling, concurrent scheduling, and process lifecycle; one-shot is a simpler linear script.
   - *Default if unanswered*: Long-lived daemon with a `--check-now` flag for testing.

2. **URL list and configuration**: Where should monitored URLs and their settings (interval, timeout, headers) live?
   - *Why it matters*: YAML/JSON config file vs CLI args vs environment variables changes project structure and how users manage targets.
   - *Default if unanswered*: YAML config file with per-URL interval (default 30s) and timeout (default 10s).

3. **Notification channels**: What should "sends notifications" mean in practice?
   - *Why it matters*: Slack webhook, email, desktop notification, or stdout-only each need different modules, dependencies, and failure handling.
   - *Default if unanswered*: Slack webhook via HTTP POST plus stdout logging on status transitions.

4. **Persistence**: Should check results and status history be stored, and if so where?
   - *Why it matters*: In-memory loses history on restart; SQLite enables transition detection and audit trail; log-only is simpler but limits querying.
   - *Default if unanswered*: SQLite for check history and last-known status per URL.

5. **"Down" criteria**: What conditions count as a site being down?
   - *Why it matters*: HTTP status thresholds (e.g. >= 400), connection timeouts, DNS failures, and SSL errors each need explicit handling in the checker.
   - *Default if unanswered*: HTTP status >= 400 or connection timeout.

6. **Concurrency model**: Should URL checks run sequentially or concurrently?
   - *Why it matters*: Concurrent checks (asyncio) scale better with many URLs but add complexity; sequential is simpler but slower.
   - *Default if unanswered*: Concurrent checks via asyncio.

7. **Stack alignment**: The repo documents FastAPI conventions, but the goal specifies a CLI tool. Which stack should we build?
   - *Why it matters*: Pure CLI (click + asyncio) vs FastAPI with a background scheduler vs hybrid affects the entire architecture and which existing rules apply.
   - *Default if unanswered*: Pure Python CLI with click and asyncio — treat FastAPI rules as out of scope unless you want an API layer too.
