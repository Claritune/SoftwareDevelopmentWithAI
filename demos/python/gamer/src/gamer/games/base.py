from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

Seat = str


class IllegalMove(Exception):
    """The move is malformed or not allowed by the game's rules."""


@dataclass(frozen=True)
class GameStatus:
    to_move: Seat | None
    finished: bool
    winner: Seat | None
    scores: dict[Seat, int]


class Game[S, M](Protocol):
    id: str
    name: str
    seats: tuple[Seat, ...]
    static_dir: Path  # served at /games/{id}/static, must contain view.js

    def initial_state(self) -> S: ...
    def legal_moves(self, state: S, seat: Seat) -> list[M]: ...
    def apply_move(self, state: S, seat: Seat, move: M) -> S: ...  # raises IllegalMove
    def status(self, state: S) -> GameStatus: ...
    def to_public(self, state: S) -> dict[str, Any]: ...
    def parse_move(self, raw: dict[str, Any]) -> M: ...  # raises IllegalMove
    def move_to_public(self, move: M) -> dict[str, Any]: ...
