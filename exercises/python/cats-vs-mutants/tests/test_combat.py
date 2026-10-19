from helpers import NEVER, only_mutant, quiet_config, tick_to

from cats_vs_mutants.core.config import CatType, MutantType
from cats_vs_mutants.core.entities import PlaceResult, SpawnEvent
from cats_vs_mutants.core.game import Game


def hairball_positions(game: Game) -> list[int]:
    return sorted(h.position for h in game.state.hairballs)


# ---- Hissing Cat ------------------------------------------------------------


def test_hissing_spits_every_15_ticks_when_mutant_in_lane():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.BRUTE), NEVER])
    assert game.place(CatType.HISSING, 0, 0) == PlaceResult.OK

    tick_to(game, 14)
    assert game.state.hairballs == []
    tick_to(game, 15)
    assert len(game.state.hairballs) == 1
    h = game.state.hairballs[0]
    assert h.lane == 0
    assert h.position == 15  # spawned at cell start + 10, then moved 5
    assert h.origin_col == 0


def test_hissing_hairball_starts_at_the_cats_right_edge():
    game = Game(quiet_config(), [SpawnEvent(1, 2, MutantType.BRUTE), NEVER])
    assert game.place(CatType.HISSING, 2, 3) == PlaceResult.OK

    tick_to(game, 15)
    assert len(game.state.hairballs) == 1
    assert game.state.hairballs[0].position == 45
    assert game.state.hairballs[0].origin_col == 3


def test_hissing_no_mutant_no_hairball_and_timer_still_resets():
    game = Game(quiet_config(), [SpawnEvent(20, 0, MutantType.BRUTE), NEVER])
    assert game.place(CatType.HISSING, 0, 0) == PlaceResult.OK

    tick_to(game, 15)
    assert game.state.hairballs == []
    assert game.cat_at(0, 0).cooldown == 15
    tick_to(game, 29)
    assert game.state.hairballs == []
    tick_to(game, 30)
    assert len(game.state.hairballs) == 1


def test_hissing_ignores_mutants_in_other_lanes():
    game = Game(quiet_config(), [SpawnEvent(1, 1, MutantType.BRUTE), NEVER])
    assert game.place(CatType.HISSING, 0, 0) == PlaceResult.OK

    tick_to(game, 15)
    assert game.state.hairballs == []


def test_hissing_ignores_mutants_behind_it():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    tick_to(game, 50)  # runner at step 40, cell 4
    assert game.place(CatType.HISSING, 0, 6) == PlaceResult.OK

    tick_to(game, 65)
    assert game.state.hairballs == []


def test_hissing_shoots_mutant_in_its_own_cell():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.HISSING, 0, 8) == PlaceResult.OK

    tick_to(game, 15)
    assert only_mutant(game).health == 40
    assert game.state.hairballs == []


def test_hissing_mutant_spawned_this_tick_can_be_targeted():
    # Spawning (step 3) runs before cats fire (step 4).
    game = Game(quiet_config(), [SpawnEvent(15, 0, MutantType.BRUTE), NEVER])
    assert game.place(CatType.HISSING, 0, 0) == PlaceResult.OK

    tick_to(game, 15)
    assert len(game.state.hairballs) == 1


# ---- Hairballs --------------------------------------------------------------


def test_hairball_moves_five_steps_per_tick_and_hits_for_twenty():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.BRUTE), NEVER])
    assert game.place(CatType.HISSING, 0, 0) == PlaceResult.OK

    tick_to(game, 16)
    assert hairball_positions(game) == [20]
    tick_to(game, 28)  # hairball 80, brute 81
    assert hairball_positions(game) == [80]
    assert only_mutant(game).health == 300
    tick_to(game, 29)  # hairball 85 passes brute at 81
    assert game.state.hairballs == []
    assert only_mutant(game).health == 280


def test_hairball_hits_when_positions_are_equal():
    config = quiet_config()
    config.hairball_speed = 79  # 10 + 79 = 89, exactly where the runner waits
    game = Game(config, [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.HISSING, 0, 0) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 15)
    assert only_mutant(game).health == 40
    assert game.state.hairballs == []


def test_hairball_misses_when_one_step_short():
    config = quiet_config()
    config.hairball_speed = 78  # 10 + 78 = 88, one short of the runner
    game = Game(config, [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.HISSING, 0, 0) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 15)
    assert only_mutant(game).health == 60
    assert hairball_positions(game) == [88]


def test_hairball_damage_follows_config():
    config = quiet_config()
    config.hairball_damage = 7
    game = Game(config, [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.HISSING, 0, 8) == PlaceResult.OK

    tick_to(game, 15)
    assert only_mutant(game).health == 53


def test_hairball_hits_the_mutant_closest_to_the_cat():
    config = quiet_config()
    config.hairball_speed = 79  # reaches step 89 on the tick it is spat
    # The Blob spawns first but stops at 89; the Hopper jumps the Sleepy Cat and walks on.
    game = Game(
        config,
        [SpawnEvent(1, 0, MutantType.BLOB), SpawnEvent(1, 0, MutantType.HOPPER), NEVER],
    )
    assert game.place(CatType.HISSING, 0, 0) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 15)
    assert len(game.state.mutants) == 2
    blob, hopper = game.state.mutants
    assert hopper.type == MutantType.HOPPER
    assert blob.position == 89
    assert hopper.position == 73
    assert blob.health == 100
    assert hopper.health == 60


def test_hairball_hits_only_one_mutant():
    game = Game(
        quiet_config(),
        [SpawnEvent(1, 0, MutantType.RUNNER), SpawnEvent(1, 0, MutantType.RUNNER), NEVER],
    )
    assert game.place(CatType.HISSING, 0, 8) == PlaceResult.OK

    tick_to(game, 15)
    assert len(game.state.mutants) == 2
    assert game.state.mutants[0].health + game.state.mutants[1].health == 100


def test_hairball_never_hits_mutants_left_of_the_cat():
    config = quiet_config()
    config.hairball_speed = 79
    game = Game(
        config,
        [SpawnEvent(1, 0, MutantType.RUNNER), SpawnEvent(51, 0, MutantType.RUNNER), NEVER],
    )
    tick_to(game, 50)  # first runner at step 40, already past column 5
    assert game.place(CatType.HISSING, 0, 5) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 0, 2) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 65)
    assert len(game.state.mutants) == 2
    behind, ahead = game.state.mutants
    assert behind.position == 29
    assert ahead.position == 89
    assert behind.health == 60
    assert ahead.health == 40


def test_hairball_ignores_mutant_already_killed_this_tick():
    config = quiet_config()
    config.laser_damage = 100  # laser kills the runner outright
    config.hissing.interval = 30  # hissing and laser fire on the same tick
    config.hairball_speed = 80  # hairball reaches step 90 immediately
    game = Game(
        config,
        [SpawnEvent(1, 0, MutantType.RUNNER), SpawnEvent(30, 0, MutantType.BLOB), NEVER],
    )
    assert game.place(CatType.HISSING, 0, 0) == PlaceResult.OK
    assert game.place(CatType.LASER, 0, 4) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 30)
    blob = only_mutant(game)
    assert blob.type == MutantType.BLOB
    assert blob.health == 80


def test_hairball_disappears_after_passing_step_90():
    # The Equivalent Mutant keeps the cat spitting, but hairballs pass through it.
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.EQUIVALENT), NEVER])
    assert game.place(CatType.HISSING, 0, 0) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 30)
    assert hairball_positions(game) == [15, 90]
    tick_to(game, 31)
    assert hairball_positions(game) == [20]


def test_hairball_can_hit_mutant_at_spawn_position_after_passing_it():
    config = quiet_config()
    config.hairball_speed = 85  # 10 + 85 = 95, past the edge, but the Blob at 90 is in reach
    game = Game(config, [SpawnEvent(15, 0, MutantType.BLOB), NEVER])
    assert game.place(CatType.HISSING, 0, 0) == PlaceResult.OK

    tick_to(game, 15)
    assert only_mutant(game).health == 80
    assert game.state.hairballs == []


def test_hairball_stays_in_its_lane():
    config = quiet_config()
    config.hairball_speed = 79
    game = Game(
        config,
        [SpawnEvent(1, 0, MutantType.RUNNER), SpawnEvent(1, 1, MutantType.RUNNER), NEVER],
    )
    assert game.place(CatType.HISSING, 0, 0) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 1, 8) == PlaceResult.OK

    tick_to(game, 15)
    assert game.state.mutants[0].health == 40
    assert game.state.mutants[1].health == 60


# ---- Laser Cat --------------------------------------------------------------


def test_laser_deals_30_damage_every_30_ticks():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.LASER, 0, 4) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 29)
    assert only_mutant(game).health == 60
    tick_to(game, 30)
    assert only_mutant(game).health == 30
    tick_to(game, 59)
    assert only_mutant(game).health == 30
    tick_to(game, 60)
    assert game.state.mutants == []  # exactly 0 health counts as dead


def test_laser_reaches_four_cells_to_the_right():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.LASER, 0, 4) == PlaceResult.OK  # covers cells 4..8
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 30)
    assert only_mutant(game).health == 30


def test_laser_does_not_reach_five_cells_to_the_right():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.LASER, 0, 3) == PlaceResult.OK  # covers cells 3..7
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 30)
    assert only_mutant(game).health == 60


def test_laser_range_and_damage_follow_config():
    config = quiet_config()
    config.laser_range = 5
    config.laser_damage = 11
    game = Game(config, [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.LASER, 0, 3) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 30)
    assert only_mutant(game).health == 49


def test_laser_hits_every_mutant_in_range_in_its_lane_only():
    game = Game(
        quiet_config(),
        [
            SpawnEvent(1, 0, MutantType.RUNNER),
            SpawnEvent(1, 0, MutantType.BLOB),
            SpawnEvent(1, 1, MutantType.RUNNER),
            NEVER,
        ],
    )
    assert game.place(CatType.LASER, 0, 4) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 1, 8) == PlaceResult.OK

    tick_to(game, 30)
    assert len(game.state.mutants) == 3
    assert game.state.mutants[0].health == 30
    assert game.state.mutants[1].health == 70
    assert game.state.mutants[2].health == 60


def test_laser_hits_mutant_in_its_own_cell():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.LASER, 0, 8) == PlaceResult.OK

    tick_to(game, 30)
    assert only_mutant(game).health == 30


def test_laser_ignores_mutants_behind_it():
    game = Game(
        quiet_config(),
        [SpawnEvent(1, 0, MutantType.RUNNER), SpawnEvent(50, 0, MutantType.RUNNER), NEVER],
    )
    tick_to(game, 50)  # first runner at step 40, cell 4
    assert game.place(CatType.LASER, 0, 5) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 0, 2) == PlaceResult.OK

    tick_to(game, 80)
    assert len(game.state.mutants) == 2
    assert game.state.mutants[0].position == 29
    assert game.state.mutants[0].health == 60
    assert game.state.mutants[1].health == 30


def test_laser_timer_resets_even_without_target():
    game = Game(quiet_config(), [SpawnEvent(31, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.LASER, 0, 4) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 30)
    assert game.cat_at(0, 4).cooldown == 30
    tick_to(game, 59)
    assert only_mutant(game).health == 60
    tick_to(game, 60)
    assert only_mutant(game).health == 30


def test_laser_creates_no_hairballs():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.BRUTE), NEVER])
    assert game.place(CatType.LASER, 0, 8) == PlaceResult.OK
    tick_to(game, 30)
    assert game.state.hairballs == []


# ---- Sleepy Cat -------------------------------------------------------------


def test_sleepy_never_attacks():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 100)
    assert only_mutant(game).health == 60
    assert game.state.hairballs == []


# ---- Equivalent Mutant ------------------------------------------------------


def test_equivalent_hairballs_pass_through_it():
    config = quiet_config()
    config.hairball_speed = 80  # 10 + 80 = 90: already past the mutant waiting at 89
    game = Game(config, [SpawnEvent(1, 0, MutantType.EQUIVALENT), NEVER])
    assert game.place(CatType.HISSING, 0, 0) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 15)
    assert only_mutant(game).health == 1
    assert hairball_positions(game) == [90]


def test_equivalent_laser_cannot_damage_it():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.EQUIVALENT), NEVER])
    assert game.place(CatType.LASER, 0, 4) == PlaceResult.OK
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 90)
    assert only_mutant(game).health == 1


def test_equivalent_can_be_blocked_and_bites():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.EQUIVALENT), NEVER])
    assert game.place(CatType.SLEEPY, 0, 8) == PlaceResult.OK

    tick_to(game, 10)
    assert game.cat_at(0, 8).health == 300
    tick_to(game, 11)  # entered the cell on tick 2, so the first bite lands on tick 11
    assert game.cat_at(0, 8).health == 290
    assert only_mutant(game).position == 89
