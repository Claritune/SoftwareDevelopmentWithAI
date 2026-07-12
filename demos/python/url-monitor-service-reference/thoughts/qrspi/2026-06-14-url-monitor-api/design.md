# Design Discussion

## Current State

Greenfield project: no application runtime code exists yet. The repo contains the product brief (`goal.md`), QRSPI workflow skills (`.cursor/skills/`), three coding-constraint documents, and Q-phase artifacts with user decisions (`answers.md`).

Documented constraints the implementation must follow:

- **Pydantic Settings only** — all config through a `BaseSettings` class; inject via FastAPI `Depends`, never `os.getenv()` directly (`.cursor/rules/pydantic-settings.mdc:9-26`)
- **Async I/O end-to-end** — `async def` routes use async libraries; no blocking calls inside async handlers; tests use `@pytest.mark.anyio` + `httpx.AsyncClient` with `ASGITransport` (`docs/rules/fastapi/async_consistency.md:3-15`)
- **Structured errors via handlers** — domain exceptions in `app/exceptions.py`; global handlers in `app/main.py`; routes raise, never catch (`docs/rules/fastapi/structured_error_response.md:3-36`)

The companion CLI demo (`../`) defines the domain vocabulary (HTTP GET checks, status ≥ 400 = fail, consecutive failures, UP/DOWN transitions) but its code is not copied — architecture, persistence, scheduler, and REST API are new work.

## Desired End State

A long-running FastAPI service that:

1. Persists monitor configuration and check history in SQLite across restarts.
2. Runs a background coordinator that checks enabled URLs concurrently without blocking API requests.
3. Exposes a versioned JSON REST API under `/api/v1/` for CRUD, history, and status summary.
4. Records every check result and every UP/DOWN transition with asymmetric threshold logic (3 failures → DOWN by default; 1 success → UP).
5. Starts the scheduler on app startup and shuts down cleanly on termination.
6. Passes a `pytest` suite and serves auto-generated OpenAPI docs at `/docs`.

**Verification checklist** (from `goal.md` success criteria):

- `POST /api/v1/monitors` → monitor appears in list; status `UNKNOWN`.
- Within one coordinator cycle (~5 s), background checks write rows to `checks`.
- After N consecutive failures against a bad endpoint, monitor status becomes `DOWN`; one success flips to `UP`.
- `GET /api/v1/monitors/{id}/checks` returns timestamps and HTTP status codes.
- `DELETE` or `PATCH` (disable) stops future checks; history retained.
- `uv run pytest` passes; `/docs` is interactive.

## Patterns to Follow

| Pattern | Source | Apply? |
|---------|--------|--------|
| `Settings` class + DI injection | `pydantic-settings.mdc:13-26` | Yes — `app/settings.py`, `get_settings()` dependency |
| `async def` routes + async I/O libs | `async_consistency.md:3-10` | Yes — `aiosqlite`, `httpx.AsyncClient` |
| `httpx.AsyncClient` + `ASGITransport` in tests | `async_consistency.md:15` | Yes — no sync `TestClient` for route tests |
| Domain exceptions + global handlers | `structured_error_response.md:6-34` | Yes — `AppError`, `NotFoundError`, etc. |
| Routes raise, no try/except bodies | `structured_error_response.md:26-34` | Yes |
| Error JSON shape `{"error", "message"}` | `structured_error_response.md:36` | Yes — including 422 validation errors |

**Adaptation for SQLite:** The async-consistency rule cites `asyncpg`/SQLAlchemy as the PostgreSQL example (`async_consistency.md:4`). For this exercise, the equivalent is `aiosqlite` with async repository functions — same principle, different driver.

**Do NOT follow:** SQLAlchemy async sessions, APScheduler, sync `sqlite3` in async routes, `os.getenv()` scattered in modules, try/except in route handlers, or copying CLI demo file structure verbatim.

## Design Decisions

### 1. Persistence: `aiosqlite` + raw SQL repositories
Thin async repo functions (`app/db/repositories/`) execute parameterized SQL against a shared `aiosqlite.Connection`. Schema defined in `app/db/schema.sql`, applied via `CREATE TABLE IF NOT EXISTS` on startup. No ORM, no Alembic.

### 2. Database schema (3 tables)

**`monitors`** — configuration + current runtime state:
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `url` TEXT NOT NULL UNIQUE
- `display_name` TEXT
- `enabled` INTEGER NOT NULL DEFAULT 1
- `check_interval_seconds` INTEGER NOT NULL DEFAULT 60
- `timeout_seconds` INTEGER NOT NULL DEFAULT 10
- `failure_threshold` INTEGER NOT NULL DEFAULT 3
- `status` TEXT NOT NULL DEFAULT `'UNKNOWN'` — enum: `UNKNOWN`, `UP`, `DOWN`
- `consecutive_failures` INTEGER NOT NULL DEFAULT 0
- `last_checked_at` TEXT (ISO-8601 UTC)
- `created_at`, `updated_at` TEXT NOT NULL

**`checks`** — every HTTP probe result:
- `id`, `monitor_id` FK, `checked_at`, `http_status` (nullable), `response_time_ms`, `success` (0/1), `error_message`

**`transitions`** — status changes only:
- `id`, `monitor_id` FK, `transitioned_at`, `from_status`, `to_status`, `check_id` FK

`consecutive_failures` lives on `monitors` so the checker can evaluate threshold without scanning history.

### 3. Background scheduler: coordinator + `asyncio.TaskGroup`
Single long-lived asyncio task started in FastAPI lifespan (`app/services/scheduler.py`):

```
loop forever:
    sleep(coordinator_tick_seconds)          # default 5 s, from Settings
    load enabled monitors from SQLite
    for each monitor:
        if last_checked_at is NULL or elapsed >= check_interval_seconds:
            add to this cycle's check batch
    async with TaskGroup() as tg:
        for monitor in batch:
            tg.create_task(run_check(monitor))
```

- **Per-URL interval** enforced via `last_checked_at` + `check_interval_seconds` — not every monitor checked every tick.
- **Config refresh** implicit: each cycle re-reads enabled monitors from DB; no event bus.
- **First check**: `last_checked_at` is NULL → eligible on first cycle after creation; status stays `UNKNOWN` until then.
- **Testability**: expose `run_cycle()` (single iteration) for unit/integration tests without waiting real time.

### 4. HTTP checker (`app/services/checker.py`)
Pure async function: `check_url(url, timeout) -> CheckResult` using a shared `httpx.AsyncClient` (created in lifespan, stored on `app.state`).

- **Success**: HTTP status < 400; record status code and response time.
- **Failure**: status ≥ 400, timeout, or connection error; record error message.
- **State machine** (after persisting check):
  - On success: reset `consecutive_failures` to 0; if status was `DOWN`, transition to `UP` and record transition; if `UNKNOWN`, set `UP` and record first transition (`UNKNOWN → UP`).
  - On failure: increment `consecutive_failures`; if status is `UP` (or `UNKNOWN` with failures ≥ threshold) and `consecutive_failures >= failure_threshold`, transition to `DOWN` and record transition.
  - No transition recorded when failures accumulate but threshold not yet met.

### 5. REST API layout

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/monitors` | Create monitor |
| GET | `/api/v1/monitors` | List (`limit`/`offset`) |
| GET | `/api/v1/monitors/{id}` | Detail + current status fields |
| PATCH | `/api/v1/monitors/{id}` | Update config |
| DELETE | `/api/v1/monitors/{id}` | Delete monitor + cascade history |
| GET | `/api/v1/monitors/{id}/checks` | Paginated check history |
| GET | `/api/v1/monitors/{id}/transitions` | Paginated transitions |
| GET | `/api/v1/status/summary` | Counts by status + per-monitor snapshot |
| GET | `/health` | Liveness (process up) |
| GET | `/ready` | Readiness (DB connection OK) |

Pydantic request/response models in `app/schemas/`. Routers split: `app/routers/monitors.py`, `app/routers/health.py`.

### 6. Application lifecycle (`app/main.py`)
FastAPI lifespan context manager:
1. Open `aiosqlite` connection, run schema init.
2. Create shared `httpx.AsyncClient`.
3. Start coordinator task (holds cancel handle).
4. On shutdown: cancel coordinator; `TaskGroup` cancels in-flight checks; close httpx client and DB connection.

API handlers and scheduler share the same DB connection (SQLite handles concurrent readers; writes serialized by `aiosqlite`). Acceptable for this exercise scale.

### 7. Configuration (`app/settings.py`)
`Settings(BaseSettings)` fields: `database_path`, `coordinator_tick_seconds` (default 5), `default_check_interval_seconds` (60), `default_timeout_seconds` (10), `default_failure_threshold` (3), `host`, `port`. Loaded from env / `.env`; injected via `Depends(get_settings)`.

### 8. Error handling extensions
Beyond domain `AppError` handlers (`structured_error_response.md:19-24`):
- `RequestValidationError` handler → 422 with `{"error": "VALIDATION_ERROR", "message": "..."}`.
- `IntegrityError` (duplicate URL) → 409 `CONFLICT`.

### 9. Project layout and tooling

```
app/
  main.py           # FastAPI app, lifespan, exception handlers
  settings.py
  exceptions.py
  dependencies.py   # get_db, get_settings, get_checker deps
  db/
    connection.py   # open/close, schema init
    schema.sql
  repositories/
    monitors.py
    checks.py
    transitions.py
  services/
    checker.py
    scheduler.py
  routers/
    monitors.py
    health.py
  schemas/
    monitors.py
    checks.py
    common.py       # pagination params
tests/
  conftest.py       # in-memory :memory: DB fixture
  test_checker.py
  test_scheduler.py
  test_api_monitors.py
  test_api_history.py
pyproject.toml      # uv, dev extras: pytest, ruff, httpx
```

Managed with `uv`; `uv.lock` committed. Dev dependency group for test/lint tools.

### 10. Testing strategy
- **Unit**: checker logic (mock httpx), state-machine transitions with in-memory DB.
- **Scheduler**: `run_cycle()` with mocked or local httpx transport.
- **API**: `httpx.AsyncClient` + `ASGITransport(app)` per `async_consistency.md:15`; in-memory SQLite per test via shared schema init.
- **Integration**: create monitor → run one scheduler cycle → assert check row and status change.

## What We're NOT Doing

- Authentication, API keys, multi-tenancy
- Push notifications (Slack, email, webhooks)
- Web UI / dashboard
- Distributed / multi-node monitoring
- Metrics, Prometheus, log rotation
- Per-URL custom headers or authenticated target URLs
- SQLAlchemy, Alembic, APScheduler
- Event-driven scheduler refresh (production sidebar only)
- Immediate check on monitor creation (API/scheduler stay decoupled)
- Separate `/monitors/{id}/status` endpoint

## Open Risks

| Risk | Mitigation |
|------|------------|
| SQLite write contention under heavy concurrent checks | Single-writer is fine at exercise scale; repos use short transactions. Revisit if load testing reveals bottlenecks. |
| Coordinator tick vs. per-monitor interval confusion in tests | Document that a monitor with 60 s interval won't be re-checked every 5 s tick; tests use short intervals (1–2 s). |
| `TaskGroup` exception propagation cancels sibling checks | Acceptable — one bad monitor doesn't corrupt others; failed task logged, cycle continues next tick. |
| Shared DB connection across tasks | `aiosqlite` serializes writes; reads during write may see brief delay. Monitor per-check writes in discrete transactions. |
| Graceful shutdown mid-TaskGroup | Lifespan cancellation stops coordinator; partial check results for cancelled tasks may be dropped — acceptable for exercise. |
