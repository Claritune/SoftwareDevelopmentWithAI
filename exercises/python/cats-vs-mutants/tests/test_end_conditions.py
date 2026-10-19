import copy

from helpers import NEVER, quiet_config, tick_n, tick_to

from cats_vs_mutants.core.config import CatType, Config, MutantType
from cats_vs_mutants.core.entities import PlaceResult, SpawnEvent, Status
from cats_vs_mutants.core.game import Game


def test_tick_advances_the_counter():
    game = Game(Config(), [NEVER])
    tick_n(game, 7)
    assert game.state.tick == 7


def test_win_no_waves_means_win_on_first_tick():
    game = Game(Config(), [])
    assert game.status == Status.PLAYING
    game.tick()
    assert game.status == Status.WON
    assert game.state.status == Status.WON


def test_win_not_won_while_spawns_are_pending():
    game = Game(Config(), [SpawnEvent(50, 0, MutantType.RUNNER)])
    tick_to(game, 49)
    assert game.state.mutants == []
    assert game.status == Status.PLAYING


def test_win_not_won_while_mutants_remain():
    game = Game(Config(), [SpawnEvent(1, 0, MutantType.RUNNER)])
    game.tick()
    assert game.state.next_spawn == 1
    assert game.status == Status.PLAYING


def test_win_won_when_last_mutant_dies():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER)])
    assert game.place(CatType.LASER, 0, 4) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 59)
    assert game.status == Status.PLAYING
    tick_to(game, 60)
    assert game.status == Status.WON


def test_win_equivalent_mutant_must_leave_before_you_win():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.EQUIVALENT)])
    tick_to(game, 181)
    assert game.status == Status.PLAYING
    tick_to(game, 182)
    assert game.status == Status.WON
    assert game.state.lives == 3


def test_lose_losing_last_life_loses_the_game():
    config = quiet_config()
    config.starting_lives = 1
    game = Game(config, [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])

    tick_to(game, 90)
    assert game.status == Status.PLAYING
    game.tick()
    assert game.status == Status.LOST
    assert game.state.lives == 0


def test_lose_lives_never_go_below_zero():
    config = quiet_config()
    config.starting_lives = 1
    game = Game(
        config,
        [
            SpawnEvent(1, 0, MutantType.RUNNER),
            SpawnEvent(1, 1, MutantType.RUNNER),
            SpawnEvent(1, 2, MutantType.RUNNER),
            NEVER,
        ],
    )
    tick_to(game, 91)
    assert game.status == Status.LOST
    assert game.state.lives == 0


def test_lose_loss_beats_win_on_the_same_tick():
    # The last mutant reaches home: the board is empty and every wave has spawned.
    config = quiet_config()
    config.starting_lives = 1
    game = Game(config, [SpawnEvent(1, 0, MutantType.RUNNER)])
    tick_to(game, 91)
    assert game.status == Status.LOST


def test_game_over_tick_does_nothing_after_win():
    game = Game(Config(), [])
    assert game.place(CatType.RICH, 0, 0) == PlaceResult.OK
    game.tick()
    assert game.status == Status.WON
    before = copy.deepcopy(game.state)

    tick_n(game, 200)
    assert game.state == before


def test_game_over_tick_does_nothing_after_loss():
    game = Game(
        Config(starting_lives=1),
        [SpawnEvent(1, 0, MutantType.RUNNER), SpawnEvent(150, 0, MutantType.BLOB)],
    )
    tick_to(game, 91)
    assert game.status == Status.LOST
    before = copy.deepcopy(game.state)

    tick_n(game, 200)
    assert game.state == before
    assert game.state.next_spawn == 1
