def env(type_: str, payload) -> dict:
    return {"v": 1, "type": type_, "payload": payload}


class FakeGame:
    name = "Fake Game"
    min_players = 2
    max_players = 2

    def __init__(self, id: str = "fake", target: int = 3) -> None:
        self.id = id
        self.target = target
