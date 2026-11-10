from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from gamer.games import REGISTRY
from gamer.games.base import Game
from gamer.protocol import GameInfo

STATIC_DIR = Path(__file__).parent / "static"


def create_app(registry: dict[str, Game] = REGISTRY) -> FastAPI:
    app = FastAPI(title="Gamer")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    for game in registry.values():
        app.mount(f"/games/{game.id}/static",
                  StaticFiles(directory=game.static_dir), name=f"{game.id}-static")

    @app.get("/api/games")
    async def list_games() -> list[GameInfo]:
        return [GameInfo(id=g.id, name=g.name) for g in registry.values()]

    @app.get("/", include_in_schema=False)
    async def index_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()


def main() -> None:
    import uvicorn
    uvicorn.run("gamer.app:app", host="127.0.0.1", port=8000)
