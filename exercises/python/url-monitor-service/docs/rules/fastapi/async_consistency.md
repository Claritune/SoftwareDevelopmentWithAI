# Rule: Async consistency in FastAPI

All FastAPI route handlers that perform I/O MUST be declared `async def` and use async libraries:
- Database: use `asyncpg` via `SQLAlchemy[asyncio]`, never `psycopg2`
- HTTP calls: use `httpx.AsyncClient`, never `requests`
- Redis: use `redis.asyncio`, never synchronous `redis`
- File I/O: use `aiofiles` for non-trivial reads/writes

NEVER define a route as `async def` and then call synchronous blocking code inside it.
This silently blocks the event loop — no error, just degraded throughput under load.

If you must call sync code, use `def` (not `async def`) so FastAPI runs it in a threadpool,
or explicitly wrap it: `await asyncio.to_thread(sync_function)`.

When writing tests, use `@pytest.mark.anyio` and `httpx.AsyncClient` with `ASGITransport`, not the sync `TestClient` for async routes.
Why it's good for teaching: It demonstrates a rule that prevents a silent failure mode — the