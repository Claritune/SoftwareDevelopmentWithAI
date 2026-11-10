import pytest

from gamer.games.base import IllegalMove
from gamer.games.othello import OTHELLO
from gamer.games.othello.logic import BLACK, EMPTY, SIZE, WHITE, OthelloState


def test_initial_state_layout():
    state = OTHELLO.initial_state()
    board = state.board
    assert board[3][3] == WHITE and board[4][4] == WHITE
    assert board[3][4] == BLACK and board[4][3] == BLACK
    assert sum(row.count(EMPTY) for row in board) == 60
    assert state.to_move == "black"


def test_initial_status():
    status = OTHELLO.status(OTHELLO.initial_state())
    assert status.scores == {"black": 2, "white": 2}
    assert status.finished is False


def test_to_public_is_8x8_lists():
    public = OTHELLO.to_public(OTHELLO.initial_state())
    board = public["board"]
    assert isinstance(board, list) and len(board) == SIZE
    assert all(isinstance(row, list) and len(row) == SIZE for row in board)


def state_from(rows: list[str], to_move="black") -> OthelloState:
    """rows: 8 strings of 8 chars, 'B' black / 'W' white / '.' empty."""
    m = {"B": BLACK, "W": WHITE, ".": EMPTY}
    return OthelloState(tuple(tuple(m[ch] for ch in row) for row in rows), to_move)


EMPTY_ROW = "." * SIZE


def test_opening_legal_moves():
    init = OTHELLO.initial_state()
    assert set(OTHELLO.legal_moves(init, "black")) == {(2, 3), (3, 2), (4, 5), (5, 4)}
    assert OTHELLO.legal_moves(init, "white") == []


def test_opening_move_flips_and_passes_turn():
    after = OTHELLO.apply_move(OTHELLO.initial_state(), "black", (2, 3))
    assert after.board[2][3] == BLACK
    assert after.board[3][3] == BLACK
    assert OTHELLO.status(after).scores == {"black": 4, "white": 1}
    assert after.to_move == "white"


def test_flips_in_all_eight_directions():
    state = state_from([
        "........",
        "........",
        "..B.B.B.",
        "...WWW..",
        "..BW.WB.",
        "...WWW..",
        "..B.B.B.",
        "........",
    ])
    after = OTHELLO.apply_move(state, "black", (4, 4))
    assert after.board[4][4] == BLACK
    assert all(cell != WHITE for row in after.board for cell in row)
    assert OTHELLO.status(after).scores == {"black": 17, "white": 0}


def test_multi_disc_flip():
    state = state_from(["BWW....."] + [EMPTY_ROW] * 7)
    after = OTHELLO.apply_move(state, "black", (0, 3))
    assert after.board[0][:4] == (BLACK, BLACK, BLACK, BLACK)


def test_occupied_square_is_illegal():
    with pytest.raises(IllegalMove):
        OTHELLO.apply_move(OTHELLO.initial_state(), "black", (3, 3))


def test_move_that_flips_nothing_is_illegal():
    with pytest.raises(IllegalMove):
        OTHELLO.apply_move(OTHELLO.initial_state(), "black", (0, 0))


def test_broken_run_does_not_flip():
    state = state_from(["BW.W...."] + [EMPTY_ROW] * 7)
    with pytest.raises(IllegalMove):
        OTHELLO.apply_move(state, "black", (0, 4))


def test_wrong_seat_is_illegal():
    with pytest.raises(IllegalMove):
        OTHELLO.apply_move(OTHELLO.initial_state(), "white", (2, 4))


@pytest.mark.parametrize("raw", [
    {"row": 8, "col": 0},
    {"row": -1, "col": 0},
    {"row": "a", "col": 1},
    {"row": True, "col": 1},
    {},
])
def test_parse_move_rejects_bad_input(raw):
    with pytest.raises(IllegalMove):
        OTHELLO.parse_move(raw)


def test_parse_move_accepts_valid_input():
    assert OTHELLO.parse_move({"row": 2, "col": 3}) == (2, 3)


def test_forced_pass_keeps_turn():
    state = state_from(["BW......"] + [EMPTY_ROW] * 6 + ["BW......"])
    after = OTHELLO.apply_move(state, "black", (0, 2))
    assert OTHELLO.legal_moves(OthelloState(after.board, "white"), "white") == []
    assert after.to_move == "black"
