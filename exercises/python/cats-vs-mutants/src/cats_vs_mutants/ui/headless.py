"""Runs a command script without curses and prints the game state."""

import re
import sys
from typing import TextIO

from cats_vs_mutants.core.config import CatType, Config
from cats_vs_mutants.core.entities import PlaceResult
from cats_vs_mutants.core.game import Game
from cats_vs_mutants.core.waves import default_waves
from cats_vs_mutants.ui.text import (
    CAT_SPRITES,
    MUTANT_SPRITES,
    PLACE_RESULT_MESSAGES,
    STATUS_NAMES,
    cell_text,
    header_text,
)

CAT_TYPES = {t.value: t for t in CatType}

INT_MIN, INT_MAX = -(2**31), 2**31 - 1


class _BadArguments(Exception):
    pass


class _LineReader:
    """Reads whitespace-separated values from one line, like C++ `istringstream >>`.

    An int is an optional sign and digits; reading stops at the first other character,
    so "2x" reads 2 and leaves "x". A failed read raises _BadArguments.
    """

    _WORD = re.compile(r"\s*(\S+)")
    _INT = re.compile(r"\s*([+-]?\d+)")

    def __init__(self, line: str) -> None:
        self._line = line
        self._pos = 0

    def at_end(self) -> bool:
        return self._WORD.match(self._line, self._pos) is None

    def _read(self, pattern: re.Pattern[str]) -> str:
        match = pattern.match(self._line, self._pos)
        if match is None:
            raise _BadArguments
        self._pos = match.end()
        return match.group(1)

    def word(self) -> str:
        return self._read(self._WORD)

    def int(self) -> int:
        value = int(self._read(self._INT))
        if not INT_MIN <= value <= INT_MAX:
            raise _BadArguments
        return value


def print_state(game: Game, out: TextIO) -> None:
    """Plain text dump of the whole game state (header, board, entity list)."""
    cfg = game.config
    s = game.state
    out.write(f"{header_text(game)}   STATUS: {STATUS_NAMES[s.status]}\n")

    border = "+" + "-" * (cfg.cols * 6) + "+"
    out.write(border + "\n")
    for lane in range(cfg.lanes):
        for row in range(2):
            cells = "".join(cell_text(game, lane, col, row) + " " for col in range(cfg.cols))
            out.write(f"|{cells}|\n")
    out.write(border + "\n")

    for c in s.cats:
        out.write(f"cat     {CAT_SPRITES[c.type]} lane {c.lane} col {c.col} hp {c.health}\n")
    for m in s.mutants:
        out.write(
            f"mutant  {MUTANT_SPRITES[m.type]} lane {m.lane} pos {m.position} hp {m.health}\n"
        )
    for h in s.hairballs:
        out.write(f"hairball  o   lane {h.lane} pos {h.position}\n")


def run_headless(path: str, out: TextIO | None = None, err: TextIO | None = None) -> int:
    """Runs the command script at `path` and prints the final state. Returns an exit code."""
    out = out if out is not None else sys.stdout
    err = err if err is not None else sys.stderr
    try:
        with open(path, encoding="utf-8", newline="") as file:
            lines = file.read().split("\n")
    except OSError:
        err.write(f"cannot open script: {path}\n")
        return 1

    game = Game(Config(), default_waves())
    for line_no, line in enumerate(lines, start=1):
        reader = _LineReader(line.split("#", 1)[0])
        if reader.at_end():
            continue
        cmd = reader.word()
        if cmd not in ("place", "remove", "tick", "print"):
            err.write(f"{path}:{line_no}: unknown command '{cmd}'\n")
            return 1
        try:
            _run_command(cmd, reader, game, out)
        except _BadArguments:
            err.write(f"{path}:{line_no}: bad {cmd} command\n")
            return 1

    out.write("=== FINAL STATE ===\n")
    print_state(game, out)
    return 0


def _run_command(cmd: str, reader: _LineReader, game: Game, out: TextIO) -> None:
    if cmd == "place":
        name, lane, col = reader.word(), reader.int(), reader.int()
        if name not in CAT_TYPES:
            raise _BadArguments
        result = game.place(CAT_TYPES[name], lane, col)
        if result != PlaceResult.OK:
            out.write(
                f"tick {game.state.tick}: place {name} {lane} {col} failed: "
                f"{PLACE_RESULT_MESSAGES[result]}\n"
            )
    elif cmd == "remove":
        lane, col = reader.int(), reader.int()
        game.remove(lane, col)
    elif cmd == "tick":
        for _ in range(reader.int()):
            game.tick()
    else:  # print
        print_state(game, out)
        out.write("\n")
