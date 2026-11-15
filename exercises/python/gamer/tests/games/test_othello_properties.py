import json

import pytest
from hypothesis import given
from hypothesis import strategies as st
from strategies import any_moves, arbitrary_boards, othello_playouts, othello_reachable_states

from gamer.games.base import IllegalMove, InvalidMove
from gamer.games.othello import SIZE, OthelloGame, OthelloMove, flips, legal_moves

GAME = OthelloGame()
SNAPSHOT_KEYS = {
    "board",
    "current_player",
    "legal_moves",
    "scores",
    "status",
    "winner",
    "seat_labels",
    "last_event",
}

# The eight symmetries of the square, as maps on (row, col).
N = SIZE - 1
SYMMETRIES = {
    "identity": lambda r, c: (r, c),
    "rot90": lambda r, c: (c, N - r),
    "rot180": lambda r, c: (N - r, N - c),
    "rot270": lambda r, c: (N - c, r),
    "flip-h": lambda r, c: (r, N - c),
    "flip-v": lambda r, c: (N - r, c),
    "transpose": lambda r, c: (c, r),
    "anti-transpose": lambda r, c: (N - c, N - r),
}


def transform(board, g):
    out = [[None] * SIZE for _ in range(SIZE)]
    for r in range(SIZE):
        for c in range(SIZE):
            nr, nc = g(r, c)
            out[nr][nc] = board[r][c]
    return tuple(tuple(row) for row in out)


def count(board, value):
    return sum(row.count(value) for row in board)


@given(othello_playouts())
def test_each_move_places_one_disc_and_only_flips_opponent_discs(states):
    for before, after in zip(states, states[1:], strict=False):
        mover = before.current
        changed = [
            (r, c)
            for r in range(SIZE)
            for c in range(SIZE)
            if before.board[r][c] != after.board[r][c]
        ]
        placed = [p for p in changed if before.board[p[0]][p[1]] is None]
        flipped = [p for p in changed if before.board[p[0]][p[1]] == 1 - mover]
        assert len(placed) == 1
        assert flipped and len(placed) + len(flipped) == len(changed)
        assert all(after.board[r][c] == mover for r, c in changed)
        assert count(after.board, None) == count(before.board, None) - 1
        assert count(after.board, mover) == count(before.board, mover) + 1 + len(flipped)


@given(othello_reachable_states)
def test_advertised_legal_moves_are_exactly_the_accepted_moves(state):
    snap = GAME.snapshot(state)
    advertised = {(m["row"], m["col"]) for m in snap["legal_moves"]}
    accepted = set()
    for r in range(SIZE):
        for c in range(SIZE):
            for seat in (0, 1):
                try:
                    GAME.apply_move(state, seat, OthelloMove(r, c))
                except IllegalMove:
                    continue
                assert seat == state.current
                accepted.add((r, c))
    assert accepted == advertised


@given(othello_playouts())
def test_turns_alternate_unless_the_opponent_must_pass(states):
    for before, after in zip(states, states[1:], strict=False):
        mover, opponent = before.current, 1 - before.current
        if after.current == opponent:
            assert after.last_event is None
        elif after.current == mover:
            assert not legal_moves(after.board, opponent)
            assert after.last_event
        else:
            assert not legal_moves(after.board, mover)
            assert not legal_moves(after.board, opponent)


@given(othello_reachable_states)
def test_snapshot_honours_the_game_contract(state):
    snap = GAME.snapshot(state)
    assert set(snap) == SNAPSHOT_KEYS
    assert json.loads(json.dumps(snap)) == snap
    black, white = snap["scores"]
    assert black + white == count(state.board, 0) + count(state.board, 1)
    if snap["status"] == "playing":
        assert snap["current_player"] in (0, 1)
        assert snap["legal_moves"], "a playing state must offer a move (passes are automatic)"
        assert snap["winner"] is None
    else:
        assert snap["status"] == "finished"
        assert snap["current_player"] is None and snap["legal_moves"] == []
        assert snap["winner"] == (None if black == white else int(white > black))


@given(othello_playouts(max_moves=200))
def test_every_game_ends_within_sixty_moves(states):
    assert len(states) - 1 <= SIZE * SIZE - 4
    if states[-1].current is None:
        assert GAME.snapshot(states[-1])["status"] == "finished"


@pytest.mark.parametrize("name", SYMMETRIES)
@given(board=arbitrary_boards, seat=st.sampled_from([0, 1]))
def test_rules_are_invariant_under_board_symmetries(name, board, seat):
    g = SYMMETRIES[name]
    expected = {g(r, c) for r, c in legal_moves(board, seat)}
    assert set(legal_moves(transform(board, g), seat)) == expected


@given(arbitrary_boards, st.sampled_from([0, 1]), st.integers(0, N), st.integers(0, N))
def test_rules_are_invariant_under_colour_swap(board, seat, r, c):
    swapped = tuple(tuple(None if v is None else 1 - v for v in row) for row in board)
    assert sorted(flips(swapped, 1 - seat, r, c)) == sorted(flips(board, seat, r, c))


@given(any_moves)
def test_parse_move_accepts_exactly_on_board_integer_cells(payload):
    well_formed = isinstance(payload, dict) and all(
        type(payload.get(k)) is int and 0 <= payload[k] < SIZE for k in ("row", "col")
    )
    try:
        move = GAME.parse_move(payload)
    except InvalidMove:
        assert not well_formed
    else:
        assert well_formed
        assert (move.row, move.col) == (payload["row"], payload["col"])
