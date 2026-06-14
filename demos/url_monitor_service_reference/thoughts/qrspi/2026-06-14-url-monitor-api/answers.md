# Answers

1. **SQLite access model**: Fully async with `aiosqlite` and thin async repository functions using raw SQL — no SQLAlchemy. Keeps async-consistency end-to-end; explicit and easier to debug than SQLAlchemy async session lifecycle.

2. **Background scheduler design**: Single coordinator task that wakes every N seconds, queries enabled monitors, and fans out checks via `asyncio.TaskGroup` (Python 3.11+). No APScheduler or external scheduler dependency. Prefer `TaskGroup` over bare `gather` for cleaner cancellation semantics. Coordinator cycle is directly testable.

3. **Monitor config refresh**: Poll SQLite on each coordinator cycle. Coordinator tick interval: ~5 seconds. No event bus or API-to-scheduler signaling. Up to one cycle delay before a new/changed monitor is picked up is acceptable. Event-driven alternative is a production sidebar only, not implemented.

4. **Initial status and first check**: Status starts as `UNKNOWN` (explicit enum value alongside `UP` and `DOWN`). Do not trigger an immediate check on monitor creation — API writes config only; coordinator picks up new monitors on the next cycle (within ~5 s). No transition recorded until the first check resolves to `UP` or `DOWN`.

5. **REST API shape and pagination**: Accept default shape with one simplification — omit separate `GET /monitors/{id}/status`; include current status fields in `GET /monitors/{id}`. Final endpoints:
   - `POST /api/v1/monitors` — create
   - `GET /api/v1/monitors` — list (`limit`/`offset`)
   - `GET /api/v1/monitors/{id}` — detail (includes current status)
   - `PATCH /api/v1/monitors/{id}` — update config
   - `DELETE /api/v1/monitors/{id}` — remove
   - `GET /api/v1/monitors/{id}/checks` — check history (`limit`/`offset`, default 50)
   - `GET /api/v1/monitors/{id}/transitions` — state transitions (`limit`/`offset`, default 50)
   - `GET /api/v1/status/summary` — aggregate overview
   - `GET /health` and `GET /ready` — outside `/api/v1/` prefix (infra concerns)

6. **Database schema and migrations**: Raw SQL via `aiosqlite`; `schema.sql` or Python module with DDL strings; `CREATE TABLE IF NOT EXISTS` on startup. No SQLAlchemy models, no Alembic. Three tables: `monitors`, `checks`, `transitions`. Test isolation via in-memory SQLite (`:memory:`) using the same schema init function.

7. **Dependency and project tooling**: `uv` with `pyproject.toml` and committed `uv.lock`. Dev extras group for `pytest`, `ruff`, `httpx` (test client).

8. **Consecutive failure threshold** (additional spec): Default 3 consecutive failures before transitioning `UP` → `DOWN`, configurable per monitor. A single successful check transitions `DOWN` → `UP` immediately. Asymmetric alarm/recovery pattern (slow to alarm, fast to recover).
