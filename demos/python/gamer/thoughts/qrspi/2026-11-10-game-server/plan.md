# Implementation Plan

## Overview
A single local FastAPI process (`uv run gamer` → `http://127.0.0.1:8000`)
serves a vanilla-JS client and a JSON HTTP API. Players browse a game
directory, create or join an Othello session from a lobby, and play in two
browser tabs. Clients poll every 1s and the server keeps no per-client state.
Games plug in through a `Game` protocol and an explicit registry, and a
test-only stub game proves this.

**Conventions for every phase**
- All paths are relative to `demos/python/gamer/`. Do not read or copy files
  from outside this folder (`CLAUDE.md`).
- Python 3.12, `uv`, `pytest`. Test command: `uv run pytest -q`.
- Every FastAPI route that touches sessions is `async def` and must not
  `await` between reading and writing session state (design decision 6).
- The server core (`app.py`, `sessions.py`, `protocol.py`, `games/base.py`)
  never imports or names a concrete game. Phase 4 enforces this with a test.
- Seat tokens live in `sessionStorage`, which is per tab (design decision 7).

---

## Phase 1: Skeleton & Game Directory

### Changes

#### 1. Project files
**File**: `pyproject.toml` — **create**
```toml
[project]
name = "gamer"
version = "0.1.0"
description = "Local turn-based game server"
requires-python = ">=3.12"
dependencies = ["fastapi>=0.115", "uvicorn>=0.32"]

[project.scripts]
gamer = "gamer.app:main"

[dependency-groups]
dev = ["pytest>=8", "httpx>=0.27"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/gamer"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["tests"]   # lets tests import `stub_game` (Phase 4)
```
**File**: `.python-version` — **create**, containing `3.12`
**File**: `.gitignore` — **create**, listing `.venv/`, `__pycache__/`, `.pytest_cache/`, `*.egg-info/`

Then run `uv sync`, which creates `uv.lock` and `.venv`.

#### 2. Game protocol
**File**: `src/gamer/__init__.py` — **create** (empty)
**File**: `src/gamer/games/base.py` — **create**
```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

Seat = str


class IllegalMove(Exception):
    """The move is malformed or not allowed by the game's rules."""


@dataclass(frozen=True)
class GameStatus:
    to_move: Seat | None
    finished: bool
    winner: Seat | None
    scores: dict[Seat, int]


class Game[S, M](Protocol):
    id: str
    name: str
    seats: tuple[Seat, ...]
    static_dir: Path  # served at /games/{id}/static, must contain view.js

    def initial_state(self) -> S: ...
    def legal_moves(self, state: S, seat: Seat) -> list[M]: ...
    def apply_move(self, state: S, seat: Seat, move: M) -> S: ...  # raises IllegalMove
    def status(self, state: S) -> GameStatus: ...
    def to_public(self, state: S) -> dict[str, Any]: ...
    def parse_move(self, raw: dict[str, Any]) -> M: ...  # raises IllegalMove
    def move_to_public(self, move: M) -> dict[str, Any]: ...
```

#### 3. Othello (metadata + initial state only)
**File**: `src/gamer/games/othello/logic.py` — **create**
```python
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
```
**File**: `src/gamer/games/othello/__init__.py` — **create**: `from gamer.games.othello.logic import OTHELLO, Othello, OthelloState`
**File**: `src/gamer/games/othello/static/view.js` — **create**. For now it only exports a placeholder `render()` (filled in Phase 2), so the static mount has something to serve.

#### 4. Registry
**File**: `src/gamer/games/__init__.py` — **create**
```python
from gamer.games.base import Game
from gamer.games.othello import OTHELLO

REGISTRY: dict[str, Game] = {OTHELLO.id: OTHELLO}
```

#### 5. API models
**File**: `src/gamer/protocol.py` — **create**. Phase 1 only needs
`GameInfo(BaseModel): id: str; name: str`. Later phases add more models.

#### 6. App factory
**File**: `src/gamer/app.py` — **create**
```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from gamer.games import REGISTRY
from gamer.games.base import Game
from gamer.protocol import GameInfo

STATIC_DIR = Path(__file__).parent / "static"


def create_app(registry: dict[str, Game] = REGISTRY) -> FastAPI:
    app = FastAPI(title="Gamer")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    for game in registry.values():
        app.mount(f"/games/{game.id}/static",
                  StaticFiles(directory=game.static_dir), name=f"{game.id}-static")

    @app.get("/api/games")
    async def list_games() -> list[GameInfo]:
        return [GameInfo(id=g.id, name=g.name) for g in registry.values()]

    @app.get("/", include_in_schema=False)
    async def index_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()


def main() -> None:
    import uvicorn
    uvicorn.run("gamer.app:app", host="127.0.0.1", port=8000)
```

#### 7. Client: directory page
**File**: `src/gamer/static/common.js` — **create**
```js
export async function api(path, { method = "GET", body, token } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers["X-Player-Token"] = token;
  const res = await fetch(path, {
    method, headers, body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const err = new Error(data?.detail ?? res.statusText);
    err.status = res.status;
    throw err;
  }
  return data;
}
```
**File**: `src/gamer/static/index.html` — **create**. Contains an `<h1>Games</h1>`,
a `<ul id="games">`, a `<link>` to `/static/style.css`, and
`<script type="module" src="/static/index.js">`.
**File**: `src/gamer/static/index.js` — **create**. Calls `api("/api/games")`
and renders one `<li><a href="/games/{id}">{name}</a></li>` per game.
**File**: `src/gamer/static/style.css` — **create**. Holds the minimal core
layout: body font, max-width container, `.status`, `.error` (red), and
`button` styles. No game-specific rules go here.

#### 8. Tests
**File**: `tests/conftest.py` — **create**
```python
import pytest
from fastapi.testclient import TestClient
from gamer.app import create_app

@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())   # fresh in-memory state per test
```
**File**: `tests/test_directory.py` — **create**
- `GET /api/games` returns `[{"id": "othello", "name": "Othello"}]`
- `GET /` returns 200 with `text/html`, and `GET /static/common.js` returns 200
- `GET /games/othello/static/view.js` returns 200

**File**: `tests/test_othello.py` — **create** (extended in Phases 3 and 4)
- `initial_state()` has white at (3,3) and (4,4), black at (3,4) and (4,3),
  60 empty squares, and `to_move == "black"`
- `status(initial)` returns scores `{"black": 2, "white": 2}` and `finished is False`
- `to_public` returns an 8×8 list of lists

### Verification
#### Automated
- [x] `uv sync` succeeds
- [x] `uv run pytest -q` passes

#### Manual
- [ ] `uv run gamer`, then open `http://127.0.0.1:8000/`. "Othello" is listed and links to `/games/othello`. That link returns 404 until Phase 2.

---

## Phase 2: Sessions, Lobby & Read-Only Board

### Changes

#### 1. Session model
**File**: `src/gamer/sessions.py` — **create**
```python
import secrets
from dataclasses import dataclass, field
from typing import Any, Literal

from gamer.games.base import Game, Seat

Lifecycle = Literal["waiting", "playing", "finished"]


class SessionError(Exception):
    message = "session error"
    def __str__(self) -> str: return self.args[0] if self.args else self.message

class GameNotFound(SessionError):    message = "unknown game"
class SessionNotFound(SessionError): message = "unknown session"
class SessionFull(SessionError):     message = "session is full"
class BadToken(SessionError):        message = "invalid or missing player token"
class StaleVersion(SessionError):    message = "board changed, refresh and try again"  # Phase 3
class NotYourTurn(SessionError):     message = "not your turn"                          # Phase 3


@dataclass
class Session:
    id: str
    game: Game
    state: Any
    version: int = 1
    seat_tokens: dict[str, Seat] = field(default_factory=dict)  # token -> seat

    @property
    def lifecycle(self) -> Lifecycle:
        if len(self.seat_tokens) < len(self.game.seats):
            return "waiting"
        return "finished" if self.game.status(self.state).finished else "playing"

    def seat_for(self, token: str | None) -> Seat | None:
        return self.seat_tokens.get(token) if token else None

    def taken_seats(self) -> set[Seat]:
        return set(self.seat_tokens.values())

    def claim_seat(self) -> tuple[Seat, str]:
        free = [s for s in self.game.seats if s not in self.taken_seats()]
        if not free:
            raise SessionFull()
        token = secrets.token_urlsafe(16)
        self.seat_tokens[token] = free[0]
        return free[0], token

    def join(self) -> tuple[Seat, str]:
        seat, token = self.claim_seat()
        self.version += 1
        return seat, token


class SessionManager:
    def __init__(self, registry: dict[str, Game]) -> None:
        self._registry = registry
        self._sessions: dict[str, Session] = {}

    def game(self, game_id: str) -> Game:
        try:
            return self._registry[game_id]
        except KeyError:
            raise GameNotFound() from None

    def create(self, game_id: str) -> tuple[Session, Seat, str]:
        game = self.game(game_id)
        session = Session(id=secrets.token_urlsafe(6), game=game, state=game.initial_state())
        seat, token = session.claim_seat()        # creator: first seat, version stays 1
        self._sessions[session.id] = session
        return session, seat, token

    def get(self, session_id: str) -> Session:
        try:
            return self._sessions[session_id]
        except KeyError:
            raise SessionNotFound() from None

    def list_open(self, game_id: str) -> list[Session]:
        self.game(game_id)                         # 404 for unknown game
        return [s for s in self._sessions.values()
                if s.game.id == game_id and s.lifecycle == "waiting"]
```

#### 2. API models
**File**: `src/gamer/protocol.py` — **modify**. Add these models:
```python
class SessionSummary(BaseModel):  session_id: str; game_id: str
class SeatAssignment(BaseModel):  session_id: str; seat: str; token: str
class StatusModel(BaseModel):
    to_move: str | None; finished: bool; winner: str | None; scores: dict[str, int]
class SessionState(BaseModel):
    session_id: str
    game_id: str
    version: int
    lifecycle: Literal["waiting", "playing", "finished"]
    public_state: dict[str, Any]
    status: StatusModel
    legal_moves: list[dict[str, Any]]
    seats: dict[str, bool]          # seat -> taken
    your_seat: str | None
```

#### 3. Routes, error mapping, pages
**File**: `src/gamer/app.py` — **modify**
- Inside `create_app`, add `manager = SessionManager(registry)` and set `app.state.manager = manager`.
- Error mapping. Phase 3 adds `StaleVersion`, `NotYourTurn` → 409 and `IllegalMove` → 400.
  ```python
  ERROR_STATUS: dict[type[Exception], int] = {
      GameNotFound: 404, SessionNotFound: 404, BadToken: 403, SessionFull: 409,
  }

  @app.exception_handler(SessionError)
  async def session_error(_, exc: SessionError) -> JSONResponse:
      status = next(c for t, c in ERROR_STATUS.items() if isinstance(exc, t))
      return JSONResponse({"detail": str(exc)}, status_code=status)
  ```
- State builder at module level, kept in `app.py` so `protocol.py` stays free of session logic:
  ```python
  def build_state(session: Session, seat: Seat | None) -> SessionState:
      game, state = session.game, session.state
      playing = seat is not None and session.lifecycle == "playing"
      legal = [game.move_to_public(m) for m in game.legal_moves(state, seat)] if playing else []
      taken = session.taken_seats()
      return SessionState(
          session_id=session.id, game_id=game.id, version=session.version,
          lifecycle=session.lifecycle, public_state=game.to_public(state),
          status=StatusModel(**asdict(game.status(state))), legal_moves=legal,
          seats={s: s in taken for s in game.seats}, your_seat=seat,
      )
  ```
- Routes. All are `async def`, and the token comes from
  `x_player_token: str | None = Header(default=None)`.

  | Route | Body |
  |---|---|
  | `GET /api/games/{game_id}/sessions` → `list[SessionSummary]` | `manager.list_open(game_id)` |
  | `POST /api/games/{game_id}/sessions` (status 201) → `SeatAssignment` | `manager.create(game_id)` |
  | `POST /api/sessions/{session_id}/join` → `SeatAssignment` | `manager.get(id).join()` |
  | `GET /api/sessions/{session_id}/state` → `SessionState` | Token is optional. If a token is given and `seat_for` returns None, raise `BadToken`. Otherwise `build_state(session, seat)`. |

- Page routes (`include_in_schema=False`):
  - `GET /games/{game_id}` calls `manager.game(game_id)` (404 if unknown) and returns `lobby.html`
  - `GET /games/{game_id}/sessions/{session_id}` calls `manager.game(game_id)` and returns `game.html`. It does not check that the session exists, because the page shows "Session not found" itself.

  The static mounts are added before these routes. `/games/{id}/static/...`
  never matches the page routes, because a path parameter never matches a
  `/`.

#### 4. Client
**File**: `src/gamer/static/common.js` — **modify**. Add:
```js
const tokenKey = (sid) => `gamer.token.${sid}`;
export const getToken = (sid) => sessionStorage.getItem(tokenKey(sid));   // per tab
export const setToken = (sid, token) => sessionStorage.setItem(tokenKey(sid), token);

// Runs fn now, then every `ms` after each run finishes (no overlapping requests).
export function poll(fn, ms) {
  let stopped = false, timer;
  const tick = async () => {
    try { await fn(); } catch (e) { console.error(e); }
    if (!stopped) timer = setTimeout(tick, ms);
  };
  tick();
  return () => { stopped = true; clearTimeout(timer); };
}
```
**File**: `src/gamer/static/lobby.html` — **create**. Contains `<h1 id="title">`,
`<button id="create">Create game</button>`, `<ul id="sessions">`, `<p id="error" class="error">`,
a back link to `/`, and the module script `/static/lobby.js`.
**File**: `src/gamer/static/lobby.js` — **create**
```js
import { api, setToken, poll } from "/static/common.js";
const gameId = location.pathname.split("/")[2];
// title: find the game's name from GET /api/games
// "Create" click: const a = await api(`/api/games/${gameId}/sessions`, {method: "POST"});
//   setToken(a.session_id, a.token); location.href = `/games/${gameId}/sessions/${a.session_id}`;
// poll every 2000 ms: GET /api/games/${gameId}/sessions and render one
//   <li><a href="/games/${gameId}/sessions/${sid}">Join game ${sid}</a></li> per session,
//   or "No open games" when the list is empty
// show errors in #error
```
**File**: `src/gamer/static/game.html` — **create**. Contains `<h1 id="title">`,
`<p id="status" class="status">`, `<div id="board">`, `<p id="error" class="error">`,
a link back to the lobby, and the module script `/static/game.js`.
**File**: `src/gamer/static/game.js` — **create**
```js
import { api, getToken, setToken, poll } from "/static/common.js";
const [, , gameId, , sessionId] = location.pathname.split("/");
const el = (id) => document.getElementById(id);
let token = getToken(sessionId);
let view, lastVersion = null;

async function ensureSeat() {
  if (token) return;
  const s = await api(`/api/sessions/${sessionId}/state`);
  if (s.lifecycle !== "waiting") return;               // full: watch without a seat
  try {
    const a = await api(`/api/sessions/${sessionId}/join`, { method: "POST" });
    token = a.token; setToken(sessionId, token);
  } catch (e) { if (e.status !== 409) throw e; }       // lost the race: full
}

function statusText(s) {
  const scores = Object.entries(s.status.scores).map(([k, v]) => `${k} ${v}`).join(" · ");
  if (s.your_seat === null) return `Session full, watching only · ${scores}`;
  if (s.lifecycle === "waiting") return `You are ${s.your_seat}. Waiting for opponent…`;
  const turn = s.status.to_move === s.your_seat ? "Your turn" : "Opponent's turn";
  return `You are ${s.your_seat} · ${turn} · ${scores}`;
}

function show(s) {
  if (s.version === lastVersion) return;
  lastVersion = s.version;
  view.render(el("board"), s.public_state, s.legal_moves, null);   // Phase 3 passes onMove
  el("status").textContent = statusText(s);
}

async function main() {
  try {
    view = await import(`/games/${gameId}/static/view.js`);
  } catch {
    el("error").textContent = `Could not load the view for "${gameId}".`; return;
  }
  try { await ensureSeat(); } catch (e) { el("error").textContent = e.message; return; }
  poll(async () => {
    try {
      show(await api(`/api/sessions/${sessionId}/state`, { token }));
      el("error").textContent = "";
    } catch (e) {
      el("error").textContent = e.status === 404 ? "Session not found." : e.message;
    }
  }, 1000);
}
main();
```
**File**: `src/gamer/games/othello/static/view.js` — **modify**. Board rendering, read-only for now:
```js
const css = document.createElement("link");
css.rel = "stylesheet"; css.href = new URL("./othello.css", import.meta.url);
document.head.append(css);

export function render(container, publicState, legalMoves, onMove) {
  const legal = new Set(legalMoves.map((m) => `${m.row},${m.col}`));
  container.className = "othello-board";
  container.replaceChildren(...publicState.board.flatMap((row, r) => row.map((cell, c) => {
    const sq = document.createElement("button");
    sq.className = "sq";
    if (cell) { const d = document.createElement("span"); d.className = `disc ${cell}`; sq.append(d); }
    if (onMove && legal.has(`${r},${c}`)) {
      sq.classList.add("legal");
      sq.addEventListener("click", () => onMove({ row: r, col: c }));
    } else sq.disabled = true;
    return sq;
  })));
}
```
**File**: `src/gamer/games/othello/static/othello.css` — **create**.
`.othello-board` is an 8×8 grid (`grid-template-columns: repeat(8, 48px)`) on
a green background. `.sq` has a 1px dark border. `.disc` is a circle in
`.black` or `.white`. `.sq.legal` gets a faint dot or outline and
`cursor: pointer`.

#### 5. Tests
**File**: `tests/conftest.py` — **modify**. Add:
```python
@dataclass
class Match:
    sid: str
    black: str   # token
    white: str   # token

@pytest.fixture
def match(client) -> Match:
    a = client.post("/api/games/othello/sessions").json()
    b = client.post(f"/api/sessions/{a['session_id']}/join").json()
    return Match(a["session_id"], a["token"], b["token"])

def headers(token: str) -> dict[str, str]:
    return {"X-Player-Token": token}
```
Because `pythonpath = ["tests"]` is set, test files use
`from conftest import headers` for the helper.

**File**: `tests/test_sessions.py` — **create** (unit tests on `SessionManager(REGISTRY)`)
- `create("othello")` gives seat `black`, a non-empty token, lifecycle `waiting`, and `version == 1`
- `join()` gives seat `white`, a different token, lifecycle `playing`, and `version == 2`
- a third `join()` raises `SessionFull`
- `seat_for(token)` maps both tokens. `seat_for("nope")` and `seat_for(None)` return `None`
- `list_open("othello")` contains the session while it is waiting and not after the join
- `get("missing")` raises `SessionNotFound`, and `create("chess")` and `list_open("chess")` raise `GameNotFound`

**File**: `tests/test_api_sessions.py` — **create**
- `POST /api/games/othello/sessions` returns 201 with `session_id`, `seat == "black"` and `token`, and the session then shows up in `GET .../sessions`
- after the join, `GET .../sessions` is `[]`, and a third join returns 409
- `GET state` with the black token gives `your_seat == "black"`, `lifecycle == "playing"`, `seats == {"black": True, "white": True}`, an 8×8 `public_state["board"]`, and `version == 2`
- `GET state` with no token gives `your_seat is None` and `legal_moves == []`
- `GET state` with a bad token returns 403. An unknown session returns 404. An unknown game returns 404 for both list and create
- pages: `/games/othello` and `/games/othello/sessions/anything` return 200 HTML. `/games/chess` returns 404

### Verification
#### Automated
- [x] `uv run pytest -q` passes

#### Manual
- [ ] `uv run gamer`. In tab A, `/` → Othello → **Create game**. The page shows "You are black. Waiting for opponent…" and the starting board.
- [ ] In tab B (same browser), open `/games/othello`. The session is listed within about 2s. Click it, and B shows "You are white · Opponent's turn". Within about 1s A shows "Your turn".
- [ ] Refreshing tab A keeps it as black (`sessionStorage`).
- [ ] Opening the session URL in tab C gives "Session full, watching only".

---

## Phase 3: Making Moves

### Changes

#### 1. Othello rules
**File**: `src/gamer/games/othello/logic.py` — **modify**. Replace the stubs:
```python
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

# methods on Othello:
def legal_moves(self, state, seat):
    return _moves(state.board, seat) if state.to_move == seat else []

def apply_move(self, state, seat, move):
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

def parse_move(self, raw):
    row, col = raw.get("row"), raw.get("col")
    if not all(type(v) is int for v in (row, col)) or not (_on_board(row, col)):
        raise IllegalMove("move must be {row, col} with integers 0-7")
    return (row, col)
```
`type(v) is int` rejects `bool` as well as strings, floats and `None`.

#### 2. Session moves
**File**: `src/gamer/sessions.py` — **modify**. Add to `Session`:
```python
def move(self, token: str | None, raw_move: dict[str, Any], version: int) -> None:
    seat = self.seat_for(token)
    if seat is None:
        raise BadToken()
    if version != self.version:
        raise StaleVersion()
    if self.lifecycle != "playing" or self.game.status(self.state).to_move != seat:
        raise NotYourTurn()
    move = self.game.parse_move(raw_move)                     # may raise IllegalMove
    self.state = self.game.apply_move(self.state, seat, move)  # may raise IllegalMove
    self.version += 1
```
The checks run in this order: token → version → turn → legality.

#### 3. API
**File**: `src/gamer/protocol.py` — **modify**. Add `MoveRequest(BaseModel): move: dict[str, Any]; version: int`.
**File**: `src/gamer/app.py` — **modify**
- Add `StaleVersion: 409` and `NotYourTurn: 409` to `ERROR_STATUS`.
- Add an `@app.exception_handler(IllegalMove)` that returns `{"detail": str(exc)}` with status 400.
- Add the route:
  ```python
  @app.post("/api/sessions/{session_id}/moves")
  async def make_move(session_id: str, body: MoveRequest,
                      x_player_token: str | None = Header(default=None)) -> SessionState:
      session = manager.get(session_id)
      session.move(x_player_token, body.move, body.version)
      return build_state(session, session.seat_for(x_player_token))
  ```

#### 4. Client
**File**: `src/gamer/static/game.js` — **modify**
- Keep the latest state in `let current`, and set it in `show()`.
- Add:
  ```js
  async function onMove(move) {
    try {
      show(await api(`/api/sessions/${sessionId}/moves`,
        { method: "POST", token, body: { move, version: current.version } }));
      el("error").textContent = "";
    } catch (e) { el("error").textContent = e.message; }   // next poll re-syncs
  }
  ```
- In `show()`, pass `onMove` instead of `null` when `s.your_seat` is set.

**File**: `src/gamer/games/othello/static/view.js`. No change is needed:
Phase 2 already highlights legal squares and makes them clickable when
`onMove` is given.

#### 5. Tests
**File**: `tests/test_othello.py` — **modify**. Add a helper:
```python
def state_from(rows: list[str], to_move="black") -> OthelloState:
    """rows: 8 strings of 8 chars, 'B' black / 'W' white / '.' empty."""
    m = {"B": BLACK, "W": WHITE, ".": EMPTY}
    return OthelloState(tuple(tuple(m[ch] for ch in row) for row in rows), to_move)
```
Add these tests:
- opening `legal_moves(init, "black")` equals `{(2,3), (3,2), (4,5), (5,4)}` as a set, and `legal_moves(init, "white") == []`
- `apply_move(init, "black", (2,3))` flips (3,3), gives counts black 4 / white 1, and `to_move == "white"`
- **all 8 directions**. On this board, black plays (4,4) and every W becomes B:
  ```
  ........
  ........
  ..B.B.B.
  ...WWW..
  ..BW.WB.
  ...WWW..
  ..B.B.B.
  ........
  ```
- multi-disc flip: row 0 is `"BWW....."` and black plays (0,3), which flips (0,1) and (0,2)
- these raise `IllegalMove`: an occupied square (3,3), a move that flips nothing (0,0) at the opening, `"BW.W...."` with black playing (0,4) (the run of whites is broken by a gap), and the wrong seat moving
- `parse_move` raises `IllegalMove` for `{"row": 8, "col": 0}`, `{"row": -1, "col": 0}`, `{"row": "a", "col": 1}`, `{"row": True, "col": 1}` and `{}`, and returns `(2, 3)` for `{"row": 2, "col": 3}`
- **forced pass**: row 0 is `"BW......"`, rows 1–6 are empty, and row 7 is `"BW......"`, with black to move. After black plays (0,2), white has no move, so `to_move == "black"`

**File**: `tests/test_api_moves.py` — **create** (uses the `match` fixture)
- black posts `{"move": {"row": 2, "col": 3}, "version": 2}` and gets 200, `version == 3`, `public_state.board[2][3] == "black"` and `legal_moves == []`. White's `GET state` then has non-empty `legal_moves` and `status.to_move == "white"`
- white moving first returns 409
- black sending `version: 1` returns 409 and leaves `version` unchanged
- black sending `(0,0)` returns 400, and `{"move": {"x": 1}, ...}` returns 400
- a bad token returns 403, no token returns 403, and an unknown session returns 404
- a move in a waiting session (creator only, no join) returns 409

### Verification
#### Automated
- [x] `uv run pytest -q` passes

#### Manual
- [ ] Using two tabs as in Phase 2, black's four legal squares are highlighted. Clicking one flips the disc, and within about 1s white's tab shows the move with white's legal squares highlighted.
- [ ] Clicking in the tab whose turn it isn't does nothing, because its squares are disabled.
- [ ] Play about 10 moves alternating between the tabs, and the disc counts in the status line stay correct.

---

## Phase 4: Game End & Extensibility Proof

### Changes

#### 1. Othello end of game
**File**: `src/gamer/games/othello/logic.py` — **modify** `status`
```python
def status(self, state):
    scores = {s: sum(row.count(s) for row in state.board) for s in self.seats}
    finished = state.to_move is None
    winner = None
    if finished and scores[BLACK] != scores[WHITE]:
        winner = max(scores, key=scores.get)
    return GameStatus(to_move=state.to_move, finished=finished, winner=winner, scores=scores)
```
`Session.lifecycle` becomes `"finished"` with no further change. Once the
game is finished, `Session.move` raises `NotYourTurn` through the existing
lifecycle check.

#### 2. Client end of game
**File**: `src/gamer/static/game.js` — **modify**
- `statusText` handles the finished state first:
  `if (s.lifecycle === "finished") return s.status.winner ? \`${s.status.winner} wins · ${scores}\` : \`Draw · ${scores}\`;`
- Keep the `stop` returned by `poll(...)` in a variable. At the end of
  `show(s)`, call `stop()` if `s.lifecycle === "finished"`. This covers both
  the poll path and the move-response path.

#### 3. Stub game (test only)
**File**: `tests/stub_game/__init__.py` — **create**
```python
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
```
**File**: `tests/stub_game/static/view.js` — **create**. A minimal
`export function render(container, publicState, legalMoves, onMove)` that
lists the claims as buttons. It only has to be served, not exercised.

#### 4. Tests
**File**: `tests/test_othello.py` — **modify**. Add:
- **board-filled finish**: rows 0–6 are `"BBBBBBBB"` and row 7 is `"BBBBBBW."`. Black plays (7,7). The result has `to_move is None`, `finished`, `winner == "black"` and scores 64/0
- **early finish**: the all-8-directions test from Phase 3 now also asserts `status(...).finished` and `winner == "black"`. Neither side can move, but the board isn't full
- **draw**: `status(state_from([... 2 B and 2 W ...], to_move=None))` gives `finished`, `winner is None` and equal scores
- `status(initial).finished is False`

**File**: `tests/test_full_game.py` — **create**
```python
def test_full_game_via_api(client, match):
    tokens = {"black": match.black, "white": match.white}
    for _ in range(100):
        states = {s: client.get(f"/api/sessions/{match.sid}/state", headers=headers(t)).json()
                  for s, t in tokens.items()}
        if states["black"]["lifecycle"] == "finished":
            break
        seat = states["black"]["status"]["to_move"]
        st = states[seat]
        r = client.post(f"/api/sessions/{match.sid}/moves", headers=headers(tokens[seat]),
                        json={"move": st["legal_moves"][0], "version": st["version"]})
        assert r.status_code == 200
    final = states["black"]
    assert final["lifecycle"] == "finished"
    scores = final["status"]["scores"]
    assert sum(scores.values()) <= 64
    expected = None if scores["black"] == scores["white"] else max(scores, key=scores.get)
    assert final["status"]["winner"] == expected
    late = client.post(f"/api/sessions/{match.sid}/moves", headers=headers(match.black),
                       json={"move": {"row": 0, "col": 0}, "version": final["version"]})
    assert late.status_code == 409
```
Picking the first legal move every turn makes the game deterministic.

**File**: `tests/test_extensibility.py` — **create**
- `TestClient(create_app(registry={STUB.id: STUB}))`:
  - `GET /api/games == [{"id": "stub", "name": "Stub"}]`
  - `GET /games/stub/static/view.js` returns 200, and `GET /games/stub` returns 200
  - create and join, then play x→0, o→1, x→2. The response has `lifecycle == "finished"` and `status.winner == "x"`
  - a move after that returns 409
- **core is game-agnostic**: for each of `src/gamer/app.py`, `sessions.py`,
  `protocol.py` and `games/base.py`, assert that `"othello"` does not appear
  in the lowercase source text (`Path(gamer.__file__).parent / name`)

### Verification
#### Automated
- [x] `uv run pytest -q` passes, covering all test files above

#### Manual
- [ ] Play a full Othello game in two tabs. Both tabs show "black wins · …", "white wins · …" or "Draw · …" when it ends.
- [ ] In the DevTools Network tab, `GET .../state` requests stop after the result shows.
- [ ] The lobby no longer lists the finished session.

---

## Deviations from `structure.md`
- **`GameNotFound`** was added to the session errors, so unknown game ids
  return 404 for the lobby, list and create routes.
- **`tests/conftest.py`** was added. It holds the `client` and `match`
  fixtures and the `headers()` helper.
- **`tests/test_othello.py` is created in Phase 1** to hold the
  initial-state tests, and is then extended in Phases 3 and 4.
- **`src/gamer/games/othello/static/othello.css`** was added. `view.js`
  loads it, which keeps board styling out of the core `style.css`.
- **`.python-version` and `.gitignore`** were added for the project scaffold.
- **`StatusModel`** was added to `protocol.py` to serialize `GameStatus`.
  `build_state()` lives in `app.py`, which keeps `protocol.py` dependent only
  on pydantic.
- **The poll loop uses chained `setTimeout`** instead of `setInterval`. This
  prevents overlapping requests when one is slow.
- **Seat tokens use `sessionStorage`** instead of `localStorage`. This was
  decided during planning, and `design.md`, `answers.md` and the diagrams
  are updated to match.
