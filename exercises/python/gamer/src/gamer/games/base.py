from typing import Any, Protocol


class InvalidMove(Exception):
    """The move payload is malformed (HTTP 400)."""


class IllegalMove(Exception):
    """The move is well-formed but not allowed in this state (HTTP 409)."""


class Game(Protocol):
    id: str
    name: str
    min_players: int
    max_players: int

    def initial_state(self) -> Any: ...

    def parse_move(self, payload: Any) -> Any: ...

    def apply_move(self, state: Any, seat: int, move: Any) -> Any: ...

    def snapshot(self, state: Any) -> dict[str, Any]:
        """JSON-safe dict with keys: board, current_player, legal_moves, scores,
        status ("playing" | "finished"), winner, seat_labels, last_event."""
        ...
