from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, Header
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from gamer.games import REGISTRY
from gamer.games.base import Game, Seat
from gamer.protocol import GameInfo, SeatAssignment, SessionState, SessionSummary, StatusModel
from gamer.sessions import (
    BadToken,
    GameNotFound,
    Session,
    SessionError,
    SessionFull,
    SessionManager,
    SessionNotFound,
)

STATIC_DIR = Path(__file__).parent / "static"

ERROR_STATUS: dict[type[Exception], int] = {
    GameNotFound: 404, SessionNotFound: 404, BadToken: 403, SessionFull: 409,
}


def build_state(session: Session, seat: Seat | None) -> SessionState:
    game, state = session.game, session.state
    playing = seat is not None and session.lifecycle == "playing"
    legal = [game.move_to_public(m) for m in game.legal_moves(state, seat)] if playing else []
    taken = session.taken_seats()
    return SessionState(
        session_id=session.id, game_id=game.id, version=session.version,
        lifecycle=session.lifecycle, public_state=game.to_public(state),
        status=StatusModel(**asdict(game.status(state))), legal_moves=legal,
        seats={s: s in taken for s in game.seats}, your_seat=seat,
    )


def create_app(registry: dict[str, Game] = REGISTRY) -> FastAPI:
    app = FastAPI(title="Gamer")
    manager = SessionManager(registry)
    app.state.manager = manager

    @app.exception_handler(SessionError)
    async def session_error(_, exc: SessionError) -> JSONResponse:
        status = next(c for t, c in ERROR_STATUS.items() if isinstance(exc, t))
        return JSONResponse({"detail": str(exc)}, status_code=status)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    for game in registry.values():
        app.mount(f"/games/{game.id}/static",
                  StaticFiles(directory=game.static_dir), name=f"{game.id}-static")

    @app.get("/api/games")
    async def list_games() -> list[GameInfo]:
        return [GameInfo(id=g.id, name=g.name) for g in registry.values()]

    @app.get("/api/games/{game_id}/sessions")
    async def list_sessions(game_id: str) -> list[SessionSummary]:
        return [SessionSummary(session_id=s.id, game_id=s.game.id)
                for s in manager.list_open(game_id)]

    @app.post("/api/games/{game_id}/sessions", status_code=201)
    async def create_session(game_id: str) -> SeatAssignment:
        session, seat, token = manager.create(game_id)
        return SeatAssignment(session_id=session.id, seat=seat, token=token)

    @app.post("/api/sessions/{session_id}/join")
    async def join_session(session_id: str) -> SeatAssignment:
        seat, token = manager.get(session_id).join()
        return SeatAssignment(session_id=session_id, seat=seat, token=token)

    @app.get("/api/sessions/{session_id}/state")
    async def session_state(
        session_id: str, x_player_token: str | None = Header(default=None),
    ) -> SessionState:
        session = manager.get(session_id)
        seat = session.seat_for(x_player_token)
        if x_player_token and seat is None:
            raise BadToken()
        return build_state(session, seat)

    @app.get("/", include_in_schema=False)
    async def index_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/games/{game_id}", include_in_schema=False)
    async def lobby_page(game_id: str) -> FileResponse:
        manager.game(game_id)
        return FileResponse(STATIC_DIR / "lobby.html")

    @app.get("/games/{game_id}/sessions/{session_id}", include_in_schema=False)
    async def game_page(game_id: str, session_id: str) -> FileResponse:
        manager.game(game_id)
        return FileResponse(STATIC_DIR / "game.html")

    return app


app = create_app()


def main() -> None:
    import uvicorn
    uvicorn.run("gamer.app:app", host="127.0.0.1", port=8000)
