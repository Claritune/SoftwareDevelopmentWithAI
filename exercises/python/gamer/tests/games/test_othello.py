import json

from gamer.games.othello import BLACK, OTHELLO, WHITE, initial_board, legal_moves


def test_initial_board():
    board = initial_board()
    assert board[3][3] == WHITE
    assert board[4][4] == WHITE
    assert board[3][4] == BLACK
    assert board[4][3] == BLACK
    empty = [board[r][c] for r in range(8) for c in range(8) if board[r][c] is None]
    assert len(empty) == 60


def test_initial_snapshot():
    snap = OTHELLO.snapshot(OTHELLO.initial_state())
    assert snap["current_player"] == 0
    assert snap["scores"] == [2, 2]
    assert snap["status"] == "playing"
    assert snap["winner"] is None
    assert snap["seat_labels"] == ["Black", "White"]
    assert snap["last_event"] is None
    assert {(m["row"], m["col"]) for m in snap["legal_moves"]} == {(2, 3), (3, 2), (4, 5), (5, 4)}


def test_white_legal_moves_at_start():
    assert set(legal_moves(initial_board(), WHITE)) == {(2, 4), (3, 5), (4, 2), (5, 3)}


def test_snapshot_is_json_safe():
    json.dumps(OTHELLO.snapshot(OTHELLO.initial_state()))
