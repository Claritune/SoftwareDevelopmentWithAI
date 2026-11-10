from conftest import headers


def test_create_session(client):
    res = client.post("/api/games/othello/sessions")
    assert res.status_code == 201
    body = res.json()
    assert body["session_id"]
    assert body["seat"] == "black"
    assert body["token"]
    listed = client.get("/api/games/othello/sessions").json()
    assert listed == [{"session_id": body["session_id"], "game_id": "othello"}]


def test_join_fills_session(client, match):
    assert client.get("/api/games/othello/sessions").json() == []
    res = client.post(f"/api/sessions/{match.sid}/join")
    assert res.status_code == 409
    assert "detail" in res.json()


def test_state_with_token(client, match):
    res = client.get(f"/api/sessions/{match.sid}/state", headers=headers(match.black))
    assert res.status_code == 200
    s = res.json()
    assert s["your_seat"] == "black"
    assert s["lifecycle"] == "playing"
    assert s["seats"] == {"black": True, "white": True}
    board = s["public_state"]["board"]
    assert len(board) == 8 and all(len(row) == 8 for row in board)
    assert s["version"] == 2


def test_state_without_token(client, match):
    s = client.get(f"/api/sessions/{match.sid}/state").json()
    assert s["your_seat"] is None
    assert s["legal_moves"] == []


def test_state_errors(client, match):
    res = client.get(f"/api/sessions/{match.sid}/state", headers=headers("bogus"))
    assert res.status_code == 403
    assert res.json() == {"detail": "invalid or missing player token"}
    assert client.get("/api/sessions/missing/state").status_code == 404
    assert client.get("/api/games/chess/sessions").status_code == 404
    assert client.post("/api/games/chess/sessions").status_code == 404


def test_pages(client):
    for path in ("/games/othello", "/games/othello/sessions/anything"):
        res = client.get(path)
        assert res.status_code == 200, path
        assert res.headers["content-type"].startswith("text/html")
    assert client.get("/games/chess").status_code == 404
