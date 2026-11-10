# Structure Outline

## Approach
A single FastAPI process serves static vanilla-JS pages and a JSON HTTP API.
Clients poll for updates and the server keeps no per-client state. Games plug
in through a `Game` protocol and an explicit registry. We build the work in
four vertical slices: directory → sessions & board → moves → game end &
extensibility. Every slice touches the logic, API and browser layers and
ends with something runnable.

Paths are relative to `demos/python/gamer/`. Run with `uv run gamer`, and
test with `uv run pytest`.

---

## Phase 1: Skeleton & Game Directory
Project scaffold, the `Game` protocol, the Othello game with only its
metadata and initial state, the registry, `GET /api/games`, and the directory
page that lists games and links to each lobby.

**Files**: `pyproject.toml`, `src/gamer/__init__.py`, `src/gamer/app.py`,
`src/gamer/protocol.py`, `src/gamer/games/__init__.py`,
`src/gamer/games/base.py`, `src/gamer/games/othello/__init__.py`,
`src/gamer/games/othello/logic.py`, `src/gamer/static/index.html`,
`src/gamer/static/index.js`, `src/gamer/static/common.js`,
`src/gamer/static/style.css`, `tests/test_directory.py`

**Key changes**:
- `Seat = str`, `class IllegalMove(Exception)`
- `GameStatus(frozen): to_move: Seat | None, finished: bool, winner: Seat | None, scores: dict[Seat, int]`
- `class Game(Protocol[S, M])` has:
  - attributes: `id: str`, `name: str`, `seats: tuple[Seat, ...]`, `static_dir: Path`
  - methods: `initial_state() -> S`, `legal_moves(state, seat) -> list[M]`,
    `apply_move(state, seat, move) -> S`, `status(state) -> GameStatus`,
    `to_public(state) -> dict`
  - **new vs design**: `parse_move(raw: dict) -> M` (raises
    `IllegalMove`) and `move_to_public(move: M) -> dict`. These keep JSON
    conversion of moves inside the game.
- `OthelloState(frozen): board: tuple[tuple[str, ...], ...], to_move: Seat | None`
  where each cell is `"black" | "white" | ""` and `Move = tuple[int, int]`
  (row, col)
- `OTHELLO: Game`. This phase implements `initial_state`, `to_public` and
  `status` (scores only).
- `REGISTRY: dict[str, Game] = {OTHELLO.id: OTHELLO}`
- `create_app(registry: dict[str, Game] = REGISTRY) -> FastAPI`, plus
  module-level `app = create_app()` and a `main()` console script that
  starts Uvicorn on `127.0.0.1:8000`
- `GameInfo{id, name}` and route `GET /api/games -> list[GameInfo]`
- Mounts: `/static` serves the core assets, and `/games/{id}/static` serves
  `game.static_dir`. `/` serves `index.html`.
- `common.js` exports `api(path, {method, body, token}) -> Promise<json>`

**Verify**: `uv run pytest` passes (`/api/games` lists Othello, and
`initial_state` has 4 center discs with Black to move). Manual: `uv run
gamer`, open `/`, and Othello is listed.

---

## Phase 2: Sessions, Lobby & Read-Only Board
Create, join and list sessions, plus the polled state endpoint. The lobby
page lists waiting sessions and creates new ones. The game page claims a
seat, polls, and renders the Othello board with no clicking yet.

**Files**: `src/gamer/sessions.py`, `src/gamer/app.py`,
`src/gamer/protocol.py`, `src/gamer/static/lobby.html`,
`src/gamer/static/lobby.js`, `src/gamer/static/game.html`,
`src/gamer/static/game.js`, `src/gamer/static/common.js`,
`src/gamer/games/othello/static/view.js`, `tests/test_sessions.py`,
`tests/test_api_sessions.py`

**Key changes**:
- `Lifecycle = Literal["waiting", "playing", "finished"]`
- `Session` (dataclass) has:
  - fields: `id`, `game`, `state`, `version: int`, `seat_tokens: dict[str, Seat]`
  - methods: `lifecycle -> Lifecycle`, `seat_for(token) -> Seat | None`,
    `join() -> tuple[Seat, str]` (raises `SessionFull`)
- `SessionManager` has:
  - `create(game_id) -> tuple[Session, Seat, str]`
  - `get(session_id) -> Session` (raises `SessionNotFound`)
  - `list_open(game_id) -> list[Session]`
- Errors: `SessionFull`, `SessionNotFound`, `BadToken`
- Models: `SessionSummary{session_id, game_id}`,
  `SeatAssignment{session_id, seat, token}`, and
  `SessionState{session_id, game_id, version, lifecycle, public_state,
  status, legal_moves, seats: dict[Seat, bool], your_seat}`
- Routes:
  - `GET /api/games/{game}/sessions` and `POST /api/games/{game}/sessions`
  - `POST /api/sessions/{id}/join` (409 if full)
  - `GET /api/sessions/{id}/state`. The `X-Player-Token` header is
    optional; without it `your_seat` is null. A bad token gets 403.
- Page routes: `/games/{game}` serves `lobby.html`, and
  `/games/{game}/sessions/{sid}` serves `game.html`
- `common.js` adds `getToken(sid)`, `setToken(sid, token)` and
  `poll(fn, ms) -> stop()`
- `game.js` flow: if there's no token and the session is `waiting`, join;
  if it's full, show "session full"; then poll every 1s and call
  `view.render(...)`
- `view.js` exports `render(container, publicState, legalMoves, onMove)`.
  In this phase it only draws the board.

**Verify**: `uv run pytest` passes. It covers create, join, the full-session
409, `list_open` dropping full sessions, the token → seat mapping, 403 on a
bad token, 404 on an unknown session, and `version` going up on join.
Manual: tab A creates a game and shows "waiting for opponent". Tab B joins
from the lobby, and both show the start board with the status "playing".
Refreshing tab A keeps it as Black.

---

## Phase 3: Making Moves
Full Othello move rules, the move endpoint with turn and version checks, and
a clickable board with legal moves highlighted.

**Files**: `src/gamer/games/othello/logic.py`, `src/gamer/sessions.py`,
`src/gamer/app.py`, `src/gamer/protocol.py`, `src/gamer/static/game.js`,
`src/gamer/games/othello/static/view.js`, `tests/test_othello.py`,
`tests/test_api_moves.py`

**Key changes**:
- Othello: `legal_moves`, `apply_move` (flips in all 8 directions, with an
  automatic pass when the opponent has no move), `parse_move({"row",
  "col"})`, and `move_to_public`
- `Session.move(token, raw_move: dict, version: int) -> None` (raises
  `BadToken`, `StaleVersion`, `NotYourTurn` or `IllegalMove`). It bumps
  `version`. There must be no `await` between validating and applying.
- `MoveRequest{move: dict, version: int}`
- Route: `POST /api/sessions/{id}/moves -> SessionState`. Responses: 400
  illegal, 409 out of turn or stale, 403 bad token, 404 unknown.
- `SessionState.legal_moves` is filled in for the seat to move
- `game.js` `onMove` posts the move with the version on screen, renders the
  response, and shows the error text on failure
- `view.js` highlights legal squares and makes only those clickable

**Verify**: `uv run pytest` passes. The Othello unit tests cover each
direction, multi-line flips, moves that flip nothing, an occupied square,
out of bounds, and a forced pass. The API tests cover a legal move, out of
turn, a stale version, an illegal move, and `version` going up. Manual: two
tabs alternate moves, and each move appears on the other tab within about a
second.

---

## Phase 4: Game End & Extensibility Proof
Game over and the winner or draw, the end-of-game UI with polling stopped,
a full-game integration test, and a stub game that proves new games need no
changes to the server core.

**Files**: `src/gamer/games/othello/logic.py`, `src/gamer/sessions.py`,
`src/gamer/static/game.js`, `src/gamer/games/othello/static/view.js`,
`tests/test_othello.py`, `tests/test_full_game.py`,
`tests/stub_game/__init__.py`, `tests/stub_game/static/view.js`,
`tests/test_extensibility.py`

**Key changes**:
- Othello `status` gets `finished` (neither side can move) and `winner`
  (more discs, or `None` for a draw). When the game is finished,
  `to_move = None`.
- `Session.lifecycle` returns `"finished"`, and moves after that raise
  `NotYourTurn`
- `game.js` shows the result banner and stops polling after it renders a
  `finished` state
- `tests/stub_game` holds a trivial 2-seat game (e.g. "first to claim 3
  squares") that implements `Game`
- `test_extensibility` calls `create_app(registry={...stub})` and plays
  create → join → moves → finished over HTTP. It also checks that the
  stub's `/games/stub/static/view.js` is served.

**Verify**: `uv run pytest` passes. It covers a scripted full Othello game
played to the end through the API, a board-filled finish, an early finish
when neither side can move, a draw, and the stub game playing end to end.
Manual: play a full game in two tabs. Both show the winner, and the browser
network tab shows that polling stopped.

---

## Testing Checkpoints
- **After Phase 1**: the server starts, the directory lists Othello, and the
  `Game` protocol and registry exist.
- **After Phase 2**: two browsers can create, join and share a session, and
  both see the start board. Seats survive a page refresh.
- **After Phase 3**: players can make moves with the rules enforced
  server-side, and moves reach the opponent through polling.
- **After Phase 4**: full games finish with the correct result, and a new
  game can be added with no changes to the server core (R2, R3).

## Notes
- Design addition: `parse_move` / `move_to_public` / `static_dir` are added
  to the `Game` protocol (design decision 3) so the server core stays
  rule-free and never interprets move JSON. This adds detail to the design
  rather than changing it.
- The `tests/stub_game` is test-only and is never added to the production
  `REGISTRY`. This keeps "Othello only" scope (`SPEC.md:70`).
