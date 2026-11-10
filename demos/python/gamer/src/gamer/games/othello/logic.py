from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gamer.games.base import GameStatus, IllegalMove, Seat

BLACK, WHITE, EMPTY = "black", "white", ""
SIZE = 8
Board = tuple[tuple[str, ...], ...]
Move = tuple[int, int]  # (row, col), 0-based, row 0 at the top


DIRECTIONS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _opponent(seat: Seat) -> Seat:
    return WHITE if seat == BLACK else BLACK


def _on_board(r: int, c: int) -> bool:
    return 0 <= r < SIZE and 0 <= c < SIZE


def _flips(board: Board, seat: Seat, row: int, col: int) -> list[Move]:
    if board[row][col] != EMPTY:
        return []
    flips: list[Move] = []
    for dr, dc in DIRECTIONS:
        line, r, c = [], row + dr, col + dc
        while _on_board(r, c) and board[r][c] == _opponent(seat):
            line.append((r, c)); r += dr; c += dc
        if line and _on_board(r, c) and board[r][c] == seat:
            flips.extend(line)
    return flips


def _moves(board: Board, seat: Seat) -> list[Move]:
    return [(r, c) for r in range(SIZE) for c in range(SIZE) if _flips(board, seat, r, c)]


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
        finished = state.to_move is None
        winner = None
        if finished and scores[BLACK] != scores[WHITE]:
            winner = max(scores, key=scores.get)
        return GameStatus(to_move=state.to_move, finished=finished, winner=winner, scores=scores)

    def to_public(self, state: OthelloState) -> dict[str, Any]:
        return {"board": [list(row) for row in state.board]}

    def legal_moves(self, state: OthelloState, seat: Seat) -> list[Move]:
        return _moves(state.board, seat) if state.to_move == seat else []

    def apply_move(self, state: OthelloState, seat: Seat, move: Move) -> OthelloState:
        if state.to_move != seat:
            raise IllegalMove("not your turn")
        row, col = move
        flips = _flips(state.board, seat, row, col)
        if not flips:
            raise IllegalMove("move must flip at least one disc")
        rows = [list(r) for r in state.board]
        for r, c in [(row, col), *flips]:
            rows[r][c] = seat
        board = tuple(map(tuple, rows))
        if _moves(board, _opponent(seat)):
            to_move = _opponent(seat)
        elif _moves(board, seat):
            to_move = seat                    # opponent must pass
        else:
            to_move = None                    # neither side can move
        return OthelloState(board, to_move)

    def parse_move(self, raw: dict[str, Any]) -> Move:
        row, col = raw.get("row"), raw.get("col")
        if not all(type(v) is int for v in (row, col)) or not (_on_board(row, col)):
            raise IllegalMove("move must be {row, col} with integers 0-7")
        return (row, col)

    def move_to_public(self, move: Move) -> dict[str, Any]:
        return {"row": move[0], "col": move[1]}


OTHELLO = Othello()
