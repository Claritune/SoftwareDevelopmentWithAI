from gamer.games.othello import OTHELLO
from gamer.games.othello.logic import BLACK, EMPTY, SIZE, WHITE


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
