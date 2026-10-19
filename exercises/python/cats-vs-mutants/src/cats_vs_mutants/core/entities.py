"""Plain value types for the game state. All compare by value."""

from dataclasses import dataclass, field
from enum import Enum

from cats_vs_mutants.core.config import CatType, MutantType


class Status(Enum):
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


class PlaceResult(Enum):
    OK = "ok"
    CELL_OCCUPIED = "cell_occupied"
    NOT_ENOUGH_TREATS = "not_enough_treats"
    OUT_OF_BOUNDS = "out_of_bounds"
    GAME_OVER = "game_over"


@dataclass
class Cat:
    type: CatType
    lane: int
    col: int
    health: int
    cooldown: int  # ticks until the next action (Rich, Hissing, Laser)


@dataclass
class Mutant:
    type: MutantType
    lane: int
    position: int  # steps from home; cell is position / cell_size
    health: int
    move_cooldown: int  # ticks until the next step
    bite_cooldown: int  # ticks until the next bite while blocked
    has_jumped: bool = False  # Hopper only: true once it has used its jump


@dataclass
class Hairball:
    lane: int
    position: int
    origin_col: int  # cell of the cat that spat it; mutants left of it are never hit


@dataclass(frozen=True)
class SpawnEvent:
    tick: int
    lane: int
    type: MutantType
    wave: int = 1


@dataclass
class GameState:
    tick: int = 0
    treats: int = 0
    lives: int = 0
    status: Status = Status.PLAYING
    cats: list[Cat] = field(default_factory=list)
    mutants: list[Mutant] = field(default_factory=list)
    hairballs: list[Hairball] = field(default_factory=list)
    next_spawn: int = 0  # index of the next unspawned wave event
