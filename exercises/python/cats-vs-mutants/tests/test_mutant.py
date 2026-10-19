import pytest
from helpers import NEVER, only_mutant, quiet_config, tick_to

from cats_vs_mutants.core.config import CatType, MutantType
from cats_vs_mutants.core.entities import PlaceResult, SpawnEvent, Status
from cats_vs_mutants.core.game import Game

# ---- Spawning ---------------------------------------------------------------


def test_spawn_mutant_appears_on_its_tick_at_spawn_position():
    game = Game(quiet_config(), [SpawnEvent(5, 3, MutantType.BRUTE), NEVER])

    tick_to(game, 4)
    assert game.state.mutants == []
    tick_to(game, 5)
    m = only_mutant(game)
    assert m.type == MutantType.BRUTE
    assert m.lane == 3
    assert m.position == 90
    assert m.health == 300
    assert m.bite_cooldown == 10
    assert not m.has_jumped


@pytest.mark.parametrize(
    ("mutant_type", "health"),
    [
        (MutantType.BLOB, 100),
        (MutantType.RUNNER, 60),
        (MutantType.BRUTE, 300),
        (MutantType.HOPPER, 80),
        (MutantType.EQUIVALENT, 1),
    ],
)
def test_spawn_each_type_gets_its_configured_health(mutant_type, health):
    game = Game(quiet_config(), [SpawnEvent(1, 0, mutant_type), NEVER])
    game.tick()
    assert only_mutant(game).health == health


def test_spawn_spawn_position_follows_board_size():
    config = quiet_config()
    config.cols = 4
    config.cell_size = 5
    game = Game(config, [SpawnEvent(1, 0, MutantType.BRUTE), NEVER])
    game.tick()
    assert only_mutant(game).position == 20


def test_spawn_all_events_on_the_same_tick_spawn():
    game = Game(
        quiet_config(),
        [
            SpawnEvent(3, 0, MutantType.BLOB),
            SpawnEvent(3, 1, MutantType.RUNNER),
            SpawnEvent(3, 2, MutantType.BRUTE),
            NEVER,
        ],
    )
    tick_to(game, 3)
    assert len(game.state.mutants) == 3
    assert game.state.next_spawn == 3


def test_spawn_events_are_sorted_by_tick():
    game = Game(
        quiet_config(),
        [SpawnEvent(10, 1, MutantType.RUNNER), SpawnEvent(5, 0, MutantType.BLOB), NEVER],
    )

    tick_to(game, 5)
    assert len(game.state.mutants) == 1
    assert game.state.mutants[0].type == MutantType.BLOB
    tick_to(game, 10)
    assert len(game.state.mutants) == 2
    assert game.state.mutants[1].type == MutantType.RUNNER


def test_spawn_event_at_tick_zero_spawns_on_first_tick():
    game = Game(quiet_config(), [SpawnEvent(0, 0, MutantType.BRUTE), NEVER])
    game.tick()
    assert len(game.state.mutants) == 1


# ---- Movement ---------------------------------------------------------------


def test_movement_blob_moves_one_step_every_two_ticks():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.BLOB), NEVER])

    tick_to(game, 1)
    assert only_mutant(game).position == 90
    tick_to(game, 2)
    assert only_mutant(game).position == 89
    tick_to(game, 3)
    assert only_mutant(game).position == 89
    tick_to(game, 4)
    assert only_mutant(game).position == 88
    tick_to(game, 40)
    assert only_mutant(game).position == 70


def test_movement_runner_moves_every_tick():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])

    tick_to(game, 1)
    assert only_mutant(game).position == 89
    tick_to(game, 30)
    assert only_mutant(game).position == 60


def test_movement_brute_moves_one_step_every_three_ticks():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.BRUTE), NEVER])

    tick_to(game, 2)
    assert only_mutant(game).position == 90
    tick_to(game, 3)
    assert only_mutant(game).position == 89
    tick_to(game, 30)
    assert only_mutant(game).position == 80


@pytest.mark.parametrize("mutant_type", [MutantType.HOPPER, MutantType.EQUIVALENT])
def test_movement_hopper_and_equivalent_move_like_blobs(mutant_type):
    game = Game(quiet_config(), [SpawnEvent(1, 0, mutant_type), NEVER])
    tick_to(game, 40)
    assert only_mutant(game).position == 70


def test_movement_speed_follows_config():
    config = quiet_config()
    config.blob.move_interval = 5
    game = Game(config, [SpawnEvent(1, 0, MutantType.BLOB), NEVER])
    tick_to(game, 50)
    assert only_mutant(game).position == 80


# ---- Blocking ---------------------------------------------------------------


def test_blocking_cat_in_mutant_cell_stops_it():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 1)
    assert only_mutant(game).position == 89
    tick_to(game, 50)
    assert only_mutant(game).position == 89


def test_blocking_mutant_walks_up_to_the_cat_cell():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.SLEEPY, 0, 4) == PlaceResult.OK

    tick_to(game, 100)
    assert only_mutant(game).position == 49


def test_blocking_cat_in_another_lane_does_not_block():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.SLEEPY, 1, 8) == PlaceResult.OK

    tick_to(game, 10)
    assert only_mutant(game).position == 80


def test_blocking_mutant_resumes_when_cat_is_removed():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK
    tick_to(game, 20)
    assert game.remove(0, 8)

    tick_to(game, 21)
    assert only_mutant(game).position == 88


# ---- Bites ------------------------------------------------------------------


def test_bites_blocked_mutant_bites_every_ten_ticks():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 9)
    assert game.cat_at(0, 8).health == 300
    tick_to(game, 10)
    assert game.cat_at(0, 8).health == 290
    tick_to(game, 19)
    assert game.cat_at(0, 8).health == 290
    tick_to(game, 20)
    assert game.cat_at(0, 8).health == 280


def test_bites_bite_damage_and_interval_follow_config():
    config = quiet_config()
    config.bite_damage = 7
    config.bite_interval = 3
    game = Game(config, [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 9)
    assert game.cat_at(0, 8).health == 300 - 3 * 7


def test_bites_every_blocked_mutant_bites():
    game = Game(
        quiet_config(),
        [SpawnEvent(1, 0, MutantType.RUNNER), SpawnEvent(1, 0, MutantType.RUNNER), NEVER],
    )
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 10)
    assert game.cat_at(0, 8).health == 280


def test_bites_cat_at_zero_health_is_removed_and_mutant_moves_on():
    config = quiet_config()
    config.sleepy.health = 20
    game = Game(config, [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 19)
    assert game.cat_at(0, 8) is not None
    assert game.cat_at(0, 8).health == 10
    tick_to(game, 20)
    assert game.cat_at(0, 8) is None
    assert only_mutant(game).position == 89
    tick_to(game, 21)
    assert only_mutant(game).position == 88


def test_bites_bite_timer_resets_when_no_longer_blocked():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK
    tick_to(game, 5)
    assert only_mutant(game).bite_cooldown == 5
    assert game.remove(0, 8)

    tick_to(game, 6)
    assert only_mutant(game).bite_cooldown == 10


def test_bites_unblocked_mutant_never_bites():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.SLEEPY, 1, 8) == PlaceResult.OK

    tick_to(game, 30)
    assert game.cat_at(1, 8).health == 300


def test_bites_mutant_killed_this_tick_does_not_bite():
    config = quiet_config()
    config.hairball_damage = 60  # one hairball kills a Runner
    config.bite_interval = 15  # the bite would land on the same tick as the hairball
    game = Game(config, [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.HISSING, 0, 8) == PlaceResult.OK

    tick_to(game, 15)
    assert game.state.mutants == []
    assert game.cat_at(0, 8).health == 60


# ---- Hopper -----------------------------------------------------------------


def test_hopper_jumps_to_the_cell_left_of_the_first_blocking_cat():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.HOPPER), NEVER])
    assert game.place(CatType.SLEEPY, 0, 5) == PlaceResult.OK

    tick_to(game, 62)
    assert only_mutant(game).position == 59
    assert not only_mutant(game).has_jumped
    tick_to(game, 63)
    assert only_mutant(game).position == 49
    assert only_mutant(game).has_jumped
    tick_to(game, 64)
    assert only_mutant(game).position == 49
    tick_to(game, 65)
    assert only_mutant(game).position == 48
    assert game.cat_at(0, 5).health == 300  # it never stopped to bite


def test_hopper_second_blocking_cat_stops_it():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.HOPPER), NEVER])
    assert game.place(CatType.SLEEPY, 0, 5) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 0, 4) == PlaceResult.OK

    tick_to(game, 100)
    assert only_mutant(game).position == 49
    assert game.cat_at(0, 4).health < 300


def test_hopper_jumping_over_cat_in_column_zero_reaches_home():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.HOPPER), NEVER])
    assert game.place(CatType.SLEEPY, 0, 0) == PlaceResult.OK

    tick_to(game, 162)
    assert only_mutant(game).position == 9
    assert game.state.lives == 3
    tick_to(game, 163)
    assert game.state.mutants == []
    assert game.state.lives == 2


@pytest.mark.parametrize(
    "mutant_type",
    [MutantType.BLOB, MutantType.RUNNER, MutantType.BRUTE, MutantType.EQUIVALENT],
)
def test_hopper_other_mutants_never_jump(mutant_type):
    game = Game(quiet_config(), [SpawnEvent(1, 0, mutant_type), NEVER])
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK
    tick_to(game, 20)
    assert only_mutant(game).position == 89
    assert not only_mutant(game).has_jumped


# ---- Reaching home ----------------------------------------------------------


def test_home_mutant_below_step_zero_costs_a_life():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])

    tick_to(game, 90)
    assert only_mutant(game).position == 0
    assert game.state.lives == 3
    tick_to(game, 91)
    assert game.state.mutants == []
    assert game.state.lives == 2


def test_home_each_mutant_costs_one_life():
    game = Game(
        quiet_config(),
        [SpawnEvent(1, 0, MutantType.RUNNER), SpawnEvent(1, 1, MutantType.RUNNER), NEVER],
    )
    tick_to(game, 91)
    assert game.state.lives == 1
    assert game.status == Status.PLAYING


def test_home_equivalent_mutant_costs_no_life():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.EQUIVALENT), NEVER])

    tick_to(game, 181)
    assert only_mutant(game).position == 0
    tick_to(game, 182)
    assert game.state.mutants == []
    assert game.state.lives == 3
