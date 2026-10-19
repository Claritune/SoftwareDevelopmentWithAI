"""Every tunable number in the game. Tests can build custom configs."""

from dataclasses import dataclass, field
from enum import Enum


class CatType(Enum):
    RICH = "rich"
    HISSING = "hissing"
    SLEEPY = "sleepy"
    LASER = "laser"


class MutantType(Enum):
    BLOB = "blob"
    RUNNER = "runner"
    BRUTE = "brute"
    HOPPER = "hopper"
    EQUIVALENT = "equivalent"


@dataclass
class CatStats:
    cost: int
    health: int
    interval: int  # ticks between actions; 0 means the cat never acts


@dataclass
class MutantStats:
    health: int
    move_interval: int  # ticks per step moved


@dataclass
class Config:
    # Board
    lanes: int = 5
    cols: int = 9
    cell_size: int = 10  # steps per cell; mutants spawn at cols * cell_size

    # Economy and lives
    starting_treats: int = 150
    passive_income: int = 25
    passive_income_interval: int = 100
    starting_lives: int = 3

    # Cats
    rich: CatStats = field(default_factory=lambda: CatStats(50, 40, 80))
    hissing: CatStats = field(default_factory=lambda: CatStats(100, 60, 15))
    sleepy: CatStats = field(default_factory=lambda: CatStats(50, 300, 0))
    laser: CatStats = field(default_factory=lambda: CatStats(175, 60, 30))
    rich_production: int = 25
    laser_range: int = 4  # cells to the right of the cat's own cell
    laser_damage: int = 30

    # Hairballs
    hairball_speed: int = 5
    hairball_damage: int = 20

    # Mutants
    blob: MutantStats = field(default_factory=lambda: MutantStats(100, 2))
    runner: MutantStats = field(default_factory=lambda: MutantStats(60, 1))
    brute: MutantStats = field(default_factory=lambda: MutantStats(300, 3))
    hopper: MutantStats = field(default_factory=lambda: MutantStats(80, 2))
    equivalent: MutantStats = field(default_factory=lambda: MutantStats(1, 2))
    bite_damage: int = 10
    bite_interval: int = 10

    # Reserved for any future randomness; the core never uses unseeded randomness.
    seed: int = 42

    def cat(self, cat_type: CatType) -> CatStats:
        return {
            CatType.RICH: self.rich,
            CatType.HISSING: self.hissing,
            CatType.SLEEPY: self.sleepy,
            CatType.LASER: self.laser,
        }[cat_type]

    def mutant(self, mutant_type: MutantType) -> MutantStats:
        return {
            MutantType.BLOB: self.blob,
            MutantType.RUNNER: self.runner,
            MutantType.BRUTE: self.brute,
            MutantType.HOPPER: self.hopper,
            MutantType.EQUIVALENT: self.equivalent,
        }[mutant_type]

    def spawn_position(self) -> int:
        return self.cols * self.cell_size
