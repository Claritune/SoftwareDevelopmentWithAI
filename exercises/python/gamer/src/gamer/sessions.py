import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from gamer.games.base import Game
from gamer.protocol import ApiError

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I
CODE_LENGTH = 6


def new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


class SessionNotFound(ApiError):
    def __init__(self, code: str) -> None:
        super().__init__(404, "session_not_found", f"Session {code} not found")


class SessionFull(ApiError):
    def __init__(self, code: str) -> None:
        super().__init__(409, "session_full", f"Session {code} is full")


@dataclass(frozen=True)
class Seat:
    player_id: str
    name: str


@dataclass
class Session:
    code: str
    game: Game
    state: Any
    seats: list[Seat] = field(default_factory=list)
    version: int = 0

    def _status(self, snapshot: dict[str, Any]) -> str:
        if len(self.seats) < self.game.max_players:
            return "waiting"
        return snapshot["status"]

    @property
    def status(self) -> str:
        return self._status(self.game.snapshot(self.state))

    def join(self, name: str) -> tuple[int, Seat]:
        if len(self.seats) >= self.game.max_players:
            raise SessionFull(self.code)
        seat = Seat(player_id=secrets.token_urlsafe(16), name=name)
        self.seats.append(seat)
        self.version += 1
        return len(self.seats) - 1, seat

    def to_payload(self) -> dict[str, Any]:
        snapshot = self.game.snapshot(self.state)
        return {
            **snapshot,
            "code": self.code,
            "game_id": self.game.id,
            "version": self.version,
            "status": self._status(snapshot),
            "players": [{"seat": i, "name": s.name} for i, s in enumerate(self.seats)],
        }


class SessionRegistry:
    def __init__(self, code_factory: Callable[[], str] = new_code) -> None:
        self._sessions: dict[str, Session] = {}
        self._new_code = code_factory

    def create(self, game: Game, name: str) -> tuple[Session, Seat]:
        code = self._new_code()
        while code in self._sessions:
            code = self._new_code()
        session = Session(code=code, game=game, state=game.initial_state())
        self._sessions[code] = session
        _, seat = session.join(name)
        return session, seat

    def open_sessions(self, game_id: str) -> list[Session]:
        return [
            s for s in self._sessions.values() if s.game.id == game_id and s.status == "waiting"
        ]

    def get(self, code: str) -> Session:
        session = self._sessions.get(code.upper())
        if session is None:
            raise SessionNotFound(code)
        return session
