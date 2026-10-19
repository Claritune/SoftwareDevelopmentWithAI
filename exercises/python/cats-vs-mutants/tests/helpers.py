"""Shared test helpers, ported from the C++ test_helpers.hpp."""

from cats_vs_mutants.core.config import Config, MutantType
from cats_vs_mutants.core.entities import Mutant, SpawnEvent, Status
from cats_vs_mutants.core.game import Game

# A spawn far in the future: keeps the game from being won while a test runs.
NEVER = SpawnEvent(1_000_000, 4, MutantType.BLOB, 1)


def quiet_config() -> Config:
    """Plenty of treats and no passive income, so rules can be tested in isolation."""
    return Config(starting_treats=1000, passive_income_interval=1_000_000)


def tick_n(game: Game, n: int) -> None:
    for _ in range(n):
        game.tick()


def tick_to(game: Game, tick: int) -> None:
    """Ticks until the tick counter reads `tick`."""
    while game.state.tick < tick and game.status == Status.PLAYING:
        game.tick()


def only_mutant(game: Game) -> Mutant:
    assert len(game.state.mutants) == 1
    return game.state.mutants[0]
