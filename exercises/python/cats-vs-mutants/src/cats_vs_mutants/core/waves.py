"""The three shipped waves, as plain spawn data sorted by tick."""

from cats_vs_mutants.core.config import MutantType as M
from cats_vs_mutants.core.entities import SpawnEvent


# At 10 ticks per second each wave lasts roughly 30 seconds (300 ticks).
def default_waves() -> list[SpawnEvent]:
    return [
        # Wave 1: a few slow Blobs to learn the ropes.
        SpawnEvent(150, 2, M.BLOB, 1),
        SpawnEvent(200, 0, M.BLOB, 1),
        SpawnEvent(240, 4, M.BLOB, 1),
        SpawnEvent(270, 1, M.BLOB, 1),
        SpawnEvent(300, 3, M.BLOB, 1),
        SpawnEvent(320, 2, M.BLOB, 1),
        # Wave 2: Runners join in.
        SpawnEvent(460, 1, M.BLOB, 2),
        SpawnEvent(490, 3, M.RUNNER, 2),
        SpawnEvent(520, 0, M.BLOB, 2),
        SpawnEvent(550, 4, M.RUNNER, 2),
        SpawnEvent(570, 2, M.BLOB, 2),
        SpawnEvent(600, 2, M.RUNNER, 2),
        SpawnEvent(630, 0, M.RUNNER, 2),
        SpawnEvent(650, 3, M.BLOB, 2),
        SpawnEvent(670, 1, M.RUNNER, 2),
        SpawnEvent(690, 4, M.BLOB, 2),
        # Wave 3: Brutes, Hoppers, and one mutant no test can kill.
        SpawnEvent(790, 2, M.BRUTE, 3),
        SpawnEvent(810, 0, M.HOPPER, 3),
        SpawnEvent(835, 4, M.BLOB, 3),
        SpawnEvent(850, 3, M.RUNNER, 3),
        SpawnEvent(870, 1, M.EQUIVALENT, 3),
        SpawnEvent(890, 4, M.HOPPER, 3),
        SpawnEvent(910, 1, M.BLOB, 3),
        SpawnEvent(930, 3, M.BRUTE, 3),
        SpawnEvent(950, 0, M.RUNNER, 3),
        SpawnEvent(970, 2, M.HOPPER, 3),
        SpawnEvent(990, 4, M.RUNNER, 3),
        SpawnEvent(1010, 1, M.BRUTE, 3),
        SpawnEvent(1030, 0, M.BLOB, 3),
        SpawnEvent(1050, 3, M.HOPPER, 3),
    ]
