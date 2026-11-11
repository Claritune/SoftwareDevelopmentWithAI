# Structure Outline

## Approach
One FastAPI process serves a static ES-module client and a `{"v":1,"type","payload"}` JSON API. Clients poll every 1 s; all state lives in memory on one event loop. Game rules live only in pure modules behind a `Game` protocol, registered in one `GAMES` mapping; the core is proven game-agnostic by tests against a `FakeGame`.

Greenfield: there is no `research.md` (Research skipped per `SPEC.md`). Othello's rules are split across Phases 2 and 4 so that each phase stays vertical: Phase 2 needs only the initial position, legal moves, and a snapshot; Phase 4 adds applying moves.

## Phase 1: Skeleton and Game Directory
`uv run gamer` starts the server; the browser shows the directory listing Othello, fetched from `GET /api/games`.

**Files**: `pyproject.toml`, `.gitignore`, `src/gamer/__init__.py`, `src/gamer/__main__.py`, `src/gamer/app.py`, `src/gamer/protocol.py`, `src/gamer/games/__init__.py`, `src/gamer/games/base.py`, `src/gamer/games/othello.py` (metadata only), `src/gamer/static/index.html`, `src/gamer/static/style.css`, `src/gamer/static/js/app.js`, `src/gamer/static/js/api.js`, `tests/conftest.py`, `tests/fakes.py`, `tests/test_api.py`

**Key changes**:
- `main(argv: list[str] | None = None) -> None`: CLI `--host` (default `127.0.0.1`), `--port` (default `8000`)
- `create_app(games: Mapping[str, Game] | None = None, registry: SessionRegistry | None = None) -> FastAPI`
- `envelope(type_: str, payload: Any) -> dict`; `ApiError(status: int, code: str, message: str)` plus one exception handler
- `class Game(Protocol)`: `id`, `name`, `min_players`, `max_players`, `initial_state()`, `parse_move(payload)`, `apply_move(state, seat, move)`, `snapshot(state)`; `InvalidMove`, `IllegalMove`
- `GAMES: dict[str, Game]`
- Client: hash router (`#/`, `#/{game}`, `#/{game}/{code}`), directory view

**Verify**: `uv run pytest` passes (`GET /api/games` returns the envelope with Othello; the injected `FakeGame` shows up instead when passed in); `uv run ruff check && uv run ruff format --check`; manual: `uv run gamer`, open `http://127.0.0.1:8000/`, Othello is listed.

---

## Phase 2: Create a Session and Join by Link
A player creates an Othello session and gets a code and a link. A second tab opening the link joins. Both tabs poll and render the starting board, with legal moves highlighted for Black. Moves aren't possible yet.

**Files**: `src/gamer/sessions.py` (new), `src/gamer/protocol.py`, `src/gamer/app.py`, `src/gamer/games/othello.py` (state, legal moves, snapshot), `src/gamer/static/js/app.js`, `src/gamer/static/js/api.js`, `src/gamer/static/games/othello.js` (new), `src/gamer/static/style.css`, `tests/fakes.py`, `tests/test_sessions.py` (new), `tests/games/test_othello.py` (new), `tests/test_api.py`

**Key changes**:
- `Seat { player_id: str, name: str }`; `Session { code, game, state, seats, version }` with `status`, `join(name) -> tuple[int, Seat]`, `to_payload() -> dict`
- `SessionRegistry.create(game, name) -> tuple[Session, Seat]`, `.get(code) -> Session`, `.open_sessions(game_id) -> list[Session]`
- `new_code() -> str` (6 chars, no `0/O/1/I`)
- Errors: `SessionNotFound` (404), `SessionFull` (409), `GameNotFound` (404), `BadRequest` (400)
- `NameRequest { v: Literal[1], type: str, payload: { name: str } }`
- Routes: `POST /api/games/{game_id}/sessions`, `POST /api/sessions/{code}/join`, `GET /api/sessions/{code}`
- `OthelloState { board: tuple[tuple[int|None,...],...], current: int|None, last_event: str|None }`; `legal_moves(board, seat) -> list[tuple[int,int]]`
- Client: name field, Create button, link-join flow, game view with polling, `render(container, state, {mySeat, onMove})`

**Verify**: `uv run pytest` passes (registry codes, joins, full session, initial Othello snapshot, API create/join/poll with the fake game, 404/409/400 errors); manual: create in tab A, open the link in tab B, both show the board with status `playing` and 4 legal moves for Black; a third tab sees "Session full".

---

## Phase 3: Lobby
The game's lobby lists sessions that are still waiting, refreshed by polling. Clicking one joins it.

**Files**: `src/gamer/app.py`, `src/gamer/static/js/app.js`, `src/gamer/static/js/api.js`, `tests/test_api.py`, `tests/test_sessions.py`

**Key changes**:
- Route: `GET /api/games/{game_id}/sessions` returns type `sessions`, a list of `{code, players: [{seat, name}]}`
- Client: the lobby view polls every 1 s and has a Join button on each row; a `409` shows "Session full" without leaving the lobby

**Verify**: `uv run pytest` passes (only waiting sessions for that game are listed; full ones drop out); manual: tab A creates, tab B sees it within about 1 s, joins, and the entry disappears from the lobby.

---

## Phase 4: Moves to Game Over
Players alternate moves from the browser. Passes happen automatically, and the game ends with scores and a winner. All rejections map to error envelopes.

**Files**: `src/gamer/games/othello.py` (`parse_move`, `apply_move`), `src/gamer/sessions.py` (`Session.move`, `UnknownPlayer`), `src/gamer/protocol.py`, `src/gamer/app.py`, `src/gamer/static/js/app.js`, `src/gamer/static/js/api.js`, `src/gamer/static/games/othello.js`, `tests/fakes.py`, `tests/games/test_othello.py`, `tests/test_sessions.py`, `tests/test_api.py`

**Key changes**:
- `OthelloMove { row: int, col: int }`; `parse_move(payload) -> OthelloMove` raises `InvalidMove`; `apply_move(state, seat, move) -> OthelloState` raises `IllegalMove`, auto-passes, sets `last_event`, finishes the game
- `Session.move(player_id: str, payload: Any) -> None`; `UnknownPlayer` (403); `GameNotStarted` (409)
- `MoveRequest { v: Literal[1], type: str, payload: { player_id: str, move: Any } }`
- Route: `POST /api/sessions/{code}/moves`; maps `InvalidMove` to 400 and `IllegalMove` to 409
- Client: clicking a highlighted square sends the move; the result banner appears; polling stops when the game is finished

**Verify**: `uv run pytest` passes (Othello flips, pass, game over, draw; two simulated HTTP players finish an Othello game by always choosing `legal_moves[0]`; the fake game finishes through the same core); manual: two tabs play to completion.

## Testing Checkpoints
- **After Phase 1**: the server runs and the directory works; the envelope, error handler, DI factory, and `Game` protocol exist.
- **After Phase 2**: sessions can be created, joined by link, and polled; `version` increases on join; the starting Othello snapshot is correct; seat and code rules are covered by unit tests.
- **After Phase 3**: the lobby lists waiting sessions only, and joining from the lobby works.
- **After Phase 4**: full games can be played over HTTP and in the browser, with every rejection path (400/403/404/409) tested. v1 is complete.
