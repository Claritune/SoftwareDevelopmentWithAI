"""A scriptable API client that speaks the envelope protocol and can deliberately break it."""

import random
from contextlib import asynccontextmanager
from typing import Any

import httpx

from gamer.app import create_app

JSON = {"content-type": "application/json"}

# Bodies that are broken at the transport/envelope level; every POST endpoint must reject
# them with a 400 bad_request envelope.
MALFORMED_BODIES: dict[str, dict[str, Any]] = {
    "empty": {"content": b"", "headers": JSON},
    "not-json": {"content": b"nope", "headers": JSON},
    "truncated-json": {"content": b'{"v": 1, "type": "x", "payload": {', "headers": JSON},
    "non-utf8": {"content": b"\xff\xfe\xfa", "headers": JSON},
    "deeply-nested": {"content": b"[" * 100_000 + b"]" * 100_000, "headers": JSON},
    "huge-number": {"content": b'{"v": 1' + b"0" * 5000 + b"}", "headers": JSON},
    "text-plain": {"content": b'{"v": 1, "type": "x", "payload": {}}', "headers": {}},
    "null": {"json": None},
    "array": {"json": []},
    "string": {"json": "hello"},
    "number": {"json": 1},
    "wrong-v": {"json": {"v": 2, "type": "x", "payload": {}}},
    "v-as-string": {"json": {"v": "1", "type": "x", "payload": {}}},
    "v-missing": {"json": {"type": "x", "payload": {}}},
    "type-missing": {"json": {"v": 1, "payload": {}}},
    "payload-missing": {"json": {"v": 1, "type": "x"}},
    "payload-array": {"json": {"v": 1, "type": "x", "payload": []}},
    "payload-null": {"json": {"v": 1, "type": "x", "payload": None}},
}

# Payloads that are well-formed envelopes but carry a bad name.
BAD_NAMES: dict[str, Any] = {
    "missing": ...,
    "empty": "",
    "blank": "   ",
    "too-long": "x" * 33,
    "int": 5,
    "null": None,
    "list": ["Ann"],
    "object": {"first": "Ann"},
}

# Move values that no game should accept as well-formed.
GARBAGE_MOVES: dict[str, Any] = {
    "null": None,
    "string": "d3",
    "list": [2, 3],
    "empty-object": {},
    "row-only": {"row": 2},
    "bool": {"row": True, "col": 3},
    "float": {"row": 2.0, "col": 3},
    "string-coords": {"row": "2", "col": "3"},
    "negative": {"row": -1, "col": 3},
    "too-big": {"row": 8, "col": 3},
    "bigint": {"row": 2**70, "col": 3},
    "nested": {"row": {"row": 2}, "col": 3},
}


def env(type_: str, payload: Any) -> dict:
    return {"v": 1, "type": type_, "payload": payload}


def random_json(rng: random.Random, depth: int = 0) -> Any:
    """A random JSON value, biased toward shapes that look almost valid."""
    kinds = ["null", "bool", "int", "float", "str"]
    if depth < 3:
        kinds += ["list", "dict", "dict"]
    kind = rng.choice(kinds)
    if kind == "null":
        return None
    if kind == "bool":
        return rng.random() < 0.5
    if kind == "int":
        return rng.choice([0, 1, -1, 7, 8, 2**31, -(2**63), rng.randint(-100, 100)])
    if kind == "float":
        return rng.choice([0.5, -0.0, 1e308, rng.uniform(-10, 10)])
    if kind == "str":
        return rng.choice(["", " ", "1", "row", "\u0000", "é" * 40, "<script>", "x" * 1000])
    if kind == "list":
        return [random_json(rng, depth + 1) for _ in range(rng.randint(0, 3))]
    keys = ["v", "type", "payload", "name", "player_id", "move", "row", "col", "step", "x"]
    return {rng.choice(keys): random_json(rng, depth + 1) for _ in range(rng.randint(0, 4))}


class MockClient:
    """One player at the HTTP boundary.

    Happy-path helpers remember the session code and player_id so tests can script a
    match, while ``send`` and the keyword overrides let a test break any part of a request.
    """

    def __init__(self, http: httpx.AsyncClient, name: str = "Mock") -> None:
        self.http = http
        self.name = name
        self.code: str | None = None
        self.player_id: str | None = None
        self.seat: int | None = None

    async def send(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return await self.http.request(method, path, **kwargs)

    def _remember(self, r: httpx.Response) -> httpx.Response:
        if r.status_code == 200:
            payload = r.json()["payload"]
            self.code, self.player_id, self.seat = (
                payload["code"],
                payload["player_id"],
                payload["seat"],
            )
        return r

    async def create(self, game_id: str, name: str | None = None) -> httpx.Response:
        body = env("create", {"name": name or self.name})
        return self._remember(await self.send("POST", f"/api/games/{game_id}/sessions", json=body))

    async def join(self, code: str, name: str | None = None) -> httpx.Response:
        body = env("join", {"name": name or self.name})
        return self._remember(await self.send("POST", f"/api/sessions/{code}/join", json=body))

    async def poll(self, code: str | None = None) -> httpx.Response:
        return await self.send("GET", f"/api/sessions/{code or self.code}")

    async def move(
        self,
        move: Any,
        *,
        code: str | None = None,
        player_id: Any = ...,
        v: Any = 1,
    ) -> httpx.Response:
        pid = self.player_id if player_id is ... else player_id
        body = {"v": v, "type": "move", "payload": {"player_id": pid, "move": move}}
        return await self.send("POST", f"/api/sessions/{code or self.code}/moves", json=body)

    async def state(self) -> dict:
        r = await self.poll()
        assert r.status_code == 200, r.text
        return r.json()["payload"]


async def start_match(http: httpx.AsyncClient, game_id: str) -> tuple[MockClient, MockClient]:
    """Two mock players seated in a fresh, playing session."""
    ann, bob = MockClient(http, "Ann"), MockClient(http, "Bob")
    assert (await ann.create(game_id)).status_code == 200
    assert (await bob.join(ann.code)).status_code == 200
    return ann, bob


@asynccontextmanager
async def mock_http(**app_kwargs: Any):
    """An in-process client that turns unhandled server exceptions into 500 responses,
    so robustness tests observe crashes the way a real client would."""
    transport = httpx.ASGITransport(app=create_app(**app_kwargs), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
