# Implementation Plan

## Overview
`uv run gamer` starts one FastAPI process on `http://127.0.0.1:8000` that serves a static ES-module client and a `{"v":1,"type","payload"}` JSON API. Players pick Othello from the directory, create or join a session (from the lobby or a shared link), and play to completion. Both tabs poll every 1 s. All rules live in `gamer.games.*`, and the core is shown to be game-agnostic by tests against a `FakeGame`.

## Conventions (apply to every phase)

- **Work only inside the project directory** (`AGENTS.md`). uv creates `.venv/` locally.
- **Every route handler and exception handler is `async def`.** FastAPI runs plain `def` handlers in a thread pool, which would break the single-event-loop, no-locks concurrency model (Design Decision 3). No `await` may appear between reading and writing session state.
- **The core never names a game.** `app.py`, `sessions.py`, and `protocol.py` must not import `gamer.games.othello` or contain the string `othello`. The core only uses `gamer.games.GAMES` and `gamer.games.base`.
- **`gamer/games/` is pure.** It has no I/O, no asyncio, and no FastAPI or Pydantic imports.
- **The client has no rules.** It only renders `legal_moves` from the server.
- Players are seats `0..n-1` to games. `player_id` exists only in the core and never appears in a `state` payload.
- Error envelope: `{"v":1,"type":"error","payload":{"code":..., "message":...}}`. The full set of codes:

  | HTTP | `code` | Raised by | Phase |
  |---|---|---|---|
  | 400 | `bad_request` | bad envelope, wrong `v`, missing or empty name (Pydantic validation) | 2 |
  | 400 | `invalid_move` | `InvalidMove` from `parse_move` | 4 |
  | 403 | `unknown_player` | `UnknownPlayer` | 4 |
  | 404 | `game_not_found` | `GameNotFound` | 2 |
  | 404 | `session_not_found` | `SessionNotFound` | 2 |
  | 409 | `session_full` | `SessionFull` (full or finished session) | 2 |
  | 409 | `game_not_started` | `GameNotStarted` (move while `waiting`) | 4 |
  | 409 | `illegal_move` | `IllegalMove` (illegal, out of turn, or game over) | 4 |

- Snapshot contract (`Game.snapshot` must return these keys): `board`, `current_player` (seat or `None`), `legal_moves` (list of move payloads for the current player, `[]` when finished), `scores` (list per seat), `status` (`"playing" | "finished"`), `winner` (seat, or `None` for a draw or unfinished game), `seat_labels`, `last_event` (str or `None`).
- `state` payload = the game's snapshot, plus core fields `code`, `game_id`, `version`, `status` (core status overrides the snapshot's), `players: [{seat, name}]`.
- Version: `Session.version` starts at `0`, and `join` and `move` each add 1. The creator's join makes a new session version `1`. After the second player joins it is `2`.
- Standard commands: `uv sync`, `uv run pytest`, `uv run ruff check`, `uv run ruff format --check`.

---

## Phase 1: Skeleton and Game Directory

### Changes

#### 1. Project config
**File**: `pyproject.toml`
**Action**: create

```toml
[project]
name = "gamer"
version = "0.1.0"
description = "Local turn-based multiplayer game server"
requires-python = ">=3.12"
dependencies = ["fastapi>=0.115", "uvicorn>=0.30"]

[project.scripts]
gamer = "gamer.__main__:main"

[dependency-groups]
dev = ["pytest>=8.3", "pytest-asyncio>=0.24", "httpx>=0.27", "ruff>=0.7"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/gamer"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

`pythonpath = ["tests"]` lets tests write `from fakes import FakeGame, env` without a `tests/__init__.py`. Hatchling ships everything under `src/gamer/`, including `static/`.

#### 2. Git ignore
**File**: `.gitignore`
**Action**: create. Contents: `.venv/`, `__pycache__/`, `*.egg-info/`, `.pytest_cache/`, `.ruff_cache/`, `dist/`, `build/`.

#### 3. Package and CLI
**File**: `src/gamer/__init__.py`
**Action**: create. One-line docstring only.

**File**: `src/gamer/__main__.py`
**Action**: create

```python
import argparse

import uvicorn

from gamer.app import create_app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="gamer", description="Turn-based game server")
    parser.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 for LAN play")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    uvicorn.run(create_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
```

#### 4. Protocol
**File**: `src/gamer/protocol.py`
**Action**: create. This is a leaf module with no `gamer` imports.

```python
from typing import Any

PROTOCOL_VERSION = 1


def envelope(type_: str, payload: Any) -> dict:
    return {"v": PROTOCOL_VERSION, "type": type_, "payload": payload}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message

    def to_envelope(self) -> dict:
        return envelope("error", {"code": self.code, "message": self.message})
```

#### 5. Game interface and registry
**File**: `src/gamer/games/base.py`
**Action**: create

```python
from typing import Any, Protocol


class InvalidMove(Exception):
    """The move payload is malformed (HTTP 400)."""


class IllegalMove(Exception):
    """The move is well-formed but not allowed in this state (HTTP 409)."""


class Game(Protocol):
    id: str
    name: str
    min_players: int
    max_players: int

    def initial_state(self) -> Any: ...

    def parse_move(self, payload: Any) -> Any: ...

    def apply_move(self, state: Any, seat: int, move: Any) -> Any: ...

    def snapshot(self, state: Any) -> dict[str, Any]:
        """JSON-safe dict with keys: board, current_player, legal_moves, scores,
        status ("playing" | "finished"), winner, seat_labels, last_event."""
        ...
```

**File**: `src/gamer/games/othello.py`
**Action**: create (metadata only in this phase)

```python
class OthelloGame:
    id = "othello"
    name = "Othello"
    min_players = 2
    max_players = 2


OTHELLO = OthelloGame()
```

**File**: `src/gamer/games/__init__.py`
**Action**: create. To add a game, add a module plus one line here.

```python
from gamer.games.base import Game
from gamer.games.othello import OTHELLO

GAMES: dict[str, Game] = {OTHELLO.id: OTHELLO}
```

#### 6. App factory
**File**: `src/gamer/app.py`
**Action**: create. The `registry` parameter is added in Phase 2. In this phase the signature is `create_app(games=None)`.

```python
from collections.abc import Mapping
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from gamer.games import GAMES
from gamer.games.base import Game
from gamer.protocol import ApiError, envelope

STATIC_DIR = Path(__file__).parent / "static"


def create_app(games: Mapping[str, Game] | None = None) -> FastAPI:
    games = GAMES if games is None else games
    app = FastAPI(title="Gamer")

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(exc.to_envelope(), status_code=exc.status)

    @app.middleware("http")
    async def no_cache_static(request: Request, call_next):
        response = await call_next(request)
        if not request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    @app.get("/api/games")
    async def list_games() -> dict:
        return envelope("games", [
            {"id": g.id, "name": g.name, "min_players": g.min_players,
             "max_players": g.max_players}
            for g in games.values()
        ])

    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app
```

The static mount must stay **last** so `/api/*` routes win. The `no-cache` middleware addresses the design's "static file caching" risk for ES modules.

#### 7. Static client shell
**File**: `src/gamer/static/index.html`
**Action**: create

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gamer</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body>
  <header><a href="#/">Gamer</a></header>
  <main id="view"></main>
  <script type="module" src="/js/app.js"></script>
</body>
</html>
```

**File**: `src/gamer/static/style.css`
**Action**: create. Basic layout: system font, centered `main` with max width 640px, a header bar, list styles for `#games`, and a `.error` class with red text. Board styles are added in Phase 2.

**File**: `src/gamer/static/js/api.js`
**Action**: create

```js
export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

const env = (type, payload) => ({ v: 1, type, payload });

async function request(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new ApiError(res.status, data?.payload?.code ?? "http_error",
                       data?.payload?.message ?? res.statusText);
  }
  return data.payload;
}

export const listGames = () => request("GET", "/api/games");
```

`env` is used starting in Phase 2. Until then, ruff doesn't lint JS, so the unused helper is harmless.

**File**: `src/gamer/static/js/app.js`
**Action**: create. This sets up the hash router, an `el` DOM helper, and the directory view. The lobby and game routes show placeholders until Phase 2.

```js
import * as api from "./api.js";

const view = document.getElementById("view");
let routeToken = 0;

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k.startsWith("on")) node.addEventListener(k.slice(2).toLowerCase(), v);
    else node.setAttribute(k, v);
  }
  node.append(...children);
  return node;
}

function parseRoute() {
  const [gameId, code] = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  return { gameId, code };
}

async function route() {
  const token = ++routeToken;
  const { gameId, code } = parseRoute();
  if (!gameId) return showDirectory(token);
  view.replaceChildren(el("p", {}, code ? `Session ${code}` : `Lobby for ${gameId}`));
}

async function showDirectory(token) {
  view.replaceChildren(el("h1", {}, "Games"), el("p", {}, "Loading…"));
  try {
    const games = await api.listGames();
    if (token !== routeToken) return;
    view.replaceChildren(
      el("h1", {}, "Games"),
      el("ul", { id: "games" }, ...games.map((g) => el("li", {}, el("a", { href: `#/${g.id}` }, g.name)))),
    );
  } catch (e) {
    view.replaceChildren(el("p", { class: "error" }, e.message));
  }
}

window.addEventListener("hashchange", route);
route();
```

`routeToken` makes stale async views drop their result after the user navigates away.

#### 8. Test scaffolding
**File**: `tests/fakes.py`
**Action**: create (metadata only in this phase)

```python
def env(type_: str, payload) -> dict:
    return {"v": 1, "type": type_, "payload": payload}


class FakeGame:
    name = "Fake Game"
    min_players = 2
    max_players = 2

    def __init__(self, id: str = "fake", target: int = 3) -> None:
        self.id = id
        self.target = target
```

**File**: `tests/conftest.py`
**Action**: create

```python
from contextlib import asynccontextmanager

import httpx
import pytest
from fakes import FakeGame

from gamer.app import create_app


@asynccontextmanager
async def _client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def client():
    async with _client(create_app()) as c:
        yield c


@pytest.fixture
async def fake_client():
    async with _client(create_app(games={"fake": FakeGame()})) as c:
        yield c
```

**File**: `tests/test_api.py`
**Action**: create

- `test_list_games_returns_othello(client)`: `GET /api/games` returns 200, and the body equals `{"v":1,"type":"games","payload":[{"id":"othello","name":"Othello","min_players":2,"max_players":2}]}`.
- `test_list_games_uses_injected_games(fake_client)`: the payload ids are `["fake"]`.
- `test_index_is_served(client)`: `GET /` returns 200, `text/html` is in `content-type`, and `Cache-Control` is `no-cache`.

### Verification
#### Automated
- [x] `uv sync` succeeds and creates `.venv/` in the project directory
- [x] `uv run pytest` passes (3 tests)
- [x] `uv run ruff check && uv run ruff format --check` passes
- [x] `rg -n -i othello src/gamer/app.py src/gamer/protocol.py` prints nothing

#### Manual
- [ ] `uv run gamer` logs `Uvicorn running on http://127.0.0.1:8000`
- [ ] Opening `http://127.0.0.1:8000/` shows "Games" with an "Othello" link. Clicking it changes the hash to `#/othello` and shows "Lobby for othello".
- [ ] `uv run gamer --port 8001` serves on port 8001

---

## Phase 2: Create a Session and Join by Link

### Changes

#### 1. Protocol additions
**File**: `src/gamer/protocol.py`
**Action**: modify. Add the generic errors and request models.

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GameNotFound(ApiError):
    def __init__(self, game_id: str) -> None:
        super().__init__(404, "game_not_found", f"Unknown game: {game_id}")


class BadRequest(ApiError):
    def __init__(self, message: str) -> None:
        super().__init__(400, "bad_request", message)


class NamePayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=32)


class NameRequest(BaseModel):
    v: Literal[1]
    type: str
    payload: NamePayload
```

#### 2. Sessions
**File**: `src/gamer/sessions.py`
**Action**: create. It imports only `gamer.protocol` and `gamer.games.base`.

```python
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from gamer.games.base import Game
from gamer.protocol import ApiError

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I
CODE_LENGTH = 6


def new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


class SessionNotFound(ApiError):
    def __init__(self, code: str) -> None:
        super().__init__(404, "session_not_found", f"Session {code} not found")


class SessionFull(ApiError):
    def __init__(self, code: str) -> None:
        super().__init__(409, "session_full", f"Session {code} is full")


@dataclass(frozen=True)
class Seat:
    player_id: str
    name: str


@dataclass
class Session:
    code: str
    game: Game
    state: Any
    seats: list[Seat] = field(default_factory=list)
    version: int = 0

    def _status(self, snapshot: dict[str, Any]) -> str:
        if len(self.seats) < self.game.max_players:
            return "waiting"
        return snapshot["status"]

    @property
    def status(self) -> str:
        return self._status(self.game.snapshot(self.state))

    def join(self, name: str) -> tuple[int, Seat]:
        if len(self.seats) >= self.game.max_players:
            raise SessionFull(self.code)
        seat = Seat(player_id=secrets.token_urlsafe(16), name=name)
        self.seats.append(seat)
        self.version += 1
        return len(self.seats) - 1, seat

    def to_payload(self) -> dict[str, Any]:
        snapshot = self.game.snapshot(self.state)
        return {
            **snapshot,
            "code": self.code,
            "game_id": self.game.id,
            "version": self.version,
            "status": self._status(snapshot),
            "players": [{"seat": i, "name": s.name} for i, s in enumerate(self.seats)],
        }


class SessionRegistry:
    def __init__(self, code_factory: Callable[[], str] = new_code) -> None:
        self._sessions: dict[str, Session] = {}
        self._new_code = code_factory

    def create(self, game: Game, name: str) -> tuple[Session, Seat]:
        code = self._new_code()
        while code in self._sessions:
            code = self._new_code()
        session = Session(code=code, game=game, state=game.initial_state())
        self._sessions[code] = session
        _, seat = session.join(name)
        return session, seat

    def get(self, code: str) -> Session:
        session = self._sessions.get(code.upper())
        if session is None:
            raise SessionNotFound(code)
        return session
```

A finished session is always full, so `SessionFull` also covers "joining a finished session" (Design Decision 10). `code_factory` exists only so tests can force a collision.

#### 3. Routes
**File**: `src/gamer/app.py`
**Action**: modify

- The signature becomes `create_app(games: Mapping[str, Game] | None = None, registry: SessionRegistry | None = None)`, with `registry = SessionRegistry() if registry is None else registry`.
- Add a `RequestValidationError` handler (from `fastapi.exceptions`). It covers malformed JSON, a wrong `v`, and a missing or empty `name`, and maps all of them to `400 bad_request`:

```python
@app.exception_handler(RequestValidationError)
async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
    err = BadRequest(f"Invalid request: {exc.errors()[0]['msg']}" if exc.errors() else "Invalid request")
    return JSONResponse(err.to_envelope(), status_code=err.status)
```

- Add routes (all `async def`) and the helpers below:

```python
def get_game(game_id: str) -> Game:
    game = games.get(game_id)
    if game is None:
        raise GameNotFound(game_id)
    return game

def joined(session: Session, seat_index: int, seat: Seat) -> dict:
    return envelope("joined", {"code": session.code, "player_id": seat.player_id,
                               "seat": seat_index, "state": session.to_payload()})

@app.post("/api/games/{game_id}/sessions")
async def create_session(game_id: str, body: NameRequest) -> dict:
    session, seat = registry.create(get_game(game_id), body.payload.name)
    return joined(session, 0, seat)

@app.post("/api/sessions/{code}/join")
async def join_session(code: str, body: NameRequest) -> dict:
    session = registry.get(code)
    index, seat = session.join(body.payload.name)
    return joined(session, index, seat)

@app.get("/api/sessions/{code}")
async def get_session(code: str) -> dict:
    return envelope("state", registry.get(code).to_payload())
```

#### 4. Othello state, legal moves, and snapshot
**File**: `src/gamer/games/othello.py`
**Action**: modify

```python
from dataclasses import dataclass
from typing import Any

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
```

Add to `OthelloGame`:

```python
    def initial_state(self) -> OthelloState:
        return OthelloState(board=initial_board(), current=BLACK)

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
```

`legal_moves` entries use the same `{row, col}` shape as a move payload, so the renderer can send them back as-is.

#### 5. Fake game: state and snapshot
**File**: `tests/fakes.py`
**Action**: modify. The fake is a counter: seats alternate adding 1, and the game finishes when the count reaches `target`.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class FakeState:
    count: int = 0
    current: int | None = 0

# in FakeGame:
    def initial_state(self) -> FakeState:
        return FakeState()

    def snapshot(self, state: FakeState) -> dict:
        finished = state.current is None
        return {
            "board": {"count": state.count},
            "current_player": state.current,
            "legal_moves": [] if finished else [{"step": 1}],
            "scores": [0, 0],
            "status": "finished" if finished else "playing",
            "winner": None,
            "seat_labels": ["First", "Second"],
            "last_event": None,
        }
```

#### 6. Client: create, link join, game view with polling
**File**: `src/gamer/static/js/api.js`
**Action**: modify. Add:

```js
export const createSession = (gameId, name) =>
  request("POST", `/api/games/${gameId}/sessions`, env("create", { name }));
export const joinSession = (code, name) =>
  request("POST", `/api/sessions/${code}/join`, env("join", { name }));
export const getSession = (code) => request("GET", `/api/sessions/${code}`);
```

**File**: `src/gamer/static/js/app.js`
**Action**: modify

- Module state: `const POLL_MS = 1000;`, `const seats = new Map();` (code → `{playerId, seat}`, memory only, so a reload loses the seat), and `let stopPolling = () => {};`.
- `route()` calls `stopPolling()` first. It sends `#/{game}` to `showLobby(gameId, token)` and `#/{game}/{code}` to `showGame(gameId, code.toUpperCase(), token)`.
- Polling helper. It chains `setTimeout` so requests never overlap, and the callback returns `false` to stop:

```js
function poll(fn) {
  let stopped = false;
  let timer;
  const tick = async () => {
    let keepGoing = true;
    try { keepGoing = await fn(); } catch { /* transient error: retry next tick */ }
    if (!stopped && keepGoing !== false) timer = setTimeout(tick, POLL_MS);
  };
  tick();
  return () => { stopped = true; clearTimeout(timer); };
}
```

- `nameForm(label, onSubmit)` returns a `<form>` with `<input name="name" maxlength="32" required>` and a submit button. On submit it calls `preventDefault`, trims the value, and calls `onSubmit(name)`. Errors are written into a `<p class="error">` inside the form.
- `showLobby(gameId, token)`: shows an `h1` with the game id and `nameForm("Create session", ...)`. The submit handler calls `api.createSession`, then `seats.set(joined.code, {playerId: joined.player_id, seat: joined.seat})`, then `location.hash = \`#/${gameId}/${joined.code}\``.
- `showGame(gameId, code, token)`:

```js
async function showGame(gameId, code, token) {
  if (!seats.has(code)) {
    view.replaceChildren(el("h1", {}, `Join ${code}`), nameForm("Join", async (name) => {
      try {
        const joined = await api.joinSession(code, name);
        seats.set(code, { playerId: joined.player_id, seat: joined.seat });
        if (token === routeToken) showGame(gameId, code, token);
      } catch (e) {
        view.replaceChildren(el("p", { class: "error" },
          e.status === 409 ? "Session full" : e.status === 404 ? "Session not found" : e.message));
      }
    }));
    return;
  }
  const mine = seats.get(code);
  const renderer = await import(`/games/${gameId}.js`);
  if (token !== routeToken) return;
  const status = el("p", { id: "status" });
  const board = el("div", { id: "board" });
  const error = el("p", { class: "error" });
  const link = `${location.origin}/#/${gameId}/${code}`;
  view.replaceChildren(el("h1", {}, `Session ${code}`),
    el("p", {}, "Share: ", el("a", { href: link }, link)), status, board, error);

  let lastVersion = -1;
  const onMove = () => {};               // Phase 4 sends the move
  const show = (state) => {
    if (state.version === lastVersion) return;
    lastVersion = state.version;
    status.textContent = describe(state, mine.seat);
    renderer.render(board, state, { mySeat: mine.seat, onMove });
  };
  stopPolling = poll(async () => {
    const state = await api.getSession(code);
    if (token !== routeToken) return false;
    show(state);
    return state.status !== "finished";
  });
}
```

- `describe(state, mySeat)` returns one status string:
  - `waiting`: `"Waiting for opponent…"`
  - `playing`: `` `${label(current)} to move${current === mySeat ? " (you)" : ""}` ``, then `` ` · ${last_event}` `` if set, then the scores, e.g. `` ` · Black 2 – White 2` ``.
  - `finished`: `"Draw"` if `winner === null`, else `` `${label(winner)} wins` ``, followed by the scores.
  - `label(seat)` = `` `${state.seat_labels[seat]} (${state.players[seat]?.name ?? "?"})` ``.

**File**: `src/gamer/static/games/othello.js`
**Action**: create

```js
export function render(container, state, { mySeat, onMove }) {
  const myTurn = state.status === "playing" && state.current_player === mySeat;
  const legal = new Set(myTurn ? state.legal_moves.map((m) => `${m.row},${m.col}`) : []);
  const grid = document.createElement("div");
  grid.className = "othello-board";
  state.board.forEach((row, r) => row.forEach((cell, c) => {
    const sq = document.createElement("button");
    sq.className = "sq";
    if (cell !== null) {
      const disc = document.createElement("span");
      disc.className = `disc ${cell === 0 ? "black" : "white"}`;
      sq.append(disc);
    }
    if (legal.has(`${r},${c}`)) {
      sq.classList.add("legal");
      sq.addEventListener("click", () => onMove({ row: r, col: c }));
    } else {
      sq.disabled = true;
    }
    grid.append(sq);
  }));
  container.replaceChildren(grid);
}
```

**File**: `src/gamer/static/style.css`
**Action**: modify. Add `.othello-board` (CSS grid `repeat(8, 48px)`, gap 2px, dark green background, padding), `.sq` (48×48px green square, no border, `cursor: default`), `.sq.legal` (cursor pointer, inset highlight ring), `.disc` (80% circle, centered), `.disc.black` and `.disc.white`, and `form` / `input` spacing.

#### 7. Tests
**File**: `tests/test_sessions.py`
**Action**: create. Use `FakeGame()` and `SessionRegistry()` directly.

- `test_new_code_shape`: for 200 codes, `len == 6` and every character is in `CODE_ALPHABET`. Also assert that `CODE_ALPHABET` has none of `0O1I`.
- `test_create_takes_seat_zero`: returns seat `name == "Ann"` and a non-empty `player_id`; `session.version == 1` and `session.status == "waiting"`.
- `test_create_retries_on_code_collision`: `SessionRegistry(code_factory=iter(["AAAAAA", "AAAAAA", "BBBBBB"]).__next__)`. Two creates give codes `AAAAAA` and `BBBBBB`.
- `test_join_fills_seat_and_starts`: `join("Bob")` returns `(1, seat)`, `version == 2`, `status == "playing"`, and the player ids differ.
- `test_join_full_raises`: a third `join` raises `SessionFull`.
- `test_get_unknown_raises` (`SessionNotFound`), and `test_get_is_case_insensitive` (`registry.get(code.lower()) is session`).
- `test_payload_hides_player_ids`: the payload has `players == [{"seat":0,"name":"Ann"},{"seat":1,"name":"Bob"}]`, `game_id == "fake"`, and neither player id appears in `json.dumps(session.to_payload())`.

**File**: `tests/games/test_othello.py`
**Action**: create. Pure unit tests, with no server.

- `test_initial_board`: `(3,3)` and `(4,4)` are WHITE, `(3,4)` and `(4,3)` are BLACK, and the other 60 squares are `None`.
- `test_initial_snapshot`: `current_player == 0`, `scores == [2, 2]`, `status == "playing"`, `winner is None`, `seat_labels == ["Black","White"]`, `last_event is None`, and the set of `(m["row"], m["col"])` is `{(2,3),(3,2),(4,5),(5,4)}`.
- `test_white_legal_moves_at_start`: `set(legal_moves(initial_board(), WHITE)) == {(2,4),(3,5),(4,2),(5,3)}`.
- `test_snapshot_is_json_safe`: `json.dumps(OTHELLO.snapshot(OTHELLO.initial_state()))` doesn't raise.

**File**: `tests/test_api.py`
**Action**: modify. Add tests that use `fake_client` unless noted, with `env` from `fakes`.

- `test_create_session`: `POST /api/games/fake/sessions` with `env("create", {"name": "Ann"})` returns 200 and `type == "joined"`. The payload has a 6-char `code`, `seat == 0`, and a `player_id`, and its `state` has `status == "waiting"`, `version == 1`, and `game_id == "fake"`.
- `test_join_and_poll`: after create, join as Bob returns `seat == 1` and `state.status == "playing"`. Then `GET /api/sessions/{code}` returns `type == "state"`, `version == 2`, and two players, and neither `player_id` appears in `r.text`.
- `test_join_full_session_409`: a third join returns 409 with `payload.code == "session_full"`.
- `test_unknown_session_404` (GET and join both give `session_not_found`) and `test_unknown_game_404` (create on `/api/games/nope/sessions` gives `game_not_found`).
- `test_bad_envelope_400` (parametrized): bodies `{"v": 2, "type": "create", "payload": {"name": "Ann"}}`, `{"v": 1, "type": "create", "payload": {}}`, `{"v": 1, "type": "create", "payload": {"name": "  "}}`, and a non-JSON body (`content=b"nope"`, `headers={"content-type": "application/json"}`). Each returns 400, `type == "error"`, and `payload.code == "bad_request"`.
- `test_create_othello_session(client)`: the real registry gives `state.legal_moves` of length 4 and `state.board` with 8 rows.

### Verification
#### Automated
- [x] `uv run pytest` passes
- [x] `uv run pytest tests/games/test_othello.py tests/test_sessions.py` passes
- [x] `uv run ruff check && uv run ruff format --check` passes
- [x] `rg -n -i othello src/gamer/app.py src/gamer/sessions.py src/gamer/protocol.py` prints nothing
- [x] `rg -n "fastapi|pydantic|asyncio" src/gamer/games` prints nothing

#### Manual
- [ ] `uv run gamer`. In tab A, open `http://127.0.0.1:8000/#/othello`, enter "Ann", and click Create. The URL becomes `#/othello/XXXXXX`, a share link is shown, and the status says "Waiting for opponent…".
- [ ] In tab B, open the share link and enter "Bob". Within about 1 s, both tabs show the starting board. The status is "Black (Ann) to move · Black 2 – White 2". Only tab A highlights 4 squares, and clicking one does nothing yet.
- [ ] In tab C, open the same link and enter a name. It shows "Session full".
- [ ] Opening `#/othello/ZZZZZZ` and entering a name shows "Session not found".

---

## Phase 3: Lobby

### Changes

#### 1. Registry: open sessions
**File**: `src/gamer/sessions.py`
**Action**: modify. Add to `SessionRegistry`:

```python
    def open_sessions(self, game_id: str) -> list[Session]:
        return [s for s in self._sessions.values()
                if s.game.id == game_id and s.status == "waiting"]
```

Insertion order (oldest first) comes from `dict` ordering.

#### 2. Route
**File**: `src/gamer/app.py`
**Action**: modify

```python
@app.get("/api/games/{game_id}/sessions")
async def list_sessions(game_id: str) -> dict:
    get_game(game_id)
    return envelope("sessions", [
        {"code": s.code, "players": [{"seat": i, "name": p.name} for i, p in enumerate(s.seats)]}
        for s in registry.open_sessions(game_id)
    ])
```

#### 3. Client lobby
**File**: `src/gamer/static/js/api.js`
**Action**: modify. Add `export const listSessions = (gameId) => request("GET", \`/api/games/${gameId}/sessions\`);`.

**File**: `src/gamer/static/js/app.js`
**Action**: modify `showLobby`

- Layout: `h1`, a single name `<input id="name" maxlength="32">` shared by Create and Join, a Create button, `<h2>Open sessions</h2>`, `<ul id="sessions">`, and `<p class="error" id="lobby-error">`. This replaces the Phase 2 `nameForm` in the lobby. The link-join view keeps `nameForm`.
- `requireName()` returns the trimmed name, or sets the error text "Enter your name" and returns `null`.
- Create works as in Phase 2.
- Join row: `` `${code} — ${players.map(p => p.name).join(", ")}` `` plus a Join button. Its click handler:

```js
async () => {
  const name = requireName();
  if (!name) return;
  try {
    const joined = await api.joinSession(code, name);
    seats.set(code, { playerId: joined.player_id, seat: joined.seat });
    location.hash = `#/${gameId}/${code}`;
  } catch (e) {
    errorEl.textContent = e.status === 409 ? "Session full" : e.message;
  }
}
```

- `stopPolling = poll(async () => { const list = await api.listSessions(gameId); if (token !== routeToken) return false; renderRows(list); return true; });`. When the list is empty, show `<li>No open sessions</li>`. Re-rendering rows must not touch the name input, so the user can keep typing.

#### 4. Tests
**File**: `tests/test_sessions.py`
**Action**: modify

- `test_open_sessions_filters`: a registry with `FakeGame("fake")` and `FakeGame("other")`. Create s1 and s2 on fake and s3 on other, then join s2 to fill it. `open_sessions("fake")` is `[s1]` and `open_sessions("other")` is `[s3]`.

**File**: `tests/test_api.py`
**Action**: modify

- `test_lobby_lists_waiting_sessions(fake_client)`: create A (Ann) and B (Cat), then join B as Bob. `GET /api/games/fake/sessions` returns `type == "sessions"` and the payload equals `[{"code": A, "players": [{"seat": 0, "name": "Ann"}]}]`.
- `test_lobby_unknown_game_404(fake_client)`: `GET /api/games/nope/sessions` returns 404 `game_not_found`.

### Verification
#### Automated
- [x] `uv run pytest` passes
- [x] `uv run ruff check && uv run ruff format --check` passes

#### Manual
- [ ] `uv run gamer`. Tab A creates as "Ann" from `#/othello`. Tab B, already on `#/othello`, shows "XXXXXX — Ann" within about 1 s.
- [ ] Tab B enters "Bob" and clicks Join. Tab B goes to the game view, and both tabs show the board. In a third tab on `#/othello`, the entry disappears within about 1 s.
- [ ] Race check: tab A creates. Tabs B and C both have the lobby open. B joins, then C clicks the stale Join row before the next refresh. C shows "Session full" and stays in the lobby.
- [ ] Clicking Join or Create with an empty name shows "Enter your name".

---

## Phase 4: Moves to Game Over

### Changes

#### 1. Othello moves
**File**: `src/gamer/games/othello.py`
**Action**: modify. Add `from gamer.games.base import IllegalMove, InvalidMove`, plus:

```python
@dataclass(frozen=True)
class OthelloMove:
    row: int
    col: int

# in OthelloGame:
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
```

`type(v) is not int` rejects `bool` and `float`. An occupied square makes `flips` return `[]`, so it becomes `IllegalMove`.

#### 2. Session moves
**File**: `src/gamer/sessions.py`
**Action**: modify

```python
class UnknownPlayer(ApiError):
    def __init__(self) -> None:
        super().__init__(403, "unknown_player", "Unknown player_id for this session")


class GameNotStarted(ApiError):
    def __init__(self, code: str) -> None:
        super().__init__(409, "game_not_started", f"Session {code} is waiting for players")

# in Session:
    def move(self, player_id: str, payload: Any) -> None:
        seat = next((i for i, s in enumerate(self.seats) if s.player_id == player_id), None)
        if seat is None:
            raise UnknownPlayer()
        if len(self.seats) < self.game.max_players:
            raise GameNotStarted(self.code)
        move = self.game.parse_move(payload)
        self.state = self.game.apply_move(self.state, seat, move)
        self.version += 1
```

Check order: unknown player (403), then not started (409), then malformed (400), then illegal (409). `version` changes only after `apply_move` succeeds.

#### 3. Protocol: move request
**File**: `src/gamer/protocol.py`
**Action**: modify

```python
class MovePayload(BaseModel):
    player_id: str
    move: Any  # game-specific; parsed by Game.parse_move, never coerced here


class MoveRequest(BaseModel):
    v: Literal[1]
    type: str
    payload: MovePayload
```

#### 4. Route and game-error mapping
**File**: `src/gamer/app.py`
**Action**: modify

```python
@app.exception_handler(InvalidMove)
async def handle_invalid_move(request: Request, exc: InvalidMove) -> JSONResponse:
    return JSONResponse(envelope("error", {"code": "invalid_move", "message": str(exc)}),
                        status_code=400)

@app.exception_handler(IllegalMove)
async def handle_illegal_move(request: Request, exc: IllegalMove) -> JSONResponse:
    return JSONResponse(envelope("error", {"code": "illegal_move", "message": str(exc)}),
                        status_code=409)

@app.post("/api/sessions/{code}/moves")
async def make_move(code: str, body: MoveRequest) -> dict:
    session = registry.get(code)
    session.move(body.payload.player_id, body.payload.move)
    return envelope("state", session.to_payload())
```

#### 5. Fake game moves
**File**: `tests/fakes.py`
**Action**: modify. Add `from gamer.games.base import IllegalMove, InvalidMove`, plus, in `FakeGame`:

```python
    def parse_move(self, payload) -> int:
        if payload != {"step": 1}:
            raise InvalidMove("expected {'step': 1}")
        return 1

    def apply_move(self, state: FakeState, seat: int, move: int) -> FakeState:
        if state.current != seat:
            raise IllegalMove("not your turn")
        count = state.count + move
        return FakeState(count, None if count >= self.target else 1 - seat)
```

#### 6. Client moves
**File**: `src/gamer/static/js/api.js`
**Action**: modify. Add:

```js
export const makeMove = (code, playerId, move) =>
  request("POST", `/api/sessions/${code}/moves`, env("move", { player_id: playerId, move }));
```

**File**: `src/gamer/static/js/app.js`
**Action**: modify `showGame`. Replace the no-op `onMove`:

```js
let sending = false;
const onMove = async (move) => {
  if (sending) return;
  sending = true;
  error.textContent = "";
  try {
    show(await api.makeMove(code, mine.playerId, move));
  } catch (e) {
    error.textContent = e.message;
  } finally {
    sending = false;
  }
};
```

When `show` gets `status === "finished"`, it adds a result banner `el("p", {class: "result"}, describe(state, mine.seat))` above the board. Polling already stops when it sees `finished`.

**File**: `src/gamer/static/games/othello.js`
**Action**: no code change. The Phase 2 renderer already wires clicks to `onMove`, and it highlights nothing once the game is finished, because `legal_moves` is `[]` and `myTurn` is false. Listed here because `structure.md` names it for this phase.

**File**: `src/gamer/static/style.css`
**Action**: modify. Add `.result` (bold, larger font, highlighted background).

#### 7. Tests
**File**: `tests/games/test_othello.py`
**Action**: modify. Add a helper `board_from(rows: dict[int, str]) -> Board` that builds a board from `{row_index: "BW."}` strings (`B` = 0, `W` = 1, `.` = `None`, padded to 8 with `None`). All other rows are empty.

- `test_parse_move_valid`: `parse_move({"row": 2, "col": 3}) == OthelloMove(2, 3)`.
- `test_parse_move_invalid` (parametrized): `None`, `[2, 3]`, `{}`, `{"row": 2}`, `{"row": "2", "col": 3}`, `{"row": True, "col": 3}`, `{"row": 2.0, "col": 3}`, `{"row": 8, "col": 0}`, and `{"row": -1, "col": 0}` each raise `InvalidMove`.
- `test_first_move_flips`: from the initial state, black plays `(2,3)`. `(2,3)` and `(3,3)` become BLACK, `current == WHITE`, the snapshot scores are `[4, 1]`, and the original state's board is unchanged.
- `test_multi_direction_flip`: `OthelloState(board_from({1: "..WB", 2: ".W..", 3: ".B.."}), BLACK)`. Black plays `(1,1)`, which flips `(1,2)` (rightward, closed by `(1,3)`) and `(2,1)` (downward, closed by `(3,1)`). Afterwards, `(1,1)`, `(1,2)`, and `(2,1)` are BLACK, and the snapshot has `scores == [5, 0]` and `status == "finished"`, because White has no discs left.
- `test_out_of_turn_raises`: white plays `(2,4)` at the start and gets `IllegalMove`.
- `test_no_flip_raises`: black plays `(0,0)` at the start and gets `IllegalMove`.
- `test_occupied_raises`: black plays `(3,3)` at the start and gets `IllegalMove`.
- `test_auto_pass`: `OthelloState(board_from({0: "BW", 2: "BW"}), current=BLACK)`. Black plays `(0,2)`. Then `current == BLACK` and `last_event == "White passed"`, and the snapshot is `playing` with legal moves `[{"row": 2, "col": 2}]`.
- `test_game_over_winner`: `OthelloState(board_from({0: "BW"}), BLACK)`. Black plays `(0,2)`. Then `current is None`, and the snapshot is `status == "finished"`, `scores == [3, 0]`, `winner == 0`, and `legal_moves == []`.
- `test_game_over_draw`: `OthelloState(board_from({0: "BW", 7: "WWW"}), BLACK)`. Black plays `(0,2)`. The snapshot is `finished`, `scores == [3, 3]`, and `winner is None`.
- `test_move_after_game_over_raises`: on the finished state above, any move raises `IllegalMove`.

- `test_self_play_invariants`: from the initial state, repeatedly play `legal_moves(board, current)[0]` until `current is None` (at most 60 plies). At each ply, with `n = len(flips(board, seat, r, c))`, the mover's disc count goes up by `1 + n` and the opponent's goes down by `n`. At the end, the snapshot is `status == "finished"` and `winner` agrees with `scores`.

**File**: `tests/test_sessions.py`
**Action**: modify

- `test_move_unknown_player`: on a full fake session, `move("nope", {"step": 1})` raises `UnknownPlayer`.
- `test_move_before_start`: on a session with only the creator, the creator's move raises `GameNotStarted`.
- `test_move_bumps_version`: a valid seat-0 move takes `version` from 2 to 3. A rejected move (`IllegalMove`, seat 1 out of turn) leaves `version` and `state` unchanged.
- `test_fake_game_finishes`: alternating moves with `FakeGame(target=3)` set `status == "finished"` after 3 moves.

**File**: `tests/test_api.py`
**Action**: modify. Add a helper `async def start(c, game_id) -> tuple[str, dict[int, str], dict]` that creates as Ann, joins as Bob, and returns `(code, {0: pid_a, 1: pid_b}, state)`. Then:

- `test_two_players_finish_othello(client)`:

```python
code, ids, state = await start(client, "othello")
for _ in range(100):
    if state["status"] == "finished":
        break
    r = await client.post(f"/api/sessions/{code}/moves", json=env("move", {
        "player_id": ids[state["current_player"]], "move": state["legal_moves"][0]}))
    assert r.status_code == 200
    state = r.json()["payload"]
assert state["status"] == "finished"
assert state["winner"] in (0, 1, None)
assert sum(state["scores"]) <= 64
```

- `test_fake_game_finishes_via_api(fake_client)`: the same loop, which ends with `finished` after 3 moves and `version == 5`.
- `test_poll_sees_move(fake_client)`: after one move, `GET /api/sessions/{code}` shows `version == 3` and `current_player == 1`.
- `test_move_errors(fake_client)` (parametrized over cases built on `start`):
  - wrong seat (Bob moves first): 409 `illegal_move`
  - `move: {"step": 2}`: 400 `invalid_move`
  - `player_id: "nope"`: 403 `unknown_player`
  - wrong `v`: 400 `bad_request`
  - unknown code: 404 `session_not_found`
- `test_move_before_join_409(fake_client)`: only Ann has joined, so her move gives 409 `game_not_started`.
- `test_move_after_finish_409(fake_client)`: finish the game, then one more move gives 409 `illegal_move`.
- `test_join_finished_session_409(fake_client)`: after the game finishes, a join gives 409 `session_full`.

### Verification
#### Automated
- [ ] `uv run pytest` passes
- [ ] `uv run pytest tests/games/test_othello.py -q` passes
- [ ] `uv run ruff check && uv run ruff format --check` passes
- [ ] `rg -n -i othello src/gamer/app.py src/gamer/sessions.py src/gamer/protocol.py` prints nothing
- [ ] `rg -n "fastapi|pydantic|asyncio" src/gamer/games` prints nothing
- [ ] `rg -n "^\s*def " src/gamer/app.py` shows no route or handler defined with plain `def`; only `create_app` and the local helpers `get_game` and `joined` may match

#### Manual
- [ ] `uv run gamer`. Tabs A and B start a session via the lobby. A clicks a highlighted square, and the move shows in B within about 1 s. B's legal squares are highlighted and A's are not.
- [ ] Clicking during the opponent's turn does nothing, because no squares are enabled.
- [ ] Play to completion (or until a pass happens). A pass shows "· White passed" (or Black) in the status, and the same player moves again.
- [ ] At game end, both tabs show the result banner ("Black (Ann) wins · Black 40 – White 24" or "Draw"), no squares are highlighted, and the browser network tab shows polling has stopped.
- [ ] `uv run gamer --host 0.0.0.0`. A second device on the LAN can open `http://<host-ip>:8000/` and join.
