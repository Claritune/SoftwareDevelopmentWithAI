"""curses renderer. Only reads game state; never mutates it."""

import curses
from dataclasses import dataclass

from cats_vs_mutants.core.config import CatType
from cats_vs_mutants.core.entities import Status
from cats_vs_mutants.core.game import Game
from cats_vs_mutants.ui.text import (
    CAT_NAMES,
    CAT_SPRITES,
    EMPTY_CAT_CELL,
    EMPTY_MUTANT_CELL,
    cell_text,
    header_text,
)

CELL_WIDTH = 6  # 5 character sprite plus a space
ROWS_PER_LANE = 3  # cat row, mutant row, separator

CAT_COLOR, MUTANT_COLOR, HAIRBALL_COLOR = 1, 2, 3


@dataclass
class UiState:
    cursor_lane: int = 2
    cursor_col: int = 0
    selected: CatType = CatType.RICH
    paused: bool = False
    message: str = ""


def init_colors() -> bool:
    """Sets up the color pairs. Call once after curses has started."""
    if not curses.has_colors():
        return False
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(CAT_COLOR, curses.COLOR_YELLOW, -1)
    curses.init_pair(MUTANT_COLOR, curses.COLOR_GREEN, -1)
    curses.init_pair(HAIRBALL_COLOR, curses.COLOR_WHITE, -1)
    return True


class Renderer:
    def __init__(self, screen: "curses.window", colors: bool = False) -> None:
        self._screen = screen
        self._colors = colors

    def draw(self, game: Game, ui: UiState) -> None:
        self._screen.erase()
        if game.status != Status.PLAYING:
            self._draw_end_screen(game)
            self._screen.refresh()
            return

        header = header_text(game)
        if ui.paused:
            header += "   [PAUSED]"
        self._put(0, 0, header)

        board_top = 2
        self._draw_board(game, ui, board_top)

        cfg = game.config
        bottom = board_top + cfg.lanes * ROWS_PER_LANE + 1
        self._put(
            bottom,
            0,
            f"Selected: {CAT_NAMES[ui.selected]} {CAT_SPRITES[ui.selected]}   {ui.message}",
        )
        self._put(
            bottom + 1,
            0,
            f"1 Rich {cfg.rich.cost}  2 Hissing {cfg.hissing.cost}  "
            f"3 Sleepy {cfg.sleepy.cost}  4 Laser {cfg.laser.cost}",
        )
        self._put(bottom + 2, 0, "Arrows move  Space/Enter place  x remove  p pause  q quit")
        self._screen.refresh()

    def _draw_board(self, game: Game, ui: UiState, top: int) -> None:
        cfg = game.config
        width = cfg.cols * CELL_WIDTH
        height = cfg.lanes * ROWS_PER_LANE - 1
        s = self._screen

        # Border
        for y in (top - 1, top + height):
            self._put(y, 0, "+" + "-" * width + "+")
        for y in range(top, top + height):
            self._put(y, 0, "|")
            self._put(y, width + 1, "|")

        for lane in range(cfg.lanes):
            y = top + lane * ROWS_PER_LANE
            for col in range(cfg.cols):
                x = 1 + col * CELL_WIDTH
                cursor = lane == ui.cursor_lane and col == ui.cursor_col
                for row in range(2):
                    text = cell_text(game, lane, col, row)
                    attr = curses.A_NORMAL
                    if self._colors and text not in (EMPTY_CAT_CELL, EMPTY_MUTANT_CELL):
                        pair = CAT_COLOR
                        # Sprites never start with a space; hairball rows always do.
                        if row == 1:
                            pair = HAIRBALL_COLOR if text[0] == " " else MUTANT_COLOR
                        attr |= curses.color_pair(pair) | curses.A_BOLD
                    if cursor:
                        attr |= curses.A_REVERSE
                    self._put(y + row, x, text + " ", attr)
            if lane + 1 < cfg.lanes:
                s.attron(curses.A_DIM)
                self._put(y + 2, 1, "." * width)
                s.attroff(curses.A_DIM)

    def _draw_end_screen(self, game: Game) -> None:
        won = game.status == Status.WON
        title = "*** THE CATS WIN! ***" if won else "*** THE MUTANTS GOT HOME ***"
        line = (
            "Every mutant was killed. Your tests are strong."
            if won
            else "Too many mutants survived. Time to write more tests."
        )
        rows, _ = self._screen.getmaxyx()
        y = rows // 2 - 3
        self._put(y, 2, title, curses.A_BOLD)
        self._put(y + 2, 2, line)
        self._put(y + 3, 2, header_text(game))
        self._put(y + 5, 2, "press q to quit")

    def _put(self, y: int, x: int, text: str, attr: int = 0) -> None:
        # Like ncurses mvaddstr, drawing past the window edge clips instead of failing.
        try:
            self._screen.addstr(y, x, text, attr)
        except curses.error:
            pass
