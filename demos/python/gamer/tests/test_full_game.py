from conftest import headers


def test_full_game_via_api(client, match):
    tokens = {"black": match.black, "white": match.white}
    for _ in range(100):
        states = {s: client.get(f"/api/sessions/{match.sid}/state", headers=headers(t)).json()
                  for s, t in tokens.items()}
        if states["black"]["lifecycle"] == "finished":
            break
        seat = states["black"]["status"]["to_move"]
        st = states[seat]
        r = client.post(f"/api/sessions/{match.sid}/moves", headers=headers(tokens[seat]),
                        json={"move": st["legal_moves"][0], "version": st["version"]})
        assert r.status_code == 200
    final = states["black"]
    assert final["lifecycle"] == "finished"
    scores = final["status"]["scores"]
    assert sum(scores.values()) <= 64
    expected = None if scores["black"] == scores["white"] else max(scores, key=scores.get)
    assert final["status"]["winner"] == expected
    late = client.post(f"/api/sessions/{match.sid}/moves", headers=headers(match.black),
                       json={"move": {"row": 0, "col": 0}, "version": final["version"]})
    assert late.status_code == 409
