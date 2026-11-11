from collections.abc import Mapping
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from gamer.games import GAMES
from gamer.games.base import Game
from gamer.protocol import ApiError, envelope

STATIC_DIR = Path(__file__).parent / "static"


def create_app(games: Mapping[str, Game] | None = None) -> FastAPI:
    games = GAMES if games is None else games
    app = FastAPI(title="Gamer")

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(exc.to_envelope(), status_code=exc.status)

    @app.middleware("http")
    async def no_cache_static(request: Request, call_next):
        response = await call_next(request)
        if not request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    @app.get("/api/games")
    async def list_games() -> dict:
        return envelope(
            "games",
            [
                {
                    "id": g.id,
                    "name": g.name,
                    "min_players": g.min_players,
                    "max_players": g.max_players,
                }
                for g in games.values()
            ],
        )

    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app
