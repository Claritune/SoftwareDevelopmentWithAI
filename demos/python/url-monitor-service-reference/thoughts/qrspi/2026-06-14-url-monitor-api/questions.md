# Clarifying Questions

## Project Type
greenfield

## Goal Summary

Build a FastAPI service that monitors URLs for uptime in the background, stores configuration and check results in SQLite, and exposes a REST API for managing monitors and querying status. The service must run concurrent async health checks on a per-URL schedule, detect UP/DOWN transitions after consecutive failures, record all checks and transitions, and serve JSON endpoints without authentication.

## Existing Constraints

- **Pydantic Settings for all configuration** — no direct `os.getenv()`; inject via FastAPI dependencies (`.cursor/rules/pydantic-settings.mdc`)
- **Async I/O consistency** — async route handlers must use async libraries (`httpx.AsyncClient`, async DB access); no blocking calls inside `async def` routes (`docs/rules/fastapi/async_consistency.md`)
- **Structured error responses** — domain exceptions + global handlers; routes raise, never catch; schema `{"error": "<CODE>", "message": "<text>"}` (`docs/rules/fastapi/structured_error_response.md`)
- **Stack from goal.md** — Python 3.11+, FastAPI, SQLite, httpx, pytest, OpenAPI via route definitions; no auth, notifications, or web UI

## Questions

1. **SQLite access model**: Should persistence use fully async SQLite (`aiosqlite`, possibly with SQLAlchemy asyncio) or synchronous SQLite behind `asyncio.to_thread` / a thread pool?
   - *Why it matters*: Determines repository interfaces, test fixtures, and whether the async-consistency rule applies directly to DB calls or via explicit offloading.
   - *Default if unanswered*: Fully async stack — `aiosqlite` with thin async repository functions, matching the async-consistency rule without thread-pool indirection.

2. **Background scheduler design**: How should per-URL checks be scheduled — one asyncio task per enabled monitor with its own sleep loop, a single coordinator task that polls SQLite and dispatches concurrent checks, or a library scheduler (e.g. APScheduler)?
   - *Why it matters*: Affects how new/updated/disabled monitors are picked up, shutdown/cancellation behavior, and concurrency limits.
   - *Default if unanswered*: Single coordinator loop that reloads enabled monitors from SQLite on each cycle (or every N seconds), spawning concurrent `httpx` checks via `asyncio.gather` / task group — no external scheduler dependency.

3. **Monitor config refresh**: When a monitor is created, updated, enabled, or disabled via the API, how quickly should the background loop reflect the change?
   - *Why it matters*: Event-driven (in-memory registry updated on CRUD) vs periodic DB polling changes API–scheduler coupling and test timing.
   - *Default if unanswered*: Poll SQLite each scheduler cycle (e.g. every 1–5 s) for the enabled-monitor list; no in-process event bus.

4. **Initial status and first check**: When a new monitor is created, what is its status before the first check completes, and should the first check run immediately or only after the first interval elapses?
   - *Why it matters*: Drives schema defaults (`UNKNOWN` vs `UP`), transition recording, and integration-test expectations.
   - *Default if unanswered*: Status `UNKNOWN` until the first check completes; run the first check immediately on creation (or within the next scheduler cycle), then respect the configured interval.

5. **REST API shape and pagination**: What exact resource paths and pagination style should history endpoints use?
   - *Why it matters*: Locks OpenAPI schemas, router layout, and client contracts before implementation.
   - *Default if unanswered*: Plural REST resources under `/api/v1/` — e.g. `GET/POST /monitors`, `GET/PATCH/DELETE /monitors/{id}`, `GET /monitors/{id}/status`, `GET /status/summary`, `GET /monitors/{id}/checks` and `GET /monitors/{id}/transitions` with `limit` + `offset` query params (default limit 50); service health at `GET /health` (liveness) and `GET /ready` (DB reachable).

6. **Database schema and migrations**: Should the schema be created via raw SQL/`aiosqlite` scripts on startup, SQLAlchemy models with `create_all`, or Alembic migrations?
   - *Why it matters*: Affects project layout, test isolation (in-memory vs file DB), and how schema changes are managed during development.
   - *Default if unanswered*: SQLAlchemy 2.0 async models with `create_all` on application startup for this exercise; no Alembic unless you want migration history from day one.

7. **Dependency and project tooling**: Should the project use `uv` (with `pyproject.toml` + committed `uv.lock`) as the README suggests, or plain `pip` + `requirements.txt`?
   - *Why it matters*: Affects CI commands, hook scripts, and how students/agents install and run the service.
   - *Default if unanswered*: `uv` with `pyproject.toml`, dev extras for pytest/ruff, and a committed `uv.lock`.
