import secrets
from dataclasses import dataclass, field
from typing import Any, Literal

from gamer.games.base import Game, Seat

Lifecycle = Literal["waiting", "playing", "finished"]


class SessionError(Exception):
    message = "session error"

    def __str__(self) -> str:
        return self.args[0] if self.args else self.message


class GameNotFound(SessionError):
    message = "unknown game"


class SessionNotFound(SessionError):
    message = "unknown session"


class SessionFull(SessionError):
    message = "session is full"


class BadToken(SessionError):
    message = "invalid or missing player token"


class StaleVersion(SessionError):
    message = "board changed, refresh and try again"  # Phase 3


class NotYourTurn(SessionError):
    message = "not your turn"  # Phase 3


@dataclass
class Session:
    id: str
    game: Game
    state: Any
    version: int = 1
    seat_tokens: dict[str, Seat] = field(default_factory=dict)  # token -> seat

    @property
    def lifecycle(self) -> Lifecycle:
        if len(self.seat_tokens) < len(self.game.seats):
            return "waiting"
        return "finished" if self.game.status(self.state).finished else "playing"

    def seat_for(self, token: str | None) -> Seat | None:
        return self.seat_tokens.get(token) if token else None

    def taken_seats(self) -> set[Seat]:
        return set(self.seat_tokens.values())

    def claim_seat(self) -> tuple[Seat, str]:
        free = [s for s in self.game.seats if s not in self.taken_seats()]
        if not free:
            raise SessionFull()
        token = secrets.token_urlsafe(16)
        self.seat_tokens[token] = free[0]
        return free[0], token

    def join(self) -> tuple[Seat, str]:
        seat, token = self.claim_seat()
        self.version += 1
        return seat, token

    def move(self, token: str | None, raw_move: dict[str, Any], version: int) -> None:
        seat = self.seat_for(token)
        if seat is None:
            raise BadToken()
        if version != self.version:
            raise StaleVersion()
        if self.lifecycle != "playing" or self.game.status(self.state).to_move != seat:
            raise NotYourTurn()
        move = self.game.parse_move(raw_move)                     # may raise IllegalMove
        self.state = self.game.apply_move(self.state, seat, move)  # may raise IllegalMove
        self.version += 1


class SessionManager:
    def __init__(self, registry: dict[str, Game]) -> None:
        self._registry = registry
        self._sessions: dict[str, Session] = {}

    def game(self, game_id: str) -> Game:
        try:
            return self._registry[game_id]
        except KeyError:
            raise GameNotFound() from None

    def create(self, game_id: str) -> tuple[Session, Seat, str]:
        game = self.game(game_id)
        session = Session(id=secrets.token_urlsafe(6), game=game, state=game.initial_state())
        seat, token = session.claim_seat()  # creator: first seat, version stays 1
        self._sessions[session.id] = session
        return session, seat, token

    def get(self, session_id: str) -> Session:
        try:
            return self._sessions[session_id]
        except KeyError:
            raise SessionNotFound() from None

    def list_open(self, game_id: str) -> list[Session]:
        self.game(game_id)  # 404 for unknown game
        return [s for s in self._sessions.values()
                if s.game.id == game_id and s.lifecycle == "waiting"]
