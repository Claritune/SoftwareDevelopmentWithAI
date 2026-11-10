from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from gamer.app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())   # fresh in-memory state per test


@dataclass
class Match:
    sid: str
    black: str   # token
    white: str   # token


@pytest.fixture
def match(client) -> Match:
    a = client.post("/api/games/othello/sessions").json()
    b = client.post(f"/api/sessions/{a['session_id']}/join").json()
    return Match(a["session_id"], a["token"], b["token"])


def headers(token: str) -> dict[str, str]:
    return {"X-Player-Token": token}
