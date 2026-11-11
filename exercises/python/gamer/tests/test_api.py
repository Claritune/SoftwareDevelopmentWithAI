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
