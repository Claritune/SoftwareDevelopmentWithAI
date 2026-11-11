from collections.abc import Mapping
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from gamer.games import GAMES
from gamer.games.base import Game
from gamer.protocol import ApiError, BadRequest, GameNotFound, NameRequest, envelope
from gamer.sessions import Seat, Session, SessionRegistry

STATIC_DIR = Path(__file__).parent / "static"


def create_app(
    games: Mapping[str, Game] | None = None, registry: SessionRegistry | None = None
) -> FastAPI:
    games = GAMES if games is None else games
    registry = SessionRegistry() if registry is None else registry
    app = FastAPI(title="Gamer")

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(exc.to_envelope(), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        err = BadRequest(
            f"Invalid request: {exc.errors()[0]['msg']}" if exc.errors() else "Invalid request"
        )
        return JSONResponse(err.to_envelope(), status_code=err.status)

    @app.middleware("http")
    async def no_cache_static(request: Request, call_next):
        response = await call_next(request)
        if not request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    def get_game(game_id: str) -> Game:
        game = games.get(game_id)
        if game is None:
            raise GameNotFound(game_id)
        return game

    def joined(session: Session, seat_index: int, seat: Seat) -> dict:
        return envelope(
            "joined",
            {
                "code": session.code,
                "player_id": seat.player_id,
                "seat": seat_index,
                "state": session.to_payload(),
            },
        )

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

    @app.post("/api/games/{game_id}/sessions")
    async def create_session(game_id: str, body: NameRequest) -> dict:
        session, seat = registry.create(get_game(game_id), body.payload.name)
        return joined(session, 0, seat)

    @app.post("/api/sessions/{code}/join")
    async def join_session(code: str, body: NameRequest) -> dict:
        session = registry.get(code)
        index, seat = session.join(body.payload.name)
        return joined(session, index, seat)

    @app.get("/api/sessions/{code}")
    async def get_session(code: str) -> dict:
        return envelope("state", registry.get(code).to_payload())

    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app
