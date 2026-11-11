from dataclasses import dataclass


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
