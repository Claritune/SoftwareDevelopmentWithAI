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


async def test_lobby_lists_waiting_sessions(fake_client):
    a = (await create(fake_client, name="Ann"))["code"]
    b = (await create(fake_client, name="Cat"))["code"]
    await join(fake_client, b, "Bob")
    r = await fake_client.get("/api/games/fake/sessions")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "sessions"
    assert body["payload"] == [{"code": a, "players": [{"seat": 0, "name": "Ann"}]}]


async def test_lobby_unknown_game_404(fake_client):
    r = await fake_client.get("/api/games/nope/sessions")
    assert r.status_code == 404
    assert r.json()["payload"]["code"] == "game_not_found"


async def start(c, game_id) -> tuple[str, dict[int, str], dict]:
    created = await create(c, game_id, "Ann")
    r = await join(c, created["code"], "Bob")
    assert r.status_code == 200
    joined = r.json()["payload"]
    return created["code"], {0: created["player_id"], 1: joined["player_id"]}, joined["state"]


async def move(c, code, player_id, mv, v=1):
    body = {"v": v, "type": "move", "payload": {"player_id": player_id, "move": mv}}
    return await c.post(f"/api/sessions/{code}/moves", json=body)


async def play_out(c, code, ids, state) -> dict:
    for _ in range(100):
        if state["status"] == "finished":
            break
        r = await move(c, code, ids[state["current_player"]], state["legal_moves"][0])
        assert r.status_code == 200, r.text
        state = r.json()["payload"]
    return state


async def test_two_players_finish_othello(client):
    code, ids, state = await start(client, "othello")
    state = await play_out(client, code, ids, state)
    assert state["status"] == "finished"
    assert state["winner"] in (0, 1, None)
    assert sum(state["scores"]) <= 64


async def test_fake_game_finishes_via_api(fake_client):
    code, ids, state = await start(fake_client, "fake")
    state = await play_out(fake_client, code, ids, state)
    assert state["status"] == "finished"
    assert state["version"] == 5


async def test_poll_sees_move(fake_client):
    code, ids, _ = await start(fake_client, "fake")
    r = await move(fake_client, code, ids[0], {"step": 1})
    assert r.status_code == 200
    r = await fake_client.get(f"/api/sessions/{code}")
    state = r.json()["payload"]
    assert state["version"] == 3
    assert state["current_player"] == 1


@pytest.mark.parametrize(
    "case, status, error_code",
    [
        ("wrong-seat", 409, "illegal_move"),
        ("bad-move", 400, "invalid_move"),
        ("unknown-player", 403, "unknown_player"),
        ("wrong-v", 400, "bad_request"),
        ("unknown-code", 404, "session_not_found"),
    ],
)
async def test_move_errors(fake_client, case, status, error_code):
    code, ids, _ = await start(fake_client, "fake")
    pid, mv, v = ids[0], {"step": 1}, 1
    if case == "wrong-seat":
        pid = ids[1]
    elif case == "bad-move":
        mv = {"step": 2}
    elif case == "unknown-player":
        pid = "nope"
    elif case == "wrong-v":
        v = 2
    elif case == "unknown-code":
        code = "ZZZZZZ"
    r = await move(fake_client, code, pid, mv, v)
    assert r.status_code == status
    body = r.json()
    assert body["type"] == "error"
    assert body["payload"]["code"] == error_code


async def test_move_before_join_409(fake_client):
    created = await create(fake_client)
    r = await move(fake_client, created["code"], created["player_id"], {"step": 1})
    assert r.status_code == 409
    assert r.json()["payload"]["code"] == "game_not_started"


async def test_move_after_finish_409(fake_client):
    code, ids, state = await start(fake_client, "fake")
    await play_out(fake_client, code, ids, state)
    r = await move(fake_client, code, ids[1], {"step": 1})
    assert r.status_code == 409
    assert r.json()["payload"]["code"] == "illegal_move"


async def test_join_finished_session_409(fake_client):
    code, ids, state = await start(fake_client, "fake")
    await play_out(fake_client, code, ids, state)
    r = await join(fake_client, code, "Cat")
    assert r.status_code == 409
    assert r.json()["payload"]["code"] == "session_full"
