def test_list_games(client):
    res = client.get("/api/games")
    assert res.status_code == 200
    assert res.json() == [{"id": "othello", "name": "Othello"}]


def test_index_page_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")


def test_common_js_served(client):
    res = client.get("/static/common.js")
    assert res.status_code == 200


def test_othello_view_js_served(client):
    res = client.get("/games/othello/static/view.js")
    assert res.status_code == 200
