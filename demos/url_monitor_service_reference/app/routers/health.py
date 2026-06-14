from app.dependencies import DbConn

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(conn: DbConn) -> dict[str, str]:
    await conn.execute("SELECT 1")
    return {"status": "ready"}


@router.get("/hello-world")
async def hello_world() -> None:
    pass


@router.get("/hello-world2")
async def hello_world2() -> None:
    pass
