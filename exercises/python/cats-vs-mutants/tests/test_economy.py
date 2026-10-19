from helpers import NEVER, quiet_config, tick_n, tick_to

from cats_vs_mutants.core.config import CatType, Config
from cats_vs_mutants.core.entities import PlaceResult, Status
from cats_vs_mutants.core.game import Game


def test_economy_starts_with_configured_treats_and_lives():
    game = Game(Config(), [NEVER])
    assert game.state.treats == 150
    assert game.state.lives == 3
    assert game.state.tick == 0
    assert game.status == Status.PLAYING


def test_economy_passive_income_every_100_ticks():
    game = Game(Config(), [NEVER])

    tick_to(game, 99)
    assert game.state.treats == 150
    tick_to(game, 100)
    assert game.state.treats == 175
    tick_to(game, 199)
    assert game.state.treats == 175
    tick_to(game, 200)
    assert game.state.treats == 200


def test_economy_passive_income_follows_config():
    game = Game(Config(passive_income=7, passive_income_interval=3), [NEVER])

    tick_n(game, 9)
    assert game.state.treats == 150 + 3 * 7


def test_economy_rich_cat_produces_every_80_ticks_from_placement():
    config = quiet_config()
    config.starting_treats = 50
    game = Game(config, [NEVER])
    assert game.place(CatType.RICH, 0, 0) == PlaceResult.OK

    tick_to(game, 79)
    assert game.state.treats == 0
    tick_to(game, 80)
    assert game.state.treats == 25
    tick_to(game, 159)
    assert game.state.treats == 25
    tick_to(game, 160)
    assert game.state.treats == 50


def test_economy_rich_cat_timer_starts_at_placement_tick():
    config = quiet_config()
    config.starting_treats = 50
    game = Game(config, [NEVER])
    tick_to(game, 10)
    assert game.place(CatType.RICH, 0, 0) == PlaceResult.OK

    tick_to(game, 89)
    assert game.state.treats == 0
    tick_to(game, 90)
    assert game.state.treats == 25


def test_economy_rich_cat_cooldown_counts_down_and_resets():
    game = Game(quiet_config(), [NEVER])
    assert game.place(CatType.RICH, 0, 0) == PlaceResult.OK

    tick_n(game, 1)
    assert game.state.cats[0].cooldown == 79
    tick_to(game, 80)
    assert game.state.cats[0].cooldown == 80


def test_economy_each_rich_cat_produces():
    config = quiet_config()
    config.starting_treats = 100
    game = Game(config, [NEVER])
    assert game.place(CatType.RICH, 0, 0) == PlaceResult.OK
    assert game.place(CatType.RICH, 1, 0) == PlaceResult.OK

    tick_to(game, 80)
    assert game.state.treats == 50


def test_economy_rich_production_follows_config():
    config = quiet_config()
    config.starting_treats = 50
    config.rich_production = 3
    config.rich.interval = 4
    game = Game(config, [NEVER])
    assert game.place(CatType.RICH, 0, 0) == PlaceResult.OK

    tick_n(game, 12)
    assert game.state.treats == 9


def test_economy_other_cats_do_not_produce():
    game = Game(quiet_config(), [NEVER])
    assert game.place(CatType.HISSING, 0, 0) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 1, 0) == PlaceResult.OK
    assert game.place(CatType.LASER, 2, 0) == PlaceResult.OK
    treats = game.state.treats

    tick_n(game, 240)
    assert game.state.treats == treats


def test_economy_passive_income_and_rich_cat_stack():
    game = Game(Config(passive_income_interval=80), [NEVER])
    assert game.place(CatType.RICH, 0, 0) == PlaceResult.OK

    tick_to(game, 80)
    assert game.state.treats == 100 + 25 + 25
