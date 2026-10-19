from typing import NamedTuple

from helpers import tick_n, tick_to

from cats_vs_mutants.core.config import CatType, Config
from cats_vs_mutants.core.entities import PlaceResult, Status
from cats_vs_mutants.core.game import Game
from cats_vs_mutants.core.waves import default_waves


class Move(NamedTuple):
    tick: int  # place after the counter reaches this tick
    type: CatType
    lane: int
    col: int


R, H, S, L = CatType.RICH, CatType.HISSING, CatType.SLEEPY, CatType.LASER

# The same moves as scripts/demo.txt: a full winning game.
WINNING_GAME = [
    Move(0, R, 2, 0), Move(1, R, 1, 0), Move(2, R, 3, 0),
    Move(81, R, 0, 0), Move(100, R, 4, 0), Move(162, H, 2, 1),
    Move(241, H, 0, 1), Move(300, H, 4, 1), Move(322, H, 1, 1),
    Move(401, H, 3, 1), Move(480, H, 2, 2), Move(500, H, 1, 2),
    Move(561, H, 3, 2), Move(640, H, 0, 2), Move(660, H, 4, 2),
    Move(790, S, 2, 6), Move(801, L, 2, 3), Move(882, L, 3, 3),
    Move(930, S, 3, 6), Move(1010, S, 1, 6), Move(1041, L, 1, 3),
    Move(1120, H, 1, 2), Move(1140, H, 1, 1), Move(1201, H, 1, 1),
    Move(1281, H, 1, 1), Move(1308, R, 1, 0), Move(1348, R, 1, 0),
    Move(1388, R, 1, 0), Move(1428, R, 1, 0), Move(1468, R, 1, 0),
    Move(1508, R, 1, 0), Move(1548, R, 1, 0), Move(1588, R, 1, 0),
    Move(1620, L, 0, 3),
]  # fmt: skip


def play(moves: list[Move], max_ticks: int) -> Game:
    game = Game(Config(), default_waves())
    for m in moves:
        tick_to(game, m.tick)
        assert game.place(m.type, m.lane, m.col) == PlaceResult.OK, m
    tick_to(game, max_ticks)
    return game


def test_full_game_sensible_play_wins_all_three_waves():
    game = play(WINNING_GAME, 5000)
    assert game.status == Status.WON
    assert game.state.lives == 3
    assert game.state.tick == 1648


def test_full_game_no_cats_loses_during_wave_one():
    game = play([], 5000)
    assert game.status == Status.LOST
    assert game.state.tick == 421
    assert game.current_wave() == 1


def test_determinism_same_inputs_give_same_state():
    a = play(WINNING_GAME, 1000)
    b = play(WINNING_GAME, 1000)
    assert a.state == b.state


def test_determinism_games_diverge_only_through_inputs():
    a = Game(Config(), default_waves())
    b = Game(Config(), default_waves())
    tick_n(a, 300)
    tick_n(b, 300)
    assert a.state == b.state

    assert a.place(CatType.SLEEPY, 2, 4) == PlaceResult.OK
    tick_n(a, 50)
    tick_n(b, 50)
    assert a.state != b.state
