import asyncio
import random

import httpx
import pytest
from fakes import FakeGame
from mock_client import (
    BAD_NAMES,
    GARBAGE_MOVES,
    MALFORMED_BODIES,
    MockClient,
    env,
    mock_http,
    random_json,
    start_match,
)

KNOWN_ERROR_CODES = {
    "bad_request",
    "not_found",
    "method_not_allowed",
    "game_not_found",
    "session_not_found",
    "session_full",
    "unknown_player",
    "game_not_started",
    "invalid_move",
    "illegal_move",
}


@pytest.fixture
async def http():
    async with mock_http() as c:
        yield c


@pytest.fixture
async def fake_http():
    async with mock_http(games={"fake": FakeGame()}) as c:
        yield c


def assert_error(r: httpx.Response, status: int, code: str) -> None:
    assert r.status_code == status, r.text
    assert r.headers["content-type"] == "application/json"
    body = r.json()
    assert body["v"] == 1
    assert body["type"] == "error"
    assert body["payload"]["code"] == code
    assert isinstance(body["payload"]["message"], str)


def assert_well_behaved(r: httpx.Response) -> None:
    """The server never crashes, and every non-200 reply is a protocol error envelope."""
    assert r.status_code < 500, r.text
    if r.status_code != 200:
        assert_error(r, r.status_code, r.json()["payload"]["code"])
        assert r.json()["payload"]["code"] in KNOWN_ERROR_CODES


async def post_targets(http: httpx.AsyncClient) -> dict[str, str]:
    ann, _ = await start_match(http, "othello")
    open_session = MockClient(http)
    await open_session.create("othello")
    return {
        "create": "/api/games/othello/sessions",
        "join": f"/api/sessions/{open_session.code}/join",
        "move": f"/api/sessions/{ann.code}/moves",
    }


@pytest.mark.parametrize("endpoint", ["create", "join", "move"])
@pytest.mark.parametrize("body", MALFORMED_BODIES.values(), ids=MALFORMED_BODIES.keys())
async def test_malformed_body_is_bad_request(http, endpoint, body):
    path = (await post_targets(http))[endpoint]
    r = await MockClient(http).send("POST", path, **body)
    assert_error(r, 400, "bad_request")


@pytest.mark.parametrize("endpoint", ["create", "join"])
@pytest.mark.parametrize("name", BAD_NAMES.values(), ids=BAD_NAMES.keys())
async def test_bad_name_is_bad_request(http, endpoint, name):
    path = (await post_targets(http))[endpoint]
    payload = {} if name is ... else {"name": name}
    r = await MockClient(http).send("POST", path, json=env(endpoint, payload))
    assert_error(r, 400, "bad_request")


@pytest.mark.parametrize(
    "player_id", [None, 123, ["id"], {"id": "x"}], ids=["null", "int", "list", "object"]
)
async def test_mistyped_player_id_is_bad_request(http, player_id):
    ann, _ = await start_match(http, "othello")
    assert_error(await ann.move({"row": 2, "col": 3}, player_id=player_id), 400, "bad_request")


@pytest.mark.parametrize(
    "method, path, status, code",
    [
        ("GET", "/api/nope", 404, "not_found"),
        ("GET", "/api/sessions/ABCDEF/moves", 404, "not_found"),
        ("POST", "/api/games/othello", 405, "method_not_allowed"),
        ("DELETE", "/api/games", 405, "method_not_allowed"),
        ("PUT", "/api/sessions/ABCDEF", 405, "method_not_allowed"),
    ],
)
async def test_unknown_routes_answer_with_envelope(http, method, path, status, code):
    assert_error(await MockClient(http).send(method, path), status, code)


async def test_unknown_static_path_is_not_an_envelope(http):
    r = await MockClient(http).send("GET", "/no-such-file.js")
    assert r.status_code == 404
    assert "type" not in r.text


@pytest.mark.parametrize(
    "code",
    ["", "A" * 5000, "%00%FF", "..%2F..%2Fgames", "ÄÖÜ", "ABC DEF", "<script>"],
    ids=["empty", "long", "control-bytes", "traversal", "unicode", "space", "html"],
)
async def test_hostile_session_codes_are_not_found(http, code):
    mock = MockClient(http)
    moved = await mock.move({}, code=code, player_id="someone")
    for r in (await mock.poll(code), await mock.join(code), moved):
        assert r.status_code in (404, 405), r.text
        assert_well_behaved(r)


async def test_session_code_is_case_insensitive(http):
    ann, _ = await start_match(http, "othello")
    r = await ann.poll(ann.code.lower())
    assert r.status_code == 200
    assert r.json()["payload"]["code"] == ann.code


@pytest.mark.parametrize("move", GARBAGE_MOVES.values(), ids=GARBAGE_MOVES.keys())
async def test_garbage_othello_moves_are_invalid(http, move):
    ann, _ = await start_match(http, "othello")
    before = await ann.state()
    assert_error(await ann.move(move), 400, "invalid_move")
    assert await ann.state() == before


@pytest.mark.parametrize(
    "who, move",
    [
        ("ann", {"row": 3, "col": 3}),  # occupied
        ("ann", {"row": 0, "col": 0}),  # flips nothing
        ("bob", {"row": 2, "col": 4}),  # out of turn (legal for White later)
    ],
    ids=["occupied", "no-flip", "out-of-turn"],
)
async def test_illegal_othello_moves_leave_state_untouched(http, who, move):
    ann, bob = await start_match(http, "othello")
    before = await ann.state()
    assert_error(await {"ann": ann, "bob": bob}[who].move(move), 409, "illegal_move")
    assert await ann.state() == before


async def test_player_id_does_not_work_across_sessions(http):
    ann, _ = await start_match(http, "othello")
    cat, _ = await start_match(http, "othello")
    r = await ann.move({"row": 2, "col": 3}, code=cat.code)
    assert_error(r, 403, "unknown_player")


async def test_spectator_cannot_move(http):
    ann, _ = await start_match(http, "othello")
    assert_error(await ann.move({"row": 2, "col": 3}, player_id="spectator"), 403, "unknown_player")


async def test_replayed_move_is_rejected(http):
    ann, _ = await start_match(http, "othello")
    assert (await ann.move({"row": 2, "col": 3})).status_code == 200
    version = (await ann.state())["version"]
    assert_error(await ann.move({"row": 2, "col": 3}), 409, "illegal_move")
    assert (await ann.state())["version"] == version


async def test_concurrent_joins_fill_exactly_one_seat(fake_http):
    host = MockClient(fake_http, "Host")
    await host.create("fake")
    crowd = [MockClient(fake_http, f"P{i}") for i in range(20)]
    results = await asyncio.gather(*(m.join(host.code) for m in crowd))
    assert sorted(r.status_code for r in results) == [200] + [409] * 19
    for r in results:
        if r.status_code != 200:
            assert_error(r, 409, "session_full")
    state = await host.state()
    assert len(state["players"]) == 2
    assert state["version"] == 2


async def test_concurrent_duplicate_moves_apply_once(fake_http):
    ann, bob = await start_match(fake_http, "fake")
    results = await asyncio.gather(*(ann.move({"step": 1}) for _ in range(10)))
    assert sorted(r.status_code for r in results) == [200] + [409] * 9
    state = await bob.state()
    assert state["version"] == 3
    assert state["board"] == {"count": 1}


async def test_errors_do_not_corrupt_a_game_in_progress(http):
    ann, bob = await start_match(http, "othello")
    players = {0: ann, 1: bob}
    rng = random.Random(0)
    state = await ann.state()
    while state["status"] == "playing":
        current, other = players[state["current_player"]], players[1 - state["current_player"]]
        await other.move(state["legal_moves"][0])
        await current.move(random_json(rng))
        await current.send("POST", f"/api/sessions/{ann.code}/moves", content=b"{")
        assert await ann.state() == state
        r = await current.move(state["legal_moves"][0])
        assert r.status_code == 200, r.text
        assert r.json()["payload"]["version"] == state["version"] + 1
        state = r.json()["payload"]
    assert state["status"] == "finished"
    assert_error(await ann.move({"row": 0, "col": 0}), 409, "illegal_move")


async def test_fuzzed_requests_never_crash_the_server(http):
    ann, _ = await start_match(http, "othello")
    mock = MockClient(http)
    rng = random.Random(1234)
    paths = [
        "/api/games/othello/sessions",
        "/api/games/nope/sessions",
        f"/api/sessions/{ann.code}/join",
        f"/api/sessions/{ann.code}/moves",
    ]
    for _ in range(300):
        body = random_json(rng)
        if rng.random() < 0.5:
            payload = {"player_id": ann.player_id, "move": body} if rng.random() < 0.5 else body
            body = {"v": 1, "type": "x", "payload": payload}
        assert_well_behaved(await mock.send("POST", rng.choice(paths), json=body))
    state = await ann.state()
    assert state["status"] == "playing"
    assert sum(state["scores"]) == 4 + state["version"] - 2
