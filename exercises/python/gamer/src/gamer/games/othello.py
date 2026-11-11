from dataclasses import dataclass
from typing import Any

from gamer.games.base import IllegalMove, InvalidMove

SIZE = 8
BLACK, WHITE = 0, 1
SEAT_LABELS = ("Black", "White")
DIRECTIONS = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]

Board = tuple[tuple[int | None, ...], ...]


@dataclass(frozen=True)
class OthelloState:
    board: Board
    current: int | None  # None means the game is over
    last_event: str | None = None


@dataclass(frozen=True)
class OthelloMove:
    row: int
    col: int


def initial_board() -> Board:
    rows: list[list[int | None]] = [[None] * SIZE for _ in range(SIZE)]
    rows[3][3] = rows[4][4] = WHITE
    rows[3][4] = rows[4][3] = BLACK
    return tuple(tuple(r) for r in rows)


def _on_board(r: int, c: int) -> bool:
    return 0 <= r < SIZE and 0 <= c < SIZE


def flips(board: Board, seat: int, row: int, col: int) -> list[tuple[int, int]]:
    if board[row][col] is not None:
        return []
    result: list[tuple[int, int]] = []
    for dr, dc in DIRECTIONS:
        line, r, c = [], row + dr, col + dc
        while _on_board(r, c) and board[r][c] == 1 - seat:
            line.append((r, c))
            r, c = r + dr, c + dc
        if line and _on_board(r, c) and board[r][c] == seat:
            result.extend(line)
    return result


def legal_moves(board: Board, seat: int) -> list[tuple[int, int]]:
    return [(r, c) for r in range(SIZE) for c in range(SIZE) if flips(board, seat, r, c)]


class OthelloGame:
    id = "othello"
    name = "Othello"
    min_players = 2
    max_players = 2

    def initial_state(self) -> OthelloState:
        return OthelloState(board=initial_board(), current=BLACK)

    def parse_move(self, payload: Any) -> OthelloMove:
        if not isinstance(payload, dict):
            raise InvalidMove("Move must be an object with row and col")
        row, col = payload.get("row"), payload.get("col")
        for v in (row, col):
            if type(v) is not int or not 0 <= v < SIZE:
                raise InvalidMove(f"row and col must be integers 0..{SIZE - 1}")
        return OthelloMove(row, col)

    def apply_move(self, state: OthelloState, seat: int, move: OthelloMove) -> OthelloState:
        if state.current is None:
            raise IllegalMove("The game is over")
        if state.current != seat:
            raise IllegalMove("Not your turn")
        flipped = flips(state.board, seat, move.row, move.col)
        if not flipped:
            raise IllegalMove("That move flips no discs")
        rows = [list(r) for r in state.board]
        for r, c in [(move.row, move.col), *flipped]:
            rows[r][c] = seat
        board = tuple(tuple(r) for r in rows)
        opponent = 1 - seat
        if legal_moves(board, opponent):
            return OthelloState(board, opponent)
        if legal_moves(board, seat):
            return OthelloState(board, seat, f"{SEAT_LABELS[opponent]} passed")
        return OthelloState(board, None)

    def snapshot(self, state: OthelloState) -> dict[str, Any]:
        black = sum(row.count(BLACK) for row in state.board)
        white = sum(row.count(WHITE) for row in state.board)
        finished = state.current is None
        winner = None
        if finished and black != white:
            winner = BLACK if black > white else WHITE
        moves = [] if finished else legal_moves(state.board, state.current)
        return {
            "board": [list(row) for row in state.board],
            "current_player": state.current,
            "legal_moves": [{"row": r, "col": c} for r, c in moves],
            "scores": [black, white],
            "status": "finished" if finished else "playing",
            "winner": winner,
            "seat_labels": list(SEAT_LABELS),
            "last_event": state.last_event,
        }


OTHELLO = OthelloGame()
