"""Interactive play: key handling and the fixed-rate game loop."""

import curses
import time

from cats_vs_mutants.core.config import CatType, Config
from cats_vs_mutants.core.entities import Status
from cats_vs_mutants.core.game import Game
from cats_vs_mutants.core.waves import default_waves
from cats_vs_mutants.ui.renderer import Renderer, UiState, init_colors
from cats_vs_mutants.ui.text import PLACE_RESULT_MESSAGES

TICK_LENGTH = 0.1  # seconds: 10 ticks per second

SELECT_KEYS = {
    ord("1"): CatType.RICH,
    ord("2"): CatType.HISSING,
    ord("3"): CatType.SLEEPY,
    ord("4"): CatType.LASER,
}
PLACE_KEYS = {ord(" "), ord("\n"), ord("\r"), curses.KEY_ENTER}


def handle_key(key: int, game: Game, ui: UiState) -> bool:
    """Translates one key press into UI state changes or core API calls.

    Returns False when the player wants to quit.
    """
    cfg = game.config
    if key in (ord("q"), ord("Q")):
        return False
    if game.status != Status.PLAYING:
        return True

    if key == curses.KEY_UP and ui.cursor_lane > 0:
        ui.cursor_lane -= 1
    elif key == curses.KEY_DOWN and ui.cursor_lane < cfg.lanes - 1:
        ui.cursor_lane += 1
    elif key == curses.KEY_LEFT and ui.cursor_col > 0:
        ui.cursor_col -= 1
    elif key == curses.KEY_RIGHT and ui.cursor_col < cfg.cols - 1:
        ui.cursor_col += 1
    elif key in SELECT_KEYS:
        ui.selected = SELECT_KEYS[key]
    elif key in (ord("p"), ord("P")):
        ui.paused = not ui.paused
    elif key in PLACE_KEYS:
        result = game.place(ui.selected, ui.cursor_lane, ui.cursor_col)
        ui.message = PLACE_RESULT_MESSAGES[result]
    elif key in (ord("x"), ord("X")):
        ui.message = "" if game.remove(ui.cursor_lane, ui.cursor_col) else "No cat there."
    return True


def _loop(screen: "curses.window") -> None:
    screen.nodelay(True)
    try:
        curses.curs_set(0)
    except curses.error:
        pass  # some terminals cannot hide the cursor
    renderer = Renderer(screen, init_colors())
    game = Game(Config(), default_waves())
    ui = UiState()

    next_tick = time.monotonic() + TICK_LENGTH
    while True:
        keep_going = True
        key = screen.getch()
        while key != -1 and keep_going:
            keep_going = handle_key(key, game, ui)
            key = screen.getch()
        if not keep_going:
            break

        now = time.monotonic()
        if now >= next_tick:
            if not ui.paused:
                game.tick()
            next_tick += TICK_LENGTH
            if next_tick < now:
                next_tick = now + TICK_LENGTH  # don't spiral after a stall
        renderer.draw(game, ui)
        curses.napms(10)


def run_interactive() -> int:
    try:
        curses.wrapper(_loop)
    except KeyboardInterrupt:
        pass  # Ctrl-C quits; curses.wrapper has already restored the terminal
    return 0
