from pathlib import Path

import gamer
import pytest
from conftest import headers
from fastapi.testclient import TestClient
from gamer.app import create_app
from stub_game import STUB


@pytest.fixture
def stub_client() -> TestClient:
    return TestClient(create_app(registry={STUB.id: STUB}))


def test_directory_lists_only_stub(stub_client):
    assert stub_client.get("/api/games").json() == [{"id": "stub", "name": "Stub"}]


def test_stub_pages_and_static(stub_client):
    assert stub_client.get("/games/stub/static/view.js").status_code == 200
    assert stub_client.get("/games/stub").status_code == 200


def test_stub_game_plays_to_finish(stub_client):
    a = stub_client.post("/api/games/stub/sessions").json()
    b = stub_client.post(f"/api/sessions/{a['session_id']}/join").json()
    sid = a["session_id"]
    tokens = {a["seat"]: a["token"], b["seat"]: b["token"]}
    assert set(tokens) == {"x", "o"}
    version = 2
    for seat, cell in [("x", 0), ("o", 1), ("x", 2)]:
        r = stub_client.post(f"/api/sessions/{sid}/moves", headers=headers(tokens[seat]),
                             json={"move": {"cell": cell}, "version": version})
        assert r.status_code == 200
        res = r.json()
        version = res["version"]
    assert res["lifecycle"] == "finished"
    assert res["status"]["winner"] == "x"
    late = stub_client.post(f"/api/sessions/{sid}/moves", headers=headers(tokens["o"]),
                            json={"move": {"cell": 3}, "version": version})
    assert late.status_code == 409


@pytest.mark.parametrize("name", ["app.py", "sessions.py", "protocol.py", "games/base.py"])
def test_core_is_game_agnostic(name):
    source = (Path(gamer.__file__).parent / name).read_text().lower()
    assert "othello" not in source
