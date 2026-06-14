# Implementation Plan

## Overview

Implement a FastAPI URL monitoring service with `aiosqlite` persistence, async httpx health checks, a coordinator scheduler using `asyncio.TaskGroup`, and a versioned REST API under `/api/v1/`. Work proceeds in five vertical phases from runnable skeleton through full end-to-end integration.

**Conventions (all phases):**
- All route handlers: `async def`; inject `conn` and `settings` via `Depends`
- Timestamps: UTC ISO-8601 strings (`datetime.now(timezone.utc).isoformat()`)
- Boolean columns in SQLite: `INTEGER` 0/1
- Package layout: flat `app/` at project root (not `src/`)
- Repo path: `app/repositories/` (per structure.md, not `app/db/repositories/`)

---

## Phase 1: Runnable Skeleton & Health Endpoints

### Changes

#### 1. Project manifest
**File**: `pyproject.toml`
**Action**: create

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "url-monitor-api"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pydantic-settings>=2.0",
    "aiosqlite>=0.20",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "anyio>=4.0", "ruff>=0.4"]

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py311"
line-length = 100
```

Then run `uv sync --extra dev` to generate `uv.lock` and commit it.

#### 2. Package stubs
**Files**: `app/__init__.py`, `app/db/__init__.py`, `app/routers/__init__.py`, `tests/__init__.py`
**Action**: create (empty files)

#### 3. Settings
**File**: `app/settings.py`
**Action**: create

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_path: str = "url_monitor.db"
    coordinator_tick_seconds: int = 5
    default_check_interval_seconds: int = 60
    default_timeout_seconds: int = 10
    default_failure_threshold: int = 3
    host: str = "127.0.0.1"
    port: int = 8000

    model_config = SettingsConfigDict(env_file=".env")

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

#### 4. Exceptions
**File**: `app/exceptions.py`
**Action**: create

```python
class AppError(Exception):
    def __init__(self, message: str, code: str, status: int = 400):
        self.message = message
        self.code = code
        self.status = status

class NotFoundError(AppError):
    def __init__(self, resource: str, id: int | str):
        super().__init__(f"{resource} {id} not found", "NOT_FOUND", 404)

class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(message, "CONFLICT", 409)
```

#### 5. Database schema
**File**: `app/db/schema.sql`
**Action**: create

```sql
CREATE TABLE IF NOT EXISTS monitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    display_name TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    check_interval_seconds INTEGER NOT NULL DEFAULT 60,
    timeout_seconds INTEGER NOT NULL DEFAULT 10,
    failure_threshold INTEGER NOT NULL DEFAULT 3,
    status TEXT NOT NULL DEFAULT 'UNKNOWN',
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    last_checked_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_id INTEGER NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
    checked_at TEXT NOT NULL,
    http_status INTEGER,
    response_time_ms INTEGER NOT NULL,
    success INTEGER NOT NULL,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monitor_id INTEGER NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
    transitioned_at TEXT NOT NULL,
    from_status TEXT NOT NULL,
    to_status TEXT NOT NULL,
    check_id INTEGER NOT NULL REFERENCES checks(id) ON DELETE CASCADE
);
```

#### 6. Database connection helpers
**File**: `app/db/connection.py`
**Action**: create

```python
from pathlib import Path
import aiosqlite

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

async def open_db(path: str) -> aiosqlite.Connection:
    conn = await aiosqlite.connect(path)
    conn.row_factory = aiosqlite.Row
    return conn

async def init_schema(conn: aiosqlite.Connection) -> None:
    ddl = SCHEMA_PATH.read_text()
    await conn.executescript(ddl)
    await conn.commit()

async def close_db(conn: aiosqlite.Connection) -> None:
    await conn.close()
```

#### 7. Dependencies
**File**: `app/dependencies.py`
**Action**: create

```python
from fastapi import Request
import aiosqlite
from app.settings import Settings, get_settings

async def get_db(request: Request) -> aiosqlite.Connection:
    return request.app.state.db

def get_settings_dep() -> Settings:
    return get_settings()
```

#### 8. Health router
**File**: `app/routers/health.py`
**Action**: create

```python
from fastapi import APIRouter, Depends
import aiosqlite
from app.dependencies import get_db

router = APIRouter(tags=["health"])

@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

@router.get("/ready")
async def ready(conn: aiosqlite.Connection = Depends(get_db)) -> dict[str, str]:
    await conn.execute("SELECT 1")
    return {"status": "ready"}
```

#### 9. Application entrypoint
**File**: `app/main.py`
**Action**: create

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.db.connection import close_db, init_schema, open_db
from app.exceptions import AppError
from app.routers import health
from app.settings import get_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    conn = await open_db(settings.database_path)
    await init_schema(conn)
    app.state.db = conn
    yield
    await close_db(conn)

def create_app() -> FastAPI:
    app = FastAPI(title="URL Monitor API", lifespan=lifespan)
    app.include_router(health.router)

    @app.exception_handler(AppError)
    async def app_error_handler(request, exc: AppError):
        return JSONResponse(
            status_code=exc.status,
            content={"error": exc.code, "message": exc.message},
        )

    return app

app = create_app()
```

Note: `RequestValidationError` handler added in Phase 5.

#### 10. Test infrastructure
**File**: `tests/conftest.py`
**Action**: create

```python
import pytest
import httpx
from httpx import ASGITransport
from app.db.connection import close_db, init_schema, open_db
from app.main import create_app
from app.settings import Settings, get_settings

@pytest.fixture
def test_settings(tmp_path) -> Settings:
    return Settings(database_path=str(tmp_path / "test.db"))

@pytest.fixture
async def db_conn(test_settings):
    conn = await open_db(test_settings.database_path)
    await init_schema(conn)
    yield conn
    await close_db(conn)

@pytest.fixture
async def app(test_settings, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", test_settings.database_path)
    get_settings.cache_clear()
    application = create_app()
    # Override lifespan db with test path via env
    yield application
    get_settings.cache_clear()

@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

Adjust `test_settings` so `Settings` reads `database_path` from env — add `model_config` env prefix or use field names matching env (`DATABASE_PATH` maps to `database_path` automatically in pydantic-settings).

#### 11. Health tests
**File**: `tests/test_health.py`
**Action**: create

```python
import pytest

@pytest.mark.anyio
async def test_health_returns_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

@pytest.mark.anyio
async def test_ready_returns_ready(client):
    resp = await client.get("/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready"}
```

### Verification

#### Automated
- [x] `uv sync --extra dev` succeeds and `uv.lock` is created
- [x] `uv run ruff check app tests` passes (no errors)
- [x] `uv run pytest tests/test_health.py -v` passes

#### Manual
- [ ] `uv run uvicorn app.main:app --reload` starts without error
- [ ] `curl http://127.0.0.1:8000/health` returns `{"status":"ok"}`
- [ ] `curl http://127.0.0.1:8000/ready` returns `{"status":"ready"}`
- [ ] `http://127.0.0.1:8000/docs` loads Swagger UI

---

## Phase 2: Monitor CRUD API

### Changes

#### 1. Shared schemas
**File**: `app/schemas/common.py`
**Action**: create

```python
from pydantic import BaseModel, Field

class PaginationParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
```

#### 2. Monitor schemas
**File**: `app/schemas/monitors.py`
**Action**: create

```python
from enum import Enum
from typing import TypedDict
from pydantic import BaseModel, Field, HttpUrl

class MonitorStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    UP = "UP"
    DOWN = "DOWN"

class MonitorRow(TypedDict):
    id: int
    url: str
    display_name: str | None
    enabled: int
    check_interval_seconds: int
    timeout_seconds: int
    failure_threshold: int
    status: str
    consecutive_failures: int
    last_checked_at: str | None
    created_at: str
    updated_at: str

class MonitorCreate(BaseModel):
    url: HttpUrl
    display_name: str | None = None
    check_interval_seconds: int | None = None
    timeout_seconds: int | None = None
    failure_threshold: int | None = None
    enabled: bool = True

class MonitorUpdate(BaseModel):
    url: HttpUrl | None = None
    display_name: str | None = None
    check_interval_seconds: int | None = None
    timeout_seconds: int | None = None
    failure_threshold: int | None = None
    enabled: bool | None = None

class MonitorResponse(BaseModel):
    id: int
    url: str
    display_name: str | None
    enabled: bool
    check_interval_seconds: int
    timeout_seconds: int
    failure_threshold: int
    status: MonitorStatus
    consecutive_failures: int
    last_checked_at: str | None
    created_at: str
    updated_at: str

class PaginatedMonitors(BaseModel):
    items: list[MonitorResponse]
    total: int
    limit: int
    offset: int
```

Add helper `def row_to_response(row: MonitorRow) -> MonitorResponse` converting `enabled` int→bool and `status` str→enum.

#### 3. Monitor repository
**File**: `app/repositories/monitors.py`
**Action**: create

Key functions:

```python
async def create_monitor(conn, data: MonitorCreate, settings: Settings) -> MonitorRow:
    now = utc_now()
    await conn.execute(
        """INSERT INTO monitors (url, display_name, enabled, check_interval_seconds,
           timeout_seconds, failure_threshold, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(data.url), data.display_name, int(data.enabled),
            data.check_interval_seconds or settings.default_check_interval_seconds,
            data.timeout_seconds or settings.default_timeout_seconds,
            data.failure_threshold or settings.default_failure_threshold,
            MonitorStatus.UNKNOWN.value, now, now,
        ),
    )
    await conn.commit()
    return await get_monitor(conn, await last_insert_id(conn))

async def list_monitors(conn, limit: int, offset: int) -> tuple[list[MonitorRow], int]:
    # SELECT COUNT(*), SELECT * ORDER BY id LIMIT ? OFFSET ?

async def get_monitor(conn, monitor_id: int) -> MonitorRow | None:
    # SELECT * WHERE id = ?

async def update_monitor(conn, monitor_id: int, data: MonitorUpdate) -> MonitorRow | None:
    # Build dynamic SET clause for non-None fields; always set updated_at

async def delete_monitor(conn, monitor_id: int) -> bool:
    # DELETE WHERE id = ?; return cursor.rowcount > 0
```

Use `conn.execute(...); row = await cursor.fetchone(); dict(row)` to build `MonitorRow`.

#### 4. Monitor router
**File**: `app/routers/monitors.py`
**Action**: create

```python
router = APIRouter(prefix="/api/v1/monitors", tags=["monitors"])

@router.post("", response_model=MonitorResponse, status_code=201)
async def create_monitor_endpoint(...):
    try:
        return row_to_response(await create_monitor(conn, data, settings))
    except aiosqlite.IntegrityError:
        raise ConflictError(f"Monitor with url {data.url} already exists")

@router.get("", response_model=PaginatedMonitors)
async def list_monitors_endpoint(limit: int = 50, offset: int = 0, ...): ...

@router.get("/{monitor_id}", response_model=MonitorResponse)
async def get_monitor_endpoint(monitor_id: int, ...):
    row = await get_monitor(conn, monitor_id)
    if not row:
        raise NotFoundError("Monitor", monitor_id)
    return row_to_response(row)

@router.patch("/{monitor_id}", response_model=MonitorResponse)
async def update_monitor_endpoint(...): ...

@router.delete("/{monitor_id}", status_code=204)
async def delete_monitor_endpoint(...): ...
```

#### 5. Wire router into app
**File**: `app/main.py`
**Action**: modify

```python
from app.routers import health, monitors
# inside create_app():
app.include_router(monitors.router)
```

#### 6. Monitor API tests
**File**: `tests/test_api_monitors.py`
**Action**: create

Test cases:
- `test_create_monitor_returns_unknown_status` — POST `{"url":"https://example.com"}` → 201, `status == "UNKNOWN"`
- `test_list_monitors_paginated` — create 2, GET with limit/offset
- `test_get_monitor_not_found` — 404 with `{"error":"NOT_FOUND",...}`
- `test_update_monitor` — PATCH `display_name`, `enabled`
- `test_delete_monitor` — 204 then GET 404
- `test_duplicate_url_returns_conflict` — POST same URL twice → 409

All tests use `@pytest.mark.anyio` and the `client` fixture.

### Verification

#### Automated
- [x] `uv run pytest tests/test_health.py tests/test_api_monitors.py -v` passes
- [x] `uv run ruff check app tests` passes

#### Manual
- [ ] `POST /api/v1/monitors` with `{"url":"https://httpbin.org/status/200"}` returns 201 with `"status":"UNKNOWN"`
- [ ] `GET /api/v1/monitors` lists the created monitor
- [ ] `DELETE /api/v1/monitors/{id}` returns 204

---

## Phase 3: HTTP Checker & State Machine

### Changes

#### 1. Check repository
**File**: `app/repositories/checks.py`
**Action**: create

```python
class CheckRow(TypedDict):
    id: int
    monitor_id: int
    checked_at: str
    http_status: int | None
    response_time_ms: int
    success: int
    error_message: str | None

async def insert_check(conn, monitor_id: int, result: CheckResult) -> int:
    now = utc_now()
    cursor = await conn.execute(
        """INSERT INTO checks (monitor_id, checked_at, http_status, response_time_ms, success, error_message)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (monitor_id, now, result.http_status, result.response_time_ms,
         int(result.success), result.error_message),
    )
    await conn.commit()
    return cursor.lastrowid
```

#### 2. Transition repository
**File**: `app/repositories/transitions.py`
**Action**: create

```python
class TransitionRow(TypedDict):
    id: int
    monitor_id: int
    transitioned_at: str
    from_status: str
    to_status: str
    check_id: int

async def insert_transition(conn, monitor_id: int, from_status: str, to_status: str, check_id: int) -> None:
    await conn.execute(
        """INSERT INTO transitions (monitor_id, transitioned_at, from_status, to_status, check_id)
           VALUES (?, ?, ?, ?, ?)""",
        (monitor_id, utc_now(), from_status, to_status, check_id),
    )
    await conn.commit()
```

#### 3. Checker service
**File**: `app/services/checker.py`
**Action**: create

```python
class CheckResult(BaseModel):
    success: bool
    http_status: int | None
    response_time_ms: int
    error_message: str | None

async def check_url(client: httpx.AsyncClient, url: str, timeout: float) -> CheckResult:
    start = time.perf_counter()
    try:
        resp = await client.get(url, timeout=timeout)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        success = resp.status_code < 400
        return CheckResult(
            success=success,
            http_status=resp.status_code,
            response_time_ms=elapsed_ms,
            error_message=None if success else f"HTTP {resp.status_code}",
        )
    except httpx.TimeoutException:
        ...
    except httpx.RequestError as exc:
        ...

async def update_monitor_after_check(
    conn, monitor_id: int, status: str, consecutive_failures: int, checked_at: str
) -> None:
    await conn.execute(
        """UPDATE monitors SET status = ?, consecutive_failures = ?,
           last_checked_at = ?, updated_at = ? WHERE id = ?""",
        (status, consecutive_failures, checked_at, utc_now(), monitor_id),
    )
    await conn.commit()

async def process_monitor_check(
    conn: aiosqlite.Connection,
    client: httpx.AsyncClient,
    monitor: MonitorRow,
) -> None:
    result = await check_url(client, monitor["url"], float(monitor["timeout_seconds"]))
    check_id = await insert_check(conn, monitor["id"], result)

    status = monitor["status"]
    consecutive = monitor["consecutive_failures"]
    threshold = monitor["failure_threshold"]
    new_status = status

    if result.success:
        consecutive = 0
        if status != MonitorStatus.UP.value:
            new_status = MonitorStatus.UP.value
            await insert_transition(conn, monitor["id"], status, new_status, check_id)
    else:
        consecutive += 1
        if consecutive >= threshold and status in (MonitorStatus.UP.value, MonitorStatus.UNKNOWN.value):
            new_status = MonitorStatus.DOWN.value
            await insert_transition(conn, monitor["id"], status, new_status, check_id)

    await update_monitor_after_check(conn, monitor["id"], new_status, consecutive, utc_now())
```

#### 4. Checker tests
**File**: `tests/test_checker.py`
**Action**: create

Use `httpx.MockTransport` to simulate responses:

```python
def make_mock_transport(handler):
    return httpx.MockTransport(handler)

@pytest.mark.anyio
async def test_success_unknown_to_up(db_conn):
    # insert monitor with status UNKNOWN
    # client with MockTransport returning 200
    # await process_monitor_check(...)
    # assert monitors.status == UP, len(transitions) == 1, check row exists

@pytest.mark.anyio
async def test_failure_threshold_unknown_to_down(db_conn):
    # threshold=3, run process_monitor_check 3 times with 500 responses
    # assert transitions only on 3rd failure, status DOWN

@pytest.mark.anyio
async def test_down_to_up_on_single_success(db_conn):
    # seed DOWN monitor, mock 200, one check → UP + transition

@pytest.mark.anyio
async def test_up_stays_up_below_threshold(db_conn):
    # 2 failures with threshold 3 → still UP, no transition
```

Helper in conftest or test file: `async def seed_monitor(conn, **kwargs) -> MonitorRow`.

### Verification

#### Automated
- [x] `uv run pytest tests/test_checker.py -v` passes
- [x] `uv run pytest tests/test_health.py tests/test_api_monitors.py tests/test_checker.py -v` passes

#### Manual
- [ ] No manual steps required — checker is service-level only in this phase

---

## Phase 4: Background Scheduler & Lifespan

### Changes

#### 1. Due-monitor query
**File**: `app/repositories/monitors.py`
**Action**: modify — add:

```python
async def list_enabled_monitors(conn) -> list[MonitorRow]:
    cursor = await conn.execute("SELECT * FROM monitors WHERE enabled = 1")
    rows = await cursor.fetchall()
    return [row_to_monitor_row(r) for r in rows]

def is_monitor_due(monitor: MonitorRow, now: datetime) -> bool:
    if monitor["last_checked_at"] is None:
        return True
    last = datetime.fromisoformat(monitor["last_checked_at"])
    elapsed = (now - last).total_seconds()
    return elapsed >= monitor["check_interval_seconds"]

async def get_monitors_due_for_check(conn, now: datetime) -> list[MonitorRow]:
    enabled = await list_enabled_monitors(conn)
    return [m for m in enabled if is_monitor_due(m, now)]
```

#### 2. Scheduler service
**File**: `app/services/scheduler.py`
**Action**: create

```python
import asyncio
import logging

logger = logging.getLogger(__name__)

async def run_cycle(
    conn: aiosqlite.Connection,
    client: httpx.AsyncClient,
    settings: Settings,
) -> None:
    now = datetime.now(timezone.utc)
    due = await get_monitors_due_for_check(conn, now)
    if not due:
        return
    async with asyncio.TaskGroup() as tg:
        for monitor in due:
            tg.create_task(process_monitor_check(conn, client, monitor))

async def scheduler_loop(
    conn: aiosqlite.Connection,
    client: httpx.AsyncClient,
    settings: Settings,
) -> None:
    while True:
        try:
            await run_cycle(conn, client, settings)
        except Exception:
            logger.exception("Scheduler cycle failed")
        await asyncio.sleep(settings.coordinator_tick_seconds)

async def start_scheduler(conn, client, settings) -> asyncio.Task:
    return asyncio.create_task(scheduler_loop(conn, client, settings))

async def stop_scheduler(task: asyncio.Task) -> None:
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
```

Wrap `process_monitor_check` in try/except inside the task if `TaskGroup` sibling cancellation is a concern — log and swallow per-monitor errors so one failure doesn't kill the group. Pattern:

```python
async def safe_check(conn, client, monitor):
    try:
        await process_monitor_check(conn, client, monitor)
    except Exception:
        logger.exception("Check failed for monitor %s", monitor["id"])
```

Use `safe_check` in `TaskGroup` instead of raw `process_monitor_check`.

#### 3. Extend lifespan
**File**: `app/main.py`
**Action**: modify

```python
import httpx
from app.services.scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    conn = await open_db(settings.database_path)
    await init_schema(conn)
    app.state.db = conn
    app.state.http_client = httpx.AsyncClient()
    scheduler_task = await start_scheduler(conn, app.state.http_client, settings)
    app.state.scheduler_task = scheduler_task
    yield
    await stop_scheduler(scheduler_task)
    await app.state.http_client.aclose()
    await close_db(conn)
```

#### 4. Scheduler tests
**File**: `tests/test_scheduler.py`
**Action**: create

```python
@pytest.mark.anyio
async def test_run_cycle_checks_due_monitors(db_conn):
    # seed enabled monitor, interval=1, last_checked_at=NULL
    # MockTransport 200
    # await run_cycle(db_conn, client, settings)
    # assert check row, status UP, last_checked_at set

@pytest.mark.anyio
async def test_run_cycle_skips_disabled(db_conn):
    # seed enabled=0, run_cycle → no checks

@pytest.mark.anyio
async def test_run_cycle_respects_interval(db_conn):
    # seed monitor with last_checked_at=now, interval=60
    # run_cycle → no checks

@pytest.mark.anyio
async def test_run_cycle_failure_then_recovery(db_conn):
    # seed monitor; cycle 1-3 with 500 → DOWN; cycle 4 with 200 → UP
```

#### 5. Update conftest
**File**: `tests/conftest.py`
**Action**: modify

Add optional fixture `mock_http_client` using `httpx.AsyncClient(transport=MockTransport(...))` for scheduler/checker tests.

For API tests: scheduler runs in background during `client` fixture lifespan. To avoid flakiness, use URLs that won't be hit accidentally, or set very long `check_interval_seconds` on test monitors (e.g. 3600). Document this in test helpers.

### Verification

#### Automated
- [x] `uv run pytest tests/test_scheduler.py -v` passes
- [x] `uv run pytest tests/test_health.py tests/test_api_monitors.py tests/test_checker.py tests/test_scheduler.py -v` passes

#### Manual
- [ ] Start server, `POST` a monitor for `https://httpbin.org/status/200`, wait ~5 s, query DB or eventual Phase 5 endpoint to confirm check ran

---

## Phase 5: History, Summary API & End-to-End Integration

### Changes

#### 1. Check/transition list queries
**File**: `app/repositories/checks.py`
**Action**: modify — add:

```python
async def list_checks(conn, monitor_id: int, limit: int, offset: int) -> tuple[list[CheckRow], int]:
    # COUNT + SELECT ORDER BY checked_at DESC

async def count_checks_for_monitor(conn, monitor_id: int) -> int: ...
```

**File**: `app/repositories/transitions.py`
**Action**: modify — add `list_transitions(...)` same pattern.

**File**: `app/repositories/monitors.py`
**Action**: modify — add:

```python
async def get_status_summary(conn) -> dict:
    # COUNT by status; SELECT id, url, status, consecutive_failures for snapshot list
```

#### 2. History schemas
**File**: `app/schemas/checks.py`
**Action**: create

```python
class CheckResponse(BaseModel):
    id: int
    monitor_id: int
    checked_at: str
    http_status: int | None
    response_time_ms: int
    success: bool
    error_message: str | None

class TransitionResponse(BaseModel):
    id: int
    monitor_id: int
    transitioned_at: str
    from_status: MonitorStatus
    to_status: MonitorStatus
    check_id: int

class PaginatedChecks(BaseModel):
    items: list[CheckResponse]
    total: int
    limit: int
    offset: int

class PaginatedTransitions(BaseModel):
    items: list[TransitionResponse]
    total: int
    limit: int
    offset: int

class MonitorSummary(BaseModel):
    id: int
    url: str
    status: MonitorStatus
    consecutive_failures: int

class StatusSummary(BaseModel):
    total: int
    up: int
    down: int
    unknown: int
    monitors: list[MonitorSummary]
```

#### 3. History routes
**File**: `app/routers/monitors.py`
**Action**: modify — add:

```python
@router.get("/{monitor_id}/checks", response_model=PaginatedChecks)
async def list_checks_endpoint(monitor_id: int, limit: int = 50, offset: int = 0, ...):
    if not await get_monitor(conn, monitor_id):
        raise NotFoundError("Monitor", monitor_id)
    ...

@router.get("/{monitor_id}/transitions", response_model=PaginatedTransitions)
async def list_transitions_endpoint(...): ...
```

**File**: `app/routers/status.py`
**Action**: create

```python
router = APIRouter(prefix="/api/v1/status", tags=["status"])

@router.get("/summary", response_model=StatusSummary)
async def status_summary(conn = Depends(get_db)):
    return await get_status_summary(conn)
```

Register in `app/main.py`: `app.include_router(status.router)`.

#### 4. Validation error handler
**File**: `app/main.py`
**Action**: modify — add inside `create_app()`:

```python
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc: RequestValidationError):
    messages = "; ".join(
        f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()
    )
    return JSONResponse(
        status_code=422,
        content={"error": "VALIDATION_ERROR", "message": messages},
    )
```

#### 5. History API tests
**File**: `tests/test_api_history.py`
**Action**: create

- `test_list_checks_empty` — new monitor, no checks yet → `items: []`
- `test_list_checks_after_manual_insert` — seed check via repo, GET returns it
- `test_list_transitions` — seed transition, GET returns it
- `test_status_summary` — seed monitors in UP/DOWN/UNKNOWN, verify counts
- `test_checks_not_found_monitor` — 404

#### 6. End-to-end integration tests
**File**: `tests/test_integration.py`
**Action**: create

```python
@pytest.mark.anyio
async def test_create_monitor_check_via_scheduler(client, db_conn, test_settings):
    # POST monitor with short interval (2s) via API
    # Get monitor id from response
    # Build httpx.AsyncClient with MockTransport (500 responses)
    # Call run_cycle directly with app.state db — OR use ASGITransport + patch
    # Simpler approach: use db_conn fixture shared with app via same db path;
    #   POST via client, then run_cycle(db_conn, mock_client, settings) x3
    # GET /api/v1/monitors/{id} → status DOWN
    # GET /api/v1/monitors/{id}/checks → 3 items

@pytest.mark.anyio
async def test_disable_stops_checks(client, db_conn, test_settings):
    # POST monitor, run_cycle (check created), PATCH enabled=false
    # run_cycle again → check count unchanged

@pytest.mark.anyio
async def test_delete_monitor_removes_history(client, db_conn):
    # POST, run_cycle, DELETE, GET checks → 404
```

Ensure `client` fixture and `db_conn` share the same database file path via `test_settings.database_path`.

#### 7. README (optional deliverable)
**File**: `README.md`
**Action**: modify — replace exercise instructions with install/run/test docs for the implemented service. Only if implementing in this repo; skip if using a separate worktree.

### Verification

#### Automated
- [x] `uv run ruff check app tests` passes
- [x] `uv run pytest -v` — full suite passes (all test files)
- [x] `uv run pytest --co -q` lists tests from: `test_health`, `test_api_monitors`, `test_checker`, `test_scheduler`, `test_api_history`, `test_integration`

#### Manual
- [ ] `uv run uvicorn app.main:app --reload` — server starts with scheduler
- [ ] `POST /api/v1/monitors` with `{"url":"https://httpbin.org/status/500","failure_threshold":3,"check_interval_seconds":5}`
- [ ] Wait ~15–20 s (3 checks × ~5 s cycle); `GET /api/v1/monitors/{id}` shows `"status":"DOWN"`
- [ ] `GET /api/v1/monitors/{id}/checks` returns check history with HTTP 500
- [ ] `PATCH` with `{"enabled":false}`; wait 10 s; check count stable
- [ ] `GET /api/v1/status/summary` returns aggregate counts
- [ ] `GET /docs` shows all endpoints under monitors and status tags

---

## Shared Utilities

Create as needed (Phase 2 or 3):

**File**: `app/util/time.py`
```python
from datetime import datetime, timezone

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
```

**File**: `app/db/helpers.py` (optional)
```python
async def last_insert_id(conn) -> int:
    cursor = await conn.execute("SELECT last_insert_rowid()")
    row = await cursor.fetchone()
    return row[0]
```

---

## Progress Tracker

| Phase | Status | Verified |
|-------|--------|----------|
| 1 — Skeleton & health | complete | automated |
| 2 — Monitor CRUD | complete | automated |
| 3 — Checker & state machine | complete | automated |
| 4 — Background scheduler | complete | automated |
| 5 — History, summary & E2E | complete | automated |

Update checkboxes and this table during `/implement`.
