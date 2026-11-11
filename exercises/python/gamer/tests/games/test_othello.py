import json

import pytest

from gamer.games.base import IllegalMove, InvalidMove
from gamer.games.othello import (
    BLACK,
    OTHELLO,
    SIZE,
    WHITE,
    Board,
    OthelloMove,
    OthelloState,
    flips,
    initial_board,
    legal_moves,
)

CELL = {"B": BLACK, "W": WHITE, ".": None}


def board_from(rows: dict[int, str]) -> Board:
    return tuple(
        tuple([CELL[ch] for ch in rows.get(r, "")] + [None] * (SIZE - len(rows.get(r, ""))))
        for r in range(SIZE)
    )


def count(board: Board, seat: int) -> int:
    return sum(row.count(seat) for row in board)


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


def test_parse_move_valid():
    assert OTHELLO.parse_move({"row": 2, "col": 3}) == OthelloMove(2, 3)


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [2, 3],
        {},
        {"row": 2},
        {"row": "2", "col": 3},
        {"row": True, "col": 3},
        {"row": 2.0, "col": 3},
        {"row": 8, "col": 0},
        {"row": -1, "col": 0},
    ],
)
def test_parse_move_invalid(payload):
    with pytest.raises(InvalidMove):
        OTHELLO.parse_move(payload)


def test_first_move_flips():
    start = OTHELLO.initial_state()
    state = OTHELLO.apply_move(start, BLACK, OthelloMove(2, 3))
    assert state.board[2][3] == BLACK
    assert state.board[3][3] == BLACK
    assert state.current == WHITE
    assert OTHELLO.snapshot(state)["scores"] == [4, 1]
    assert start.board == initial_board()


def test_multi_direction_flip():
    start = OthelloState(board_from({1: "..WB", 2: ".W..", 3: ".B.."}), BLACK)
    state = OTHELLO.apply_move(start, BLACK, OthelloMove(1, 1))
    for r, c in [(1, 1), (1, 2), (2, 1)]:
        assert state.board[r][c] == BLACK
    snap = OTHELLO.snapshot(state)
    assert snap["scores"] == [5, 0]
    assert snap["status"] == "finished"


def test_out_of_turn_raises():
    with pytest.raises(IllegalMove):
        OTHELLO.apply_move(OTHELLO.initial_state(), WHITE, OthelloMove(2, 4))


def test_no_flip_raises():
    with pytest.raises(IllegalMove):
        OTHELLO.apply_move(OTHELLO.initial_state(), BLACK, OthelloMove(0, 0))


def test_occupied_raises():
    with pytest.raises(IllegalMove):
        OTHELLO.apply_move(OTHELLO.initial_state(), BLACK, OthelloMove(3, 3))


def test_auto_pass():
    start = OthelloState(board_from({0: "BW", 2: "BW"}), current=BLACK)
    state = OTHELLO.apply_move(start, BLACK, OthelloMove(0, 2))
    assert state.current == BLACK
    assert state.last_event == "White passed"
    snap = OTHELLO.snapshot(state)
    assert snap["status"] == "playing"
    assert snap["legal_moves"] == [{"row": 2, "col": 2}]


def test_game_over_winner():
    start = OthelloState(board_from({0: "BW"}), BLACK)
    state = OTHELLO.apply_move(start, BLACK, OthelloMove(0, 2))
    assert state.current is None
    snap = OTHELLO.snapshot(state)
    assert snap["status"] == "finished"
    assert snap["scores"] == [3, 0]
    assert snap["winner"] == 0
    assert snap["legal_moves"] == []


def finished_draw() -> OthelloState:
    start = OthelloState(board_from({0: "BW", 7: "WWW"}), BLACK)
    return OTHELLO.apply_move(start, BLACK, OthelloMove(0, 2))


def test_game_over_draw():
    snap = OTHELLO.snapshot(finished_draw())
    assert snap["status"] == "finished"
    assert snap["scores"] == [3, 3]
    assert snap["winner"] is None


def test_move_after_game_over_raises():
    state = finished_draw()
    for seat in (BLACK, WHITE):
        with pytest.raises(IllegalMove):
            OTHELLO.apply_move(state, seat, OthelloMove(5, 5))


def test_self_play_invariants():
    state = OTHELLO.initial_state()
    for _ in range(60):
        if state.current is None:
            break
        seat = state.current
        r, c = legal_moves(state.board, seat)[0]
        n = len(flips(state.board, seat, r, c))
        mine, theirs = count(state.board, seat), count(state.board, 1 - seat)
        state = OTHELLO.apply_move(state, seat, OthelloMove(r, c))
        assert count(state.board, seat) == mine + 1 + n
        assert count(state.board, 1 - seat) == theirs - n
    assert state.current is None
    snap = OTHELLO.snapshot(state)
    assert snap["status"] == "finished"
    black, white = snap["scores"]
    expected = None if black == white else (BLACK if black > white else WHITE)
    assert snap["winner"] == expected
