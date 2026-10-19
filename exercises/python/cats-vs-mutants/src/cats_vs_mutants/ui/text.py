"""Names, sprites and text rows. Shared by the curses renderer and headless output."""

from cats_vs_mutants.core.config import CatType, MutantType
from cats_vs_mutants.core.entities import Mutant, PlaceResult, Status
from cats_vs_mutants.core.game import Game

CAT_SPRITES = {
    CatType.RICH: "=$.$=",
    CatType.HISSING: "=^o^=",
    CatType.SLEEPY: "=-.-=",
    CatType.LASER: "=O.O=",
}

CAT_NAMES = {
    CatType.RICH: "Rich Cat",
    CatType.HISSING: "Hissing Cat",
    CatType.SLEEPY: "Sleepy Cat",
    CatType.LASER: "Laser Cat",
}

MUTANT_SPRITES = {
    MutantType.BLOB: "(x_x)",
    MutantType.RUNNER: "{@_@}",
    MutantType.BRUTE: "<O_O>",
    MutantType.HOPPER: "(o_O)",
    MutantType.EQUIVALENT: "( _ )",
}

MUTANT_NAMES = {
    MutantType.BLOB: "Blob",
    MutantType.RUNNER: "Runner",
    MutantType.BRUTE: "Brute",
    MutantType.HOPPER: "Hopper",
    MutantType.EQUIVALENT: "Equivalent Mutant",
}

STATUS_NAMES = {
    Status.PLAYING: "Playing",
    Status.WON: "Won",
    Status.LOST: "Lost",
}

PLACE_RESULT_MESSAGES = {
    PlaceResult.OK: "",
    PlaceResult.CELL_OCCUPIED: "That cell already has a cat.",
    PlaceResult.NOT_ENOUGH_TREATS: "Not enough treats!",
    PlaceResult.OUT_OF_BOUNDS: "Out of bounds.",
    PlaceResult.GAME_OVER: "The game is over.",
}

EMPTY_CAT_CELL = "  .  "
EMPTY_MUTANT_CELL = "     "


def cell_text(game: Game, lane: int, col: int, row: int) -> str:
    """The 5 character content of one cell row.

    Each lane is drawn as two text rows: cats on row 0, mutants and hairballs on row 1.
    """
    if row == 0:
        cat = game.cat_at(lane, col)
        return CAT_SPRITES[cat.type] if cat is not None else EMPTY_CAT_CELL

    # The frontmost mutant in the cell wins; otherwise show a hairball.
    front: Mutant | None = None
    for m in game.state.mutants:
        if (
            m.lane == lane
            and m.position >= 0
            and game.cell_of(m.position) == col
            and (front is None or m.position < front.position)
        ):
            front = m
    if front is not None:
        return MUTANT_SPRITES[front.type]

    text = list(EMPTY_MUTANT_CELL)
    cell_size = game.config.cell_size
    for h in game.state.hairballs:
        if h.lane == lane and game.cell_of(h.position) == col:
            text[(h.position % cell_size) * 5 // cell_size] = "o"
    return "".join(text)


def header_text(game: Game) -> str:
    s = game.state
    return (
        f"TREATS: {s.treats}   WAVE {game.current_wave()}/{game.total_waves()}"
        f"   LIVES: {s.lives}   TICK: {s.tick}"
    )
