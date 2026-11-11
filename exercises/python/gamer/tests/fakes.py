from dataclasses import dataclass

from gamer.games.base import IllegalMove, InvalidMove


def env(type_: str, payload) -> dict:
    return {"v": 1, "type": type_, "payload": payload}


@dataclass(frozen=True)
class FakeState:
    count: int = 0
    current: int | None = 0


class FakeGame:
    name = "Fake Game"
    min_players = 2
    max_players = 2

    def __init__(self, id: str = "fake", target: int = 3) -> None:
        self.id = id
        self.target = target

    def initial_state(self) -> FakeState:
        return FakeState()

    def parse_move(self, payload) -> int:
        if payload != {"step": 1}:
            raise InvalidMove("expected {'step': 1}")
        return 1

    def apply_move(self, state: FakeState, seat: int, move: int) -> FakeState:
        if state.current != seat:
            raise IllegalMove("not your turn")
        count = state.count + move
        return FakeState(count, None if count >= self.target else 1 - seat)

    def snapshot(self, state: FakeState) -> dict:
        finished = state.current is None
        return {
            "board": {"count": state.count},
            "current_player": state.current,
            "legal_moves": [] if finished else [{"step": 1}],
            "scores": [0, 0],
            "status": "finished" if finished else "playing",
            "winner": None,
            "seat_labels": ["First", "Second"],
            "last_event": None,
        }
