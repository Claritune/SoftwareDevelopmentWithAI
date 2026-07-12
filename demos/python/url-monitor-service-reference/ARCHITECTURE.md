# URL Monitor API — Architecture

A long-running FastAPI service that persists monitor configuration in SQLite, probes URLs on a background schedule, and exposes a versioned REST API for configuration and observability.

## High-level diagram

```mermaid
flowchart TB
    subgraph Clients
        HTTP["HTTP clients / OpenAPI (/docs)"]
    end

    subgraph Platform["Platform (@platform)"]
        Main["app/main.py\nlifespan · exception handlers"]
        Settings["app/settings.py"]
        Deps["app/dependencies.py"]
        DBConn["app/db/connection.py"]
        Health["app/routers/health.py\n/health · /ready"]
    end

    subgraph API["HTTP API layer"]
        MonitorAPI["Monitor API (@monitor-api)\napp/routers/monitors.py\nCRUD /api/v1/monitors"]
        Observability["Observability (@observability)\napp/routers/monitors.py (history)\napp/routers/status.py"]
    end

    subgraph Domain["Domain services"]
        Coordinator["Coordinator (@coordinator)\napp/services/scheduler.py\ntick loop · TaskGroup"]
        CheckEngine["Check Engine (@check-engine)\napp/services/checker.py\nprobe · state machine"]
    end

    subgraph Persistence["Persistence"]
        Repos["app/repositories/\nmonitors · checks · transitions"]
        Schema["app/db/schema.sql"]
        SQLite[("SQLite")]
    end

    subgraph External
        Targets["Monitored URLs\n(HTTP GET)"]
    end

    HTTP --> Health
    HTTP --> MonitorAPI
    HTTP --> Observability

    Main --> Settings
    Main --> DBConn
    Main --> Coordinator
    Main --> MonitorAPI
    Main --> Observability
    Main --> Health

    MonitorAPI --> Deps
    Observability --> Deps
    Health --> Deps

    MonitorAPI --> Repos
    Observability --> Repos
    Coordinator --> Repos
    CheckEngine --> Repos

    DBConn --> Schema
    Schema --> SQLite
    Repos --> SQLite

    Coordinator -->|"due monitors each tick"| CheckEngine
    CheckEngine -->|"httpx.AsyncClient"| Targets
```

## Runtime flows

### API request (configuration / queries)

```mermaid
sequenceDiagram
    participant Client
    participant Router as FastAPI router
    participant Repo as Repository
    participant DB as SQLite

    Client->>Router: HTTP request
    Router->>Repo: async repo call
    Repo->>DB: parameterized SQL
    DB-->>Repo: rows
    Repo-->>Router: domain rows / models
    Router-->>Client: JSON response
```

Routes raise domain exceptions (`NotFoundError`, `ConflictError`); global handlers in `app/main.py` map them to structured JSON (`{"error", "message"}`).

### Background monitoring (no API trigger)

```mermaid
sequenceDiagram
    participant Lifespan as App lifespan
    participant Scheduler as Coordinator
    participant Checker as Check Engine
    participant Repo as Repository
    participant URL as Target URL
    participant DB as SQLite

    Lifespan->>Scheduler: start_scheduler()
    loop every coordinator_tick_seconds
        Scheduler->>Repo: get_monitors_due_for_check()
        Repo->>DB: SELECT enabled monitors
        par concurrent checks (TaskGroup)
            Scheduler->>Checker: process_monitor_check(monitor)
            Checker->>URL: GET (timeout from monitor config)
            URL-->>Checker: response / error
            Checker->>Repo: insert check, update status, maybe insert transition
            Repo->>DB: INSERT / UPDATE
        end
    end
    Lifespan->>Scheduler: stop_scheduler() on shutdown
```

The API and scheduler share one `aiosqlite` connection opened at startup. Monitor creation does not trigger an immediate check — the coordinator picks up new monitors on the next eligible cycle.

## Vertical modules

The codebase is organized into five agent-scoped modules (see `.cursor/rules/`):

| Module | Responsibility | Key paths |
|--------|----------------|-----------|
| **Platform** | Bootstrap, settings, DB init, errors, health | `app/main.py`, `app/settings.py`, `app/db/`, `app/routers/health.py` |
| **Monitor API** | Monitor CRUD, validation, pagination | `app/routers/monitors.py` (CRUD), `app/repositories/monitors.py`, `app/schemas/monitors.py` |
| **Check Engine** | HTTP probe, UP/DOWN state machine | `app/services/checker.py`, `app/repositories/checks.py`, `app/repositories/transitions.py` |
| **Coordinator** | Background tick loop, due-monitor selection | `app/services/scheduler.py`, scheduler wiring in lifespan |
| **Observability** | History, transitions, status summary | `app/routers/status.py`, history routes on monitors router, `app/schemas/checks.py` |

## Data model

```mermaid
erDiagram
    monitors ||--o{ checks : "has"
    monitors ||--o{ transitions : "has"
    checks ||--o| transitions : "triggers"

    monitors {
        int id PK
        string url UK
        string display_name
        string tags
        int enabled
        int check_interval_seconds
        int timeout_seconds
        int failure_threshold
        string status
        int consecutive_failures
        string last_checked_at
        string created_at
        string updated_at
    }

    checks {
        int id PK
        int monitor_id FK
        string checked_at
        int http_status
        int response_time_ms
        int success
        string error_message
    }

    transitions {
        int id PK
        int monitor_id FK
        string transitioned_at
        string from_status
        string to_status
        int check_id FK
    }
```

- **`monitors`** — configuration plus current runtime state (`status`, `consecutive_failures`, `last_checked_at`).
- **`checks`** — append-only log of every HTTP probe result.
- **`transitions`** — append-only log of status changes (`UNKNOWN` / `UP` / `DOWN`).

## State machine (Check Engine)

| Event | Current status | Result |
|-------|----------------|--------|
| Probe success | `UNKNOWN` or `DOWN` | → `UP`, record transition |
| Probe success | `UP` | stay `UP`, reset failure counter |
| Probe failure | any | increment `consecutive_failures` |
| Failures ≥ threshold | `UP` or `UNKNOWN` | → `DOWN`, record transition |

Default threshold: 3 consecutive failures. One success flips `DOWN` back to `UP`.

## Technology stack

| Layer | Choice |
|-------|--------|
| Web framework | FastAPI (async) |
| HTTP client | httpx.AsyncClient (shared in lifespan) |
| Database | SQLite via aiosqlite, raw SQL repositories |
| Config | pydantic-settings (`Settings` class, env / `.env`) |
| Concurrency | asyncio task loop + `TaskGroup` per coordinator cycle |
| Tests | pytest + httpx ASGITransport (no sync TestClient) |

## API surface (summary)

| Method | Path | Module |
|--------|------|--------|
| GET | `/health`, `/ready` | Platform |
| POST, GET, PATCH, DELETE | `/api/v1/monitors` … | Monitor API |
| GET | `/api/v1/monitors/{id}/checks` | Observability |
| GET | `/api/v1/monitors/{id}/transitions` | Observability |
| GET | `/api/v1/status/summary` | Observability |

Interactive OpenAPI docs: `/docs`.
