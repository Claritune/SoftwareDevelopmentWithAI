"""Hypothesis strategies that emulate what clients can send to the server."""

import string
from typing import Any
from urllib.parse import quote

from hypothesis import strategies as st

from gamer.games.othello import SIZE, OthelloGame, OthelloState, legal_moves
from gamer.sessions import CODE_ALPHABET, CODE_LENGTH

json_scalars = (
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(max_size=20)
)

json_values: st.SearchStrategy[Any] = st.recursive(
    json_scalars,
    lambda children: (
        st.lists(children, max_size=4)
        | st.dictionaries(
            st.sampled_from(["v", "type", "payload", "name", "player_id", "move", "row", "col"])
            | st.text(max_size=5),
            children,
            max_size=4,
        )
    ),
    max_leaves=12,
)

# Names whose validity is unambiguous: ASCII letters padded with plain spaces.
valid_names = st.builds(
    lambda pad_l, core, pad_r: " " * pad_l + core + " " * pad_r,
    st.integers(0, 3),
    st.text(string.ascii_letters + string.digits, min_size=1, max_size=32).filter(
        lambda s: s.strip() == s
    ),
    st.integers(0, 3),
)
invalid_names = st.one_of(
    st.just(""),
    st.text(" \t\n", min_size=1, max_size=5),
    st.text(string.ascii_letters, min_size=33, max_size=60),
    json_values.filter(lambda v: not isinstance(v, str)),
)
# Anything a hostile client might type, including control characters and exotic whitespace.
any_names = st.text(max_size=40)

on_board = st.integers(0, SIZE - 1)
cells = st.fixed_dictionaries({"row": on_board, "col": on_board})
near_miss_moves = st.one_of(
    st.fixed_dictionaries({"row": st.integers(-3, SIZE + 2), "col": st.integers(-3, SIZE + 2)}),
    st.fixed_dictionaries({"row": on_board | st.booleans() | st.floats(0, 7), "col": on_board}),
    st.fixed_dictionaries({"row": st.text(max_size=2), "col": st.text(max_size=2)}),
    st.dictionaries(st.sampled_from(["row", "col", "x"]), on_board, max_size=3),
)
any_moves = st.one_of(cells, near_miss_moves, json_values)

valid_code_shape = st.text(CODE_ALPHABET, min_size=CODE_LENGTH, max_size=CODE_LENGTH)
# Arbitrary URL path segments, percent-encoded the way a browser would send them.
url_segments = st.text(st.characters(blacklist_categories=("Cs",)), max_size=12).map(
    lambda s: quote(s, safe="")
)


@st.composite
def broken_envelopes(draw, valid: dict) -> Any:
    """A valid request body with exactly one part of the envelope broken."""
    body = dict(valid)
    kind = draw(st.sampled_from(["drop", "bad_v", "bad_payload", "bad_type", "not_object"]))
    if kind == "drop":
        del body[draw(st.sampled_from(sorted(body)))]
    elif kind == "bad_v":
        body["v"] = draw(json_values.filter(lambda v: v != 1 or isinstance(v, bool | float)))
    elif kind == "bad_payload":
        body["payload"] = draw(json_values.filter(lambda v: not isinstance(v, dict)))
    elif kind == "bad_type":
        body["type"] = draw(json_values.filter(lambda v: not isinstance(v, str)))
    else:
        return draw(json_values.filter(lambda v: not isinstance(v, dict)))
    return body


@st.composite
def othello_playouts(draw, max_moves: int = 64) -> list[OthelloState]:
    """A random legal Othello game as the list of states it passes through."""
    game = OthelloGame()
    states = [game.initial_state()]
    for _ in range(draw(st.integers(0, max_moves))):
        state = states[-1]
        if state.current is None:
            break
        r, c = draw(st.sampled_from(legal_moves(state.board, state.current)))
        states.append(game.apply_move(state, state.current, game.parse_move({"row": r, "col": c})))
    return states


othello_reachable_states = othello_playouts().map(lambda states: states[-1])

arbitrary_boards = st.lists(
    st.lists(st.sampled_from([None, 0, 1]), min_size=SIZE, max_size=SIZE).map(tuple),
    min_size=SIZE,
    max_size=SIZE,
).map(tuple)
