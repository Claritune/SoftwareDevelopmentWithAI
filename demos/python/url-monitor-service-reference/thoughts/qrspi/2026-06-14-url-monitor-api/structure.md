# Structure Outline

## Approach

Build bottom-up in vertical slices: each phase delivers a testable end-to-end capability crossing config, persistence, service, and API layers. Early phases establish the runnable skeleton and CRUD API; middle phases add the checker state machine and background coordinator; the final phase exposes history/summary endpoints and locks in full integration coverage. Signatures and types only — implementation detail deferred to `/plan`.

---

## Phase 1: Runnable Skeleton & Health Endpoints

Delivers a bootable FastAPI app with `uv`, Pydantic settings, SQLite schema init, structured error handling, and liveness/readiness probes — no monitors or scheduler yet.

**Files**: `pyproject.toml`, `app/main.py`, `app/settings.py`, `app/exceptions.py`, `app/dependencies.py`, `app/db/connection.py`, `app/db/schema.sql`, `app/routers/health.py`, `tests/conftest.py`, `tests/test_health.py`

**Key changes**:
- `Settings(BaseSettings)` — `database_path: str`, `coordinator_tick_seconds: int = 5`, `default_check_interval_seconds: int = 60`, `default_timeout_seconds: int = 10`, `default_failure_threshold: int = 3`, `host: str`, `port: int`
- `async def open_db(path: str) -> aiosqlite.Connection` — open connection
- `async def init_schema(conn: aiosqlite.Connection) -> None` — execute `schema.sql`
- `async def get_db(request: Request) -> aiosqlite.Connection` — DI dependency
- `class AppError(Exception)`, `class NotFoundError(AppError)` — domain exceptions
- `GET /health -> {"status": "ok"}`, `GET /ready -> {"status": "ready"}` — readiness probes DB with `SELECT 1`
- Lifespan: open DB, init schema, yield, close DB (no httpx client or scheduler yet)

**Verify**: `uv sync --extra dev && uv run pytest tests/test_health.py -v` passes; `uv run uvicorn app.main:app` → `GET /health` returns 200, `GET /ready` returns 200, `GET /docs` loads.

---

## Phase 2: Monitor CRUD API

Delivers full monitor configuration management persisted in SQLite — create, list, detail, update, delete — with `UNKNOWN` initial status and structured validation/conflict errors.

**Files**: `app/repositories/monitors.py`, `app/schemas/monitors.py`, `app/schemas/common.py`, `app/routers/monitors.py`, `tests/test_api_monitors.py`

**Key changes**:
- `class MonitorStatus(str, Enum)` — `UNKNOWN`, `UP`, `DOWN`
- `class MonitorRow(TypedDict)` — DB row shape (`id`, `url`, `display_name`, `enabled`, `check_interval_seconds`, `timeout_seconds`, `failure_threshold`, `status`, `consecutive_failures`, `last_checked_at`, `created_at`, `updated_at`)
- `class MonitorCreate(BaseModel)` — `url: HttpUrl`, optional `display_name`, `check_interval_seconds`, `timeout_seconds`, `failure_threshold`, `enabled`
- `class MonitorUpdate(BaseModel)` — all fields optional
- `class MonitorResponse(BaseModel)` — full monitor including status fields
- `class PaginatedMonitors(BaseModel)` — `items: list[MonitorResponse]`, `total: int`, `limit: int`, `offset: int`
- `async def create_monitor(conn, data: MonitorCreate, settings: Settings) -> MonitorRow`
- `async def list_monitors(conn, limit: int, offset: int) -> tuple[list[MonitorRow], int]`
- `async def get_monitor(conn, monitor_id: int) -> MonitorRow | None`
- `async def update_monitor(conn, monitor_id: int, data: MonitorUpdate) -> MonitorRow | None`
- `async def delete_monitor(conn, monitor_id: int) -> bool`
- Routes: `POST/GET /api/v1/monitors`, `GET/PATCH/DELETE /api/v1/monitors/{id}`
- `IntegrityError` → 409 `CONFLICT` on duplicate URL; `NotFoundError` on missing id

**Verify**: `uv run pytest tests/test_api_monitors.py -v` passes; manual `POST /api/v1/monitors` then `GET /api/v1/monitors` shows entry with `status: "UNKNOWN"`.

---

## Phase 3: HTTP Checker & State Machine

Delivers the core domain logic: probe a URL with httpx, persist a check row, update consecutive-failure counter, and record transitions — callable directly without the scheduler.

**Files**: `app/repositories/checks.py`, `app/repositories/transitions.py`, `app/services/checker.py`, `tests/test_checker.py`

**Key changes**:
- `class CheckResult(BaseModel)` — `success: bool`, `http_status: int | None`, `response_time_ms: int`, `error_message: str | None`
- `class CheckRow(TypedDict)`, `class TransitionRow(TypedDict)` — DB shapes
- `async def check_url(client: httpx.AsyncClient, url: str, timeout: float) -> CheckResult`
- `async def insert_check(conn, monitor_id: int, result: CheckResult) -> int` — returns `check_id`
- `async def insert_transition(conn, monitor_id: int, from_status: str, to_status: str, check_id: int) -> None`
- `async def process_monitor_check(conn, client: httpx.AsyncClient, monitor: MonitorRow) -> None` — probe → insert check → apply state machine → update `monitors` row
- State machine rules: success resets failures; `UNKNOWN→UP` or `DOWN→UP` on success; `UP→DOWN` (or `UNKNOWN→DOWN` after threshold) on N consecutive failures

**Verify**: `uv run pytest tests/test_checker.py -v` passes; tests seed a monitor in `:memory:` DB, call `process_monitor_check` with mocked httpx transport, assert `checks` row, `monitors.status`, and `transitions` row as expected for success/failure/threshold scenarios.

---

## Phase 4: Background Scheduler & Lifespan

Wires the coordinator into app startup: polls enabled monitors every tick, fans out due checks via `TaskGroup`, respects per-monitor intervals — background monitoring runs without API intervention.

**Files**: `app/services/scheduler.py`, `app/main.py` (lifespan extended), `tests/test_scheduler.py`, `tests/conftest.py` (shared httpx client fixture)

**Key changes**:
- `async def get_monitors_due_for_check(conn, now: datetime) -> list[MonitorRow]` — enabled monitors where `last_checked_at IS NULL` or interval elapsed
- `async def run_cycle(conn, client: httpx.AsyncClient, settings: Settings) -> None` — load due monitors, `TaskGroup` of `process_monitor_check`
- `async def start_scheduler(conn, client, settings) -> asyncio.Task` — background loop with `asyncio.sleep(tick)`
- `async def stop_scheduler(task: asyncio.Task) -> None` — cancel and await
- Lifespan extended: create shared `httpx.AsyncClient` on `app.state`, start/stop scheduler task
- `process_monitor_check` updates `last_checked_at` after each check

**Verify**: `uv run pytest tests/test_scheduler.py -v` passes; integration test creates monitor via repo, calls `run_cycle` twice with mocked transport (failing then succeeding), asserts status transitions and multiple check rows.

---

## Phase 5: History, Summary API & End-to-End Integration

Delivers read endpoints for check history, transitions, and aggregate status — plus full goal.md success-criteria coverage and remaining error-handler polish.

**Files**: `app/schemas/checks.py`, `app/routers/monitors.py` (history routes added), `app/routers/health.py` (unchanged), `tests/test_api_history.py`, `tests/test_integration.py`

**Key changes**:
- `class CheckResponse(BaseModel)`, `class TransitionResponse(BaseModel)` — API shapes
- `class PaginatedChecks(BaseModel)`, `class PaginatedTransitions(BaseModel)`
- `class StatusSummary(BaseModel)` — `total: int`, `up: int`, `down: int`, `unknown: int`, `monitors: list[MonitorSummary]`
- `async def list_checks(conn, monitor_id: int, limit: int, offset: int) -> tuple[list[CheckRow], int]`
- `async def list_transitions(conn, monitor_id: int, limit: int, offset: int) -> tuple[list[TransitionRow], int]`
- `async def get_status_summary(conn) -> StatusSummary`
- Routes: `GET /api/v1/monitors/{id}/checks`, `GET /api/v1/monitors/{id}/transitions`, `GET /api/v1/status/summary`
- `RequestValidationError` handler → 422 `VALIDATION_ERROR`
- `tests/test_integration.py`: create monitor via API → `run_cycle` (scheduler helper) → `GET` detail shows `UP`/`DOWN` → `GET` checks returns timestamps → disable monitor → `run_cycle` confirms no new checks

**Verify**: `uv run pytest -v` full suite passes; manual flow: start server, `POST` monitor pointing at failing URL, wait ~5 s, `GET /api/v1/monitors/{id}` shows `DOWN` after threshold, `GET .../checks` shows history, `PATCH` `enabled: false`, confirm checks stop.

---

## Testing Checkpoints

| After Phase | What is true |
|-------------|--------------|
| **1** | App starts; schema exists; `/health` and `/ready` work; error handlers registered; pytest infra ready |
| **2** | Monitors CRUD via REST; `UNKNOWN` on create; duplicate URL → 409; delete removes monitor |
| **3** | Single check persists result + updates status/transitions; threshold logic correct in isolation |
| **4** | Background coordinator runs on lifespan; `run_cycle` testable; per-monitor interval respected; disabled monitors skipped |
| **5** | All API endpoints live; full `pytest` green; goal.md success criteria met; `/docs` interactive |

## Resume Guide

If context resets mid-implementation, run `uv run pytest -v` and compare against the checkpoint table. The highest passing phase number tells you where to resume. Do not start the scheduler (Phase 4) before checker logic (Phase 3) is green — the coordinator only orchestrates `process_monitor_check`.

## Note on Vertical Slicing

Phase 3 is intentionally invokable without HTTP routes (tests call the service directly). This avoids waiting on the scheduler while still crossing service + persistence layers. Phase 4 closes the loop by wiring it into lifespan; Phase 5 adds the read API that consumers use to observe Phase 3–4 output.
