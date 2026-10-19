from helpers import NEVER, quiet_config, tick_to

from cats_vs_mutants.core.config import CatType, Config, MutantType
from cats_vs_mutants.core.entities import SpawnEvent
from cats_vs_mutants.core.game import Game
from cats_vs_mutants.core.waves import default_waves


def first_wave_of(waves: list[SpawnEvent], mutant_type: MutantType) -> int:
    for e in waves:
        if e.type == mutant_type:
            return e.wave
    return 0


# ---- Shipped wave data ------------------------------------------------------


def test_default_waves_are_sorted_by_tick():
    waves = default_waves()
    assert waves
    ticks = [e.tick for e in waves]
    assert ticks == sorted(ticks)


def test_default_waves_three_waves_in_order():
    waves = default_waves()
    assert waves[0].wave == 1
    assert waves[-1].wave == 3
    numbers = [e.wave for e in waves]
    assert numbers == sorted(numbers)


def test_default_waves_spawn_in_valid_lanes_after_tick_zero():
    config = Config()
    for e in default_waves():
        assert 0 <= e.lane < config.lanes
        assert e.tick > 0


def test_default_waves_each_wave_lasts_roughly_thirty_seconds():
    waves = default_waves()
    for wave in (1, 2, 3):
        ticks = [e.tick for e in waves if e.wave == wave]
        assert ticks, f"wave {wave} is empty"
        assert ticks[-1] - ticks[0] <= 300, f"wave {wave}"


def test_default_waves_introduce_mutants_in_the_right_wave():
    waves = default_waves()
    assert first_wave_of(waves, MutantType.BLOB) == 1
    assert first_wave_of(waves, MutantType.RUNNER) == 2
    assert first_wave_of(waves, MutantType.BRUTE) == 3
    assert first_wave_of(waves, MutantType.HOPPER) == 3


def test_default_waves_contain_exactly_one_equivalent_mutant():
    waves = default_waves()
    assert sum(1 for e in waves if e.type == MutantType.EQUIVALENT) == 1


def test_default_waves_get_harder():
    waves = default_waves()

    def count(wave: int) -> int:
        return sum(1 for e in waves if e.wave == wave)

    assert count(1) < count(2)
    assert count(2) < count(3)


# ---- Wave progress ----------------------------------------------------------


def test_wave_progress_current_wave_follows_spawns():
    game = Game(
        quiet_config(),
        [
            SpawnEvent(5, 0, MutantType.BRUTE, 1),
            SpawnEvent(10, 1, MutantType.BRUTE, 2),
            SpawnEvent(1_000_000, 2, MutantType.BRUTE, 3),
        ],
    )
    assert game.total_waves() == 3
    assert game.current_wave() == 1
    tick_to(game, 9)
    assert game.current_wave() == 1
    tick_to(game, 10)
    assert game.current_wave() == 2


def test_wave_progress_current_wave_before_any_spawn_is_the_first_events_wave():
    game = Game(quiet_config(), [SpawnEvent(5, 0, MutantType.BRUTE, 2)])
    assert game.current_wave() == 2


def test_wave_progress_no_waves():
    game = Game(quiet_config(), [])
    assert game.current_wave() == 0
    assert game.total_waves() == 0


def test_wave_progress_default_game_has_three_waves():
    game = Game(Config(), default_waves())
    assert game.total_waves() == 3
    assert game.current_wave() == 1


# ---- Config -----------------------------------------------------------------


def test_config_lookup_cat_stats_by_type():
    c = Config()
    assert c.cat(CatType.RICH).cost == 50
    assert c.cat(CatType.HISSING).cost == 100
    assert c.cat(CatType.SLEEPY).cost == 50
    assert c.cat(CatType.LASER).cost == 175
    assert c.cat(CatType.RICH).interval == 80
    assert c.cat(CatType.HISSING).interval == 15
    assert c.cat(CatType.LASER).interval == 30
    assert c.cat(CatType.SLEEPY).health == 300


def test_config_lookup_mutant_stats_by_type():
    c = Config()
    assert c.mutant(MutantType.BLOB).move_interval == 2
    assert c.mutant(MutantType.RUNNER).move_interval == 1
    assert c.mutant(MutantType.BRUTE).move_interval == 3
    assert c.mutant(MutantType.HOPPER).health == 80
    assert c.mutant(MutantType.EQUIVALENT).health == 1


def test_config_lookup_spawn_position_is_board_width_in_steps():
    c = Config()
    assert c.spawn_position() == 90
    c.cols = 4
    c.cell_size = 3
    assert c.spawn_position() == 12


def test_config_lookup_cell_of_uses_integer_division():
    game = Game(Config(), [NEVER])
    assert game.cell_of(0) == 0
    assert game.cell_of(9) == 0
    assert game.cell_of(10) == 1
    assert game.cell_of(89) == 8
    assert game.cell_of(90) == 9


def test_config_lookup_cell_of_truncates_toward_zero_like_cpp():
    # Python port only: -1 // 10 is -1 in Python, but 0 in C++.
    game = Game(Config(), [NEVER])
    assert game.cell_of(-1) == 0
    assert game.cell_of(-9) == 0
    assert game.cell_of(-10) == -1


def test_config_instances_do_not_share_cat_stats():
    # Python port only: guards against shared mutable defaults.
    a = Config()
    b = Config()
    a.hissing.interval = 30
    assert b.hissing.interval == 15
