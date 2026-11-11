import pytest
from fakes import env


async def create(c, game_id="fake", name="Ann"):
    r = await c.post(f"/api/games/{game_id}/sessions", json=env("create", {"name": name}))
    assert r.status_code == 200, r.text
    return r.json()["payload"]


async def join(c, code, name="Bob"):
    return await c.post(f"/api/sessions/{code}/join", json=env("join", {"name": name}))


async def test_list_games_returns_othello(client):
    r = await client.get("/api/games")
    assert r.status_code == 200
    assert r.json() == {
        "v": 1,
        "type": "games",
        "payload": [{"id": "othello", "name": "Othello", "min_players": 2, "max_players": 2}],
    }


async def test_list_games_uses_injected_games(fake_client):
    r = await fake_client.get("/api/games")
    assert [g["id"] for g in r.json()["payload"]] == ["fake"]


async def test_index_is_served(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert r.headers["cache-control"] == "no-cache"


async def test_create_session(fake_client):
    r = await fake_client.post("/api/games/fake/sessions", json=env("create", {"name": "Ann"}))
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "joined"
    payload = body["payload"]
    assert len(payload["code"]) == 6
    assert payload["seat"] == 0
    assert payload["player_id"]
    assert payload["state"]["status"] == "waiting"
    assert payload["state"]["version"] == 1
    assert payload["state"]["game_id"] == "fake"


async def test_join_and_poll(fake_client):
    created = await create(fake_client)
    code = created["code"]
    r = await join(fake_client, code)
    assert r.status_code == 200
    joined = r.json()["payload"]
    assert joined["seat"] == 1
    assert joined["state"]["status"] == "playing"
    r = await fake_client.get(f"/api/sessions/{code}")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "state"
    assert body["payload"]["version"] == 2
    assert len(body["payload"]["players"]) == 2
    assert created["player_id"] not in r.text
    assert joined["player_id"] not in r.text


async def test_join_full_session_409(fake_client):
    code = (await create(fake_client))["code"]
    await join(fake_client, code)
    r = await join(fake_client, code, "Cat")
    assert r.status_code == 409
    assert r.json()["payload"]["code"] == "session_full"


async def test_unknown_session_404(fake_client):
    r = await fake_client.get("/api/sessions/ZZZZZZ")
    assert r.status_code == 404
    assert r.json()["payload"]["code"] == "session_not_found"
    r = await join(fake_client, "ZZZZZZ")
    assert r.status_code == 404
    assert r.json()["payload"]["code"] == "session_not_found"


async def test_unknown_game_404(fake_client):
    r = await fake_client.post("/api/games/nope/sessions", json=env("create", {"name": "Ann"}))
    assert r.status_code == 404
    assert r.json()["payload"]["code"] == "game_not_found"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"json": {"v": 2, "type": "create", "payload": {"name": "Ann"}}},
        {"json": {"v": 1, "type": "create", "payload": {}}},
        {"json": {"v": 1, "type": "create", "payload": {"name": "  "}}},
        {"content": b"nope", "headers": {"content-type": "application/json"}},
    ],
    ids=["wrong-v", "missing-name", "blank-name", "not-json"],
)
async def test_bad_envelope_400(fake_client, kwargs):
    r = await fake_client.post("/api/games/fake/sessions", **kwargs)
    assert r.status_code == 400
    body = r.json()
    assert body["type"] == "error"
    assert body["payload"]["code"] == "bad_request"


async def test_create_othello_session(client):
    state = (await create(client, "othello"))["state"]
    assert len(state["legal_moves"]) == 4
    assert len(state["board"]) == 8
