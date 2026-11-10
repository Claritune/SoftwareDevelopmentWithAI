from typing import Any, Literal

from pydantic import BaseModel


class GameInfo(BaseModel):
    id: str
    name: str


class SessionSummary(BaseModel):
    session_id: str
    game_id: str


class SeatAssignment(BaseModel):
    session_id: str
    seat: str
    token: str


class StatusModel(BaseModel):
    to_move: str | None
    finished: bool
    winner: str | None
    scores: dict[str, int]


class SessionState(BaseModel):
    session_id: str
    game_id: str
    version: int
    lifecycle: Literal["waiting", "playing", "finished"]
    public_state: dict[str, Any]
    status: StatusModel
    legal_moves: list[dict[str, Any]]
    seats: dict[str, bool]  # seat -> taken
    your_seat: str | None


class MoveRequest(BaseModel):
    move: dict[str, Any]
    version: int
