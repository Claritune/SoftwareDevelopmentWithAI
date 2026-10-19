import pytest
from helpers import NEVER, quiet_config

from cats_vs_mutants.core.config import CatType, Config, MutantType
from cats_vs_mutants.core.entities import PlaceResult, SpawnEvent, Status
from cats_vs_mutants.core.game import Game


def test_placement_placing_deducts_cost_and_creates_cat():
    game = Game(Config(), [NEVER])

    assert game.place(CatType.HISSING, 2, 3) == PlaceResult.OK

    assert game.state.treats == 50
    assert len(game.state.cats) == 1
    cat = game.state.cats[0]
    assert cat.type == CatType.HISSING
    assert cat.lane == 2
    assert cat.col == 3
    assert cat.health == 60
    assert cat.cooldown == 15


@pytest.mark.parametrize(
    ("cat_type", "cost", "health"),
    [
        (CatType.RICH, 50, 40),
        (CatType.HISSING, 100, 60),
        (CatType.SLEEPY, 50, 300),
        (CatType.LASER, 175, 60),
    ],
)
def test_placement_each_cat_type_has_its_cost_and_health(cat_type, cost, health):
    game = Game(quiet_config(), [NEVER])
    assert game.place(cat_type, 0, 0) == PlaceResult.OK
    assert game.state.treats == 1000 - cost
    assert game.state.cats[0].health == health


def test_placement_cost_equal_to_treats_is_allowed():
    game = Game(Config(starting_treats=175), [NEVER])

    assert game.place(CatType.LASER, 0, 0) == PlaceResult.OK
    assert game.state.treats == 0


def test_placement_cost_above_treats_is_rejected():
    game = Game(Config(starting_treats=99), [NEVER])

    assert game.place(CatType.HISSING, 0, 0) == PlaceResult.NOT_ENOUGH_TREATS
    assert game.state.treats == 99
    assert game.state.cats == []


def test_placement_default_treats_cannot_afford_laser():
    game = Game(Config(), [NEVER])
    assert game.place(CatType.LASER, 0, 0) == PlaceResult.NOT_ENOUGH_TREATS


def test_placement_occupied_cell_is_rejected_without_charging():
    game = Game(Config(), [NEVER])
    assert game.place(CatType.RICH, 1, 1) == PlaceResult.OK

    assert game.place(CatType.SLEEPY, 1, 1) == PlaceResult.CELL_OCCUPIED
    assert game.state.treats == 100
    assert len(game.state.cats) == 1
    assert game.state.cats[0].type == CatType.RICH


def test_placement_neighbouring_cells_are_independent():
    game = Game(quiet_config(), [NEVER])
    assert game.place(CatType.RICH, 1, 1) == PlaceResult.OK

    assert game.place(CatType.RICH, 1, 2) == PlaceResult.OK
    assert game.place(CatType.RICH, 2, 1) == PlaceResult.OK
    assert len(game.state.cats) == 3


def test_placement_out_of_bounds_is_rejected():
    game = Game(quiet_config(), [NEVER])

    assert game.place(CatType.RICH, -1, 0) == PlaceResult.OUT_OF_BOUNDS
    assert game.place(CatType.RICH, 5, 0) == PlaceResult.OUT_OF_BOUNDS
    assert game.place(CatType.RICH, 0, -1) == PlaceResult.OUT_OF_BOUNDS
    assert game.place(CatType.RICH, 0, 9) == PlaceResult.OUT_OF_BOUNDS
    assert game.state.cats == []
    assert game.state.treats == 1000


def test_placement_board_corners_are_in_bounds():
    game = Game(quiet_config(), [NEVER])

    assert game.place(CatType.RICH, 0, 0) == PlaceResult.OK
    assert game.place(CatType.RICH, 4, 8) == PlaceResult.OK
    assert game.place(CatType.RICH, 0, 8) == PlaceResult.OK
    assert game.place(CatType.RICH, 4, 0) == PlaceResult.OK


def test_placement_bounds_follow_config():
    config = quiet_config()
    config.lanes = 2
    config.cols = 3
    game = Game(config, [SpawnEvent(1_000_000, 0, MutantType.BLOB)])

    assert game.place(CatType.RICH, 1, 2) == PlaceResult.OK
    assert game.place(CatType.RICH, 2, 0) == PlaceResult.OUT_OF_BOUNDS
    assert game.place(CatType.RICH, 0, 3) == PlaceResult.OUT_OF_BOUNDS


def test_placement_bounds_are_checked_before_treats():
    game = Game(Config(starting_treats=0), [NEVER])

    assert game.place(CatType.RICH, 9, 9) == PlaceResult.OUT_OF_BOUNDS


def test_placement_occupancy_is_checked_before_treats():
    game = Game(Config(starting_treats=50), [NEVER])
    assert game.place(CatType.RICH, 0, 0) == PlaceResult.OK

    assert game.place(CatType.RICH, 0, 0) == PlaceResult.CELL_OCCUPIED


def test_placement_cannot_place_after_game_is_over():
    game = Game(Config(), [])
    game.tick()
    assert game.status == Status.WON

    assert game.place(CatType.RICH, 0, 0) == PlaceResult.GAME_OVER
    assert game.state.cats == []


def test_placement_can_place_on_cell_holding_a_mutant():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    game.tick()  # runner now at step 89, cell 8

    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK


def test_remove_removes_cat_without_refund():
    game = Game(Config(), [NEVER])
    assert game.place(CatType.SLEEPY, 3, 4) == PlaceResult.OK

    assert game.remove(3, 4)
    assert game.state.cats == []
    assert game.state.treats == 100


def test_remove_empty_cell_returns_false():
    game = Game(Config(), [NEVER])
    assert not game.remove(0, 0)


def test_remove_only_the_target_cat_is_removed():
    game = Game(quiet_config(), [NEVER])
    assert game.place(CatType.RICH, 0, 0) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 0, 1) == PlaceResult.OK
    assert game.place(CatType.HISSING, 1, 0) == PlaceResult.OK

    assert game.remove(0, 1)

    assert len(game.state.cats) == 2
    assert game.cat_at(0, 0) is not None
    assert game.cat_at(0, 1) is None
    assert game.cat_at(1, 0) is not None


def test_remove_cell_can_be_reused_after_removal():
    game = Game(quiet_config(), [NEVER])
    assert game.place(CatType.RICH, 2, 2) == PlaceResult.OK
    assert game.remove(2, 2)

    assert game.place(CatType.LASER, 2, 2) == PlaceResult.OK
    assert game.cat_at(2, 2).type == CatType.LASER


def test_remove_cannot_remove_after_game_is_over():
    game = Game(Config(), [])
    assert game.place(CatType.RICH, 0, 0) == PlaceResult.OK
    game.tick()
    assert game.status == Status.WON

    assert not game.remove(0, 0)
    assert len(game.state.cats) == 1


def test_cat_at_finds_cat_by_lane_and_column():
    game = Game(quiet_config(), [NEVER])
    assert game.place(CatType.LASER, 3, 5) == PlaceResult.OK

    cat = game.cat_at(3, 5)
    assert cat is not None
    assert cat.type == CatType.LASER
    assert game.cat_at(5, 3) is None
    assert game.cat_at(3, 4) is None


def test_game_keeps_its_own_copy_of_the_config():
    # Python port only: C++ takes the config by value.
    config = quiet_config()
    game = Game(config, [NEVER])
    config.hissing.cost = 999

    assert game.place(CatType.HISSING, 0, 0) == PlaceResult.OK
    assert game.state.treats == 900
