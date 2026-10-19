import curses

import pytest
from helpers import NEVER, quiet_config, tick_to

from cats_vs_mutants.core.config import CatType, Config, MutantType
from cats_vs_mutants.core.entities import PlaceResult, SpawnEvent, Status
from cats_vs_mutants.core.game import Game
from cats_vs_mutants.ui.interactive import handle_key
from cats_vs_mutants.ui.renderer import Renderer, UiState
from cats_vs_mutants.ui.text import cell_text


def press(game: Game, ui: UiState, *keys: int | str) -> list[bool]:
    return [handle_key(ord(k) if isinstance(k, str) else k, game, ui) for k in keys]


# ---- Key handling -----------------------------------------------------------


def test_cursor_starts_in_the_middle_lane_at_column_zero():
    ui = UiState()
    assert (ui.cursor_lane, ui.cursor_col, ui.selected) == (2, 0, CatType.RICH)


def test_arrows_move_the_cursor():
    game, ui = Game(Config(), [NEVER]), UiState()
    press(game, ui, curses.KEY_RIGHT, curses.KEY_RIGHT, curses.KEY_DOWN)
    assert (ui.cursor_lane, ui.cursor_col) == (3, 2)
    press(game, ui, curses.KEY_UP, curses.KEY_LEFT)
    assert (ui.cursor_lane, ui.cursor_col) == (2, 1)


def test_cursor_stays_on_the_board():
    game, ui = Game(Config(), [NEVER]), UiState()
    press(game, ui, *[curses.KEY_UP] * 10, *[curses.KEY_LEFT] * 10)
    assert (ui.cursor_lane, ui.cursor_col) == (0, 0)
    press(game, ui, *[curses.KEY_DOWN] * 10, *[curses.KEY_RIGHT] * 20)
    assert (ui.cursor_lane, ui.cursor_col) == (4, 8)


@pytest.mark.parametrize(
    ("key", "cat_type"),
    [("1", CatType.RICH), ("2", CatType.HISSING), ("3", CatType.SLEEPY), ("4", CatType.LASER)],
)
def test_number_keys_select_a_cat(key, cat_type):
    other = CatType.LASER if cat_type == CatType.RICH else CatType.RICH
    game, ui = Game(Config(), [NEVER]), UiState(selected=other)
    press(game, ui, key)
    assert ui.selected == cat_type


@pytest.mark.parametrize("key", [" ", "\n", "\r", curses.KEY_ENTER])
def test_space_and_enter_place_the_selected_cat_at_the_cursor(key):
    game, ui = Game(Config(), [NEVER]), UiState()
    press(game, ui, "3", curses.KEY_RIGHT, key)
    assert game.cat_at(2, 1).type == CatType.SLEEPY
    assert ui.message == ""


def test_failed_placement_shows_the_reason():
    game, ui = Game(Config(), [NEVER]), UiState()
    press(game, ui, "4", " ")
    assert ui.message == "Not enough treats!"
    press(game, ui, "1", " ", " ")
    assert ui.message == "That cell already has a cat."


def test_x_removes_the_cat_at_the_cursor():
    game, ui = Game(Config(), [NEVER]), UiState()
    press(game, ui, " ", "x")
    assert game.state.cats == []
    assert ui.message == ""
    press(game, ui, "X")
    assert ui.message == "No cat there."


def test_p_toggles_pause():
    game, ui = Game(Config(), [NEVER]), UiState()
    press(game, ui, "p")
    assert ui.paused
    press(game, ui, "P")
    assert not ui.paused


def test_q_quits():
    game, ui = Game(Config(), [NEVER]), UiState()
    assert press(game, ui, "a", "q", "Q") == [True, False, False]


def test_only_quit_works_after_the_game_is_over():
    game, ui = Game(Config(), []), UiState()
    game.tick()
    assert game.status == Status.WON
    assert press(game, ui, " ", "p", curses.KEY_RIGHT) == [True, True, True]
    assert (ui.paused, ui.cursor_col, ui.message) == (False, 0, "")
    assert press(game, ui, "q") == [False]


# ---- Drawing ----------------------------------------------------------------


class FakeScreen:
    """Just enough of a curses window to capture what the renderer draws."""

    def __init__(self, rows: int = 30, cols: int = 80) -> None:
        self.rows, self.cols = rows, cols
        self.erase()

    def erase(self) -> None:
        self.grid = [[" "] * self.cols for _ in range(self.rows)]
        self.attrs: dict[tuple[int, int], int] = {}

    def addstr(self, y: int, x: int, text: str, attr: int = 0) -> None:
        if not 0 <= y < self.rows:
            raise curses.error
        for i, ch in enumerate(text):
            if x + i < self.cols:
                self.grid[y][x + i] = ch
                self.attrs[(y, x + i)] = attr

    def attron(self, attr: int) -> None:
        pass

    def attroff(self, attr: int) -> None:
        pass

    def refresh(self) -> None:
        pass

    def getmaxyx(self) -> tuple[int, int]:
        return self.rows, self.cols

    def line(self, y: int) -> str:
        return "".join(self.grid[y]).rstrip()


def test_draw_shows_header_board_and_help():
    game = Game(quiet_config(), [SpawnEvent(1, 0, MutantType.RUNNER), NEVER])
    assert game.place(CatType.HISSING, 0, 0) == PlaceResult.OK
    tick_to(game, 20)
    screen = FakeScreen()
    Renderer(screen).draw(game, UiState(message="hello"))

    assert screen.line(0) == "TREATS: 900   WAVE 1/1   LIVES: 3   TICK: 20"
    assert screen.line(1) == "+" + "-" * 54 + "+"
    for lane in range(5):
        for row in range(2):
            cells = "".join(cell_text(game, lane, col, row) + " " for col in range(9))
            assert screen.line(2 + lane * 3 + row) == f"|{cells}|".rstrip()
    assert screen.line(4) == "|" + "." * 54 + "|"  # separator under lane 0
    assert screen.line(16) == "+" + "-" * 54 + "+"
    assert screen.line(18) == "Selected: Rich Cat =$.$=   hello"
    assert screen.line(19) == "1 Rich 50  2 Hissing 100  3 Sleepy 50  4 Laser 175"
    assert screen.line(20) == "Arrows move  Space/Enter place  x remove  p pause  q quit"


def test_draw_highlights_the_cursor_cell():
    game = Game(Config(), [NEVER])
    screen = FakeScreen()
    Renderer(screen).draw(game, UiState(cursor_lane=1, cursor_col=3))

    y, x = 2 + 1 * 3, 1 + 3 * 6
    assert screen.attrs[(y, x)] & curses.A_REVERSE
    assert screen.attrs[(y + 1, x)] & curses.A_REVERSE
    assert not screen.attrs[(y, x + 6)] & curses.A_REVERSE


def test_draw_marks_pause_in_the_header():
    game = Game(Config(), [NEVER])
    screen = FakeScreen()
    Renderer(screen).draw(game, UiState(paused=True))
    assert screen.line(0).endswith("   [PAUSED]")


@pytest.mark.parametrize(
    ("waves", "lives", "title"),
    [
        ([], 3, "*** THE CATS WIN! ***"),
        ([SpawnEvent(1, 0, MutantType.RUNNER)], 1, "*** THE MUTANTS GOT HOME ***"),
    ],
)
def test_draw_end_screen(waves, lives, title):
    config = quiet_config()
    config.starting_lives = lives
    game = Game(config, waves)
    tick_to(game, 100)
    assert game.status != Status.PLAYING
    screen = FakeScreen(rows=20)
    Renderer(screen).draw(game, UiState())

    assert screen.line(7) == "  " + title
    assert screen.line(12) == "  press q to quit"


def test_draw_clips_instead_of_crashing_on_a_small_screen():
    game = Game(Config(), [NEVER])
    Renderer(FakeScreen(rows=5, cols=20)).draw(game, UiState())
