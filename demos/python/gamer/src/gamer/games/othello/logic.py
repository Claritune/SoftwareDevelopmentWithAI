from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gamer.games.base import GameStatus, IllegalMove, Seat

BLACK, WHITE, EMPTY = "black", "white", ""
SIZE = 8
Board = tuple[tuple[str, ...], ...]
Move = tuple[int, int]  # (row, col), 0-based, row 0 at the top


@dataclass(frozen=True)
class OthelloState:
    board: Board
    to_move: Seat | None  # None once neither side can move


class Othello:
    id = "othello"
    name = "Othello"
    seats: tuple[Seat, ...] = (BLACK, WHITE)
    static_dir = Path(__file__).parent / "static"

    def initial_state(self) -> OthelloState:
        rows = [[EMPTY] * SIZE for _ in range(SIZE)]
        rows[3][3] = rows[4][4] = WHITE
        rows[3][4] = rows[4][3] = BLACK
        return OthelloState(tuple(map(tuple, rows)), BLACK)

    def status(self, state: OthelloState) -> GameStatus:
        scores = {s: sum(row.count(s) for row in state.board) for s in self.seats}
        return GameStatus(to_move=state.to_move, finished=False, winner=None, scores=scores)

    def to_public(self, state: OthelloState) -> dict[str, Any]:
        return {"board": [list(row) for row in state.board]}

    # Phase 3 replaces these stubs.
    def legal_moves(self, state, seat): return []
    def apply_move(self, state, seat, move): raise IllegalMove("moves not implemented yet")
    def parse_move(self, raw): raise IllegalMove("moves not implemented yet")
    def move_to_public(self, move): return {"row": move[0], "col": move[1]}


OTHELLO = Othello()
