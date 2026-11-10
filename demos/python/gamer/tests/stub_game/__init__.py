from dataclasses import dataclass
from pathlib import Path
from gamer.games.base import GameStatus, IllegalMove

@dataclass(frozen=True)
class StubState:
    claims: tuple[str, ...]      # 4 cells, "" or the seat that claimed it
    to_move: str | None

class StubGame:
    """Players take turns claiming cells 0-3. The first to hold 2 cells wins."""
    id, name, seats = "stub", "Stub", ("x", "o")
    static_dir = Path(__file__).parent / "static"

    def initial_state(self): return StubState(("",) * 4, "x")
    def legal_moves(self, state, seat):
        return [i for i, c in enumerate(state.claims) if not c] if state.to_move == seat else []
    def apply_move(self, state, seat, move):
        if move not in self.legal_moves(state, seat): raise IllegalMove("cell not available")
        claims = tuple(seat if i == move else c for i, c in enumerate(state.claims))
        nxt = None if claims.count(seat) >= 2 else ("o" if seat == "x" else "x")
        return StubState(claims, nxt)
    def status(self, state):
        scores = {s: state.claims.count(s) for s in self.seats}
        winner = next((s for s in self.seats if scores[s] >= 2), None)
        return GameStatus(state.to_move, state.to_move is None, winner, scores)
    def to_public(self, state): return {"claims": list(state.claims)}
    def parse_move(self, raw):
        cell = raw.get("cell")
        if type(cell) is not int or not 0 <= cell < 4: raise IllegalMove("cell must be 0-3")
        return cell
    def move_to_public(self, move): return {"cell": move}

STUB = StubGame()
