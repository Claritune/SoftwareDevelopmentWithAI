from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.db.connection import close_db, init_schema, open_db
from app.exceptions import AppError
from app.routers import health, monitors, status
from app.services.scheduler import start_scheduler, stop_scheduler
from app.settings import get_settings


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


def create_app() -> FastAPI:
    app = FastAPI(title="URL Monitor API", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(monitors.router)
    app.include_router(status.router)

    @app.exception_handler(AppError)
    async def app_error_handler(request, exc: AppError):
        return JSONResponse(
            status_code=exc.status,
            content={"error": exc.code, "message": exc.message},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request, exc: RequestValidationError):
        messages = "; ".join(
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        return JSONResponse(
            status_code=422,
            content={"error": "VALIDATION_ERROR", "message": messages},
        )

    return app


app = create_app()
