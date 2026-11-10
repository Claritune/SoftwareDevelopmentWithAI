from conftest import headers


def post_move(client, sid, token, move, version):
    hdrs = headers(token) if token is not None else {}
    return client.post(f"/api/sessions/{sid}/moves",
                       json={"move": move, "version": version}, headers=hdrs)


def state(client, sid, token):
    return client.get(f"/api/sessions/{sid}/state", headers=headers(token)).json()


def test_black_moves(client, match):
    res = post_move(client, match.sid, match.black, {"row": 2, "col": 3}, 2)
    assert res.status_code == 200
    s = res.json()
    assert s["version"] == 3
    assert s["public_state"]["board"][2][3] == "black"
    assert s["legal_moves"] == []
    w = state(client, match.sid, match.white)
    assert w["legal_moves"] != []
    assert w["status"]["to_move"] == "white"


def test_white_moving_first_is_409(client, match):
    res = post_move(client, match.sid, match.white, {"row": 2, "col": 4}, 2)
    assert res.status_code == 409
    assert "detail" in res.json()


def test_stale_version_is_409(client, match):
    res = post_move(client, match.sid, match.black, {"row": 2, "col": 3}, 1)
    assert res.status_code == 409
    assert "detail" in res.json()
    assert state(client, match.sid, match.black)["version"] == 2


def test_illegal_move_is_400(client, match):
    res = post_move(client, match.sid, match.black, {"row": 0, "col": 0}, 2)
    assert res.status_code == 400
    assert "detail" in res.json()
    res = post_move(client, match.sid, match.black, {"x": 1}, 2)
    assert res.status_code == 400
    assert "detail" in res.json()


def test_token_and_session_errors(client, match):
    move = {"row": 2, "col": 3}
    assert post_move(client, match.sid, "bogus", move, 2).status_code == 403
    assert post_move(client, match.sid, None, move, 2).status_code == 403
    assert post_move(client, "missing", match.black, move, 2).status_code == 404


def test_move_in_waiting_session_is_409(client):
    a = client.post("/api/games/othello/sessions").json()
    res = post_move(client, a["session_id"], a["token"], {"row": 2, "col": 3}, 1)
    assert res.status_code == 409
