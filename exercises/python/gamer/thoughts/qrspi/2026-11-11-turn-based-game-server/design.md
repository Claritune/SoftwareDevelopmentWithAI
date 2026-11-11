# Design Discussion

## Current State

Greenfield. The project directory has no code, only:

- `SPEC.md`: requirements R1–R6, Othello rules, and v1 scope (`SPEC.md:10-70`).
- `AGENTS.md`: all work stays inside the project directory (`AGENTS.md:3`).
- QRSPI artifacts in this directory: `task.md`, `questions.md`, `answers.md`.

Constraints carried forward:

- The core must not know any game's rules. Games plug in through a common interface (`SPEC.md:23-28`).
- Adding a game must need only "a new game module plus its registration" (`SPEC.md:20-21`).
- Game logic must be unit-testable with no server or client running (`SPEC.md:29`).
- The server is the authority and rejects illegal or out-of-turn moves (`SPEC.md:34-35`).
- One slow or absent client must not block the others (`SPEC.md:14-15`).
- No auth and no persistence. Players are identified by display name or a session-assigned id (`SPEC.md:51-52`, `SPEC.md:63-70`).
- Out of scope: AI, spectators, chat, matchmaking, rankings, and other games (`SPEC.md:63-70`).

## Desired End State

`uv run gamer` starts one process on `http://127.0.0.1:8000`. That process serves both the static HTML client and a JSON API. In a browser:

1. The **directory** view lists games (v1: Othello).
2. Picking a game opens its **lobby**. The lobby lists open sessions, refreshed by polling, and has a "Create session" button and a display-name field.
3. Creating a session gives a short code (e.g. `K7QX2M`) and a shareable link `/#/othello/K7QX2M`. A second player joins by clicking the session in the lobby or by opening the link.
4. The **game view** shows the board, whose turn it is, the scores, and the result. Legal moves are highlighted only for the player whose turn it is. Moves made in one tab show up in the other within about 1 second.

How we verify it:

- `uv run pytest`: Othello unit tests, session-registry unit tests, and in-process HTTP integration tests in which two simulated players finish a game.
- An integration test runs the core against a **fake game**, which shows the core is game-agnostic (R2/R3).
- `uv run ruff check` and `uv run ruff format --check` pass.
- A manual check: two browser tabs play Othello to completion.

Diagrams: `diagrams-architecture.md` (components, trust boundaries), `diagrams-modules.md` (imports, key types, session states), `diagrams-sequences.md` (lobby, create/join, link join, move, auto-pass, polling).

## Patterns to Follow

There is no existing code, so these patterns come from the constraint docs and the answers:

- **Rules live only in game modules** (`SPEC.md:23-28`). Server core files must never branch on a game id or import `othello`. If you're about to write `if game_id == "othello"` in the core, stop, because that's the anti-pattern.
- **No rules on the client** (`answers.md:6`). The client renders the `legal_moves` the server sends and never computes legality itself. A renderer only translates a click into a move payload.
- **Game logic is pure functions over immutable state** (`SPEC.md:29`). No I/O, no asyncio, no FastAPI imports in `gamer/games/`.
- **Explicit registration** (`SPEC.md:20-21`). There is one `GAMES` mapping in `gamer/games/__init__.py`. Adding a game means a new module plus one line there. No entry points and no import scanning.
- **Dependency injection over globals.** `create_app(games=..., registry=...)` builds the app, so tests can inject a fake game and a fresh registry. No module-level mutable singletons.
- **Envelope everywhere** (`answers.md:6`). Every request and response body is `{"v": 1, "type": ..., "payload": ...}`.
- **Stay inside the project dir** (`AGENTS.md:3`). That includes tooling: uv creates `.venv` locally.

## Design Decisions

1. **Transport**: HTTP with interval polling, no WebSockets (`answers.md:3`). The client polls `GET` endpoints every ~1 s. Each request is short and stateless, so a dead client just stops polling and holds nothing open, which satisfies R1.

2. **Framework**: **FastAPI + uvicorn**, the user's choice. One process serves the static files (`StaticFiles`) and the API. Pydantic models validate the envelope and the core request fields. Integration tests use `httpx.AsyncClient` with `ASGITransport`, so no real socket is needed.

3. **Concurrency model**: a single asyncio event loop with all state in memory. Handlers make each state change synchronously, with no `await` between reading and writing state. On one loop that makes each change atomic, so v1 needs no locks. Any future `await` inside a state change must add a per-session `asyncio.Lock`.

4. **Game interface** (`gamer/games/base.py`): a `typing.Protocol` with:
   - metadata: `id`, `name`, `min_players`, `max_players` (Othello: 2/2)
   - `initial_state() -> State`
   - `parse_move(payload: dict) -> Move`, which raises `InvalidMove` on a malformed payload
   - `apply_move(state, seat: int, move) -> State`, which raises `IllegalMove` for an illegal or out-of-turn move
   - `snapshot(state) -> dict`: JSON-safe output with `board` (game-specific), `current_player`, `legal_moves`, `scores`, `status` (`"playing" | "finished"`), `winner` (seat, or `null` for a draw), and `seat_labels` (e.g. `["Black", "White"]`)

   Players are identified to games only by **seat index** (`0..n-1`). Names and player IDs stay in the core.

5. **Othello passes are automatic**: inside `apply_move`, if the next player has no legal move, the turn goes back to the mover. If neither player can move, the status becomes `finished`. There is no explicit "pass" move, so the client never needs to know about passing. The snapshot includes a `last_event` such as `"White passed"` so the UI can explain why the turn didn't change.

6. **Sessions** (`gamer/sessions.py`): a `Session` holds the game, the state, its seats (`player_id`, `name`), a `version: int`, and a core `status` of `waiting`, `playing`, or `finished`. The status is `waiting` until `max_players` have joined, then it follows the game's snapshot. `version` goes up on every join and move. `SessionRegistry` maps codes to sessions and lists open sessions for each game.

7. **Session codes**: 6 characters from an alphabet without look-alike characters (no `0/O/1/I`), generated with `secrets`. If a generated code already exists, generate another. The code doubles as the session id in URLs.

8. **Seat ownership**: on create or join, the server returns an opaque `player_id` (`secrets.token_urlsafe(16)`). Every move must include it, and the server maps it to a seat. The client keeps it only in memory, so a page reload loses the seat. That matches "no session management" (`answers.md:5`). `player_id` never appears in snapshots.

9. **HTTP API** (all bodies use the envelope):

   | Method & path | Purpose | Response `type` |
   |---|---|---|
   | `GET /api/games` | Directory | `games` |
   | `GET /api/games/{game_id}/sessions` | Lobby: sessions still `waiting` | `sessions` |
   | `POST /api/games/{game_id}/sessions` `{name}` | Create a session and take seat 0 | `joined` (`code`, `player_id`, `seat`, `state`) |
   | `POST /api/sessions/{code}/join` `{name}` | Take the next free seat | `joined` |
   | `GET /api/sessions/{code}` | Poll for the snapshot | `state` |
   | `POST /api/sessions/{code}/moves` `{player_id, move}` | Make a move | `state` |

   The `state` payload has the core fields (`code`, `game_id`, `version`, `status`, `players: [{seat, name}]`) plus the game's `snapshot()` output.

10. **Errors**: `{"v":1,"type":"error","payload":{"code","message"}}`, sent with a matching HTTP status. `400` covers a bad envelope, a wrong `v`, or a malformed move. `403` covers an unknown `player_id`. `404` covers an unknown game or session. `409` covers a full session, joining a finished session, out-of-turn play, or an illegal move. The game's exceptions are turned into these errors in one exception handler.

11. **Client** (static, ES modules, no build step, per `answers.md:7`): `index.html` plus `js/app.js` (a hash router for `#/`, `#/{game}`, and `#/{game}/{code}`, plus the polling loop), `js/api.js` (fetch wrappers that build the envelope), and `games/othello.js` exporting `render(container, state, {mySeat, onMove})`. The core loads renderers with `import(\`./games/${id}.js\`)`. The client polls every 1 s and skips re-rendering when `version` hasn't changed. Opening a `#/{game}/{code}` link without a `player_id` triggers a join. If the session is already full, the page shows "Session full".

12. **Binding**: the default host is `127.0.0.1`. `gamer --host 0.0.0.0` allows LAN play (`SPEC.md:49-50`). `--port` is configurable.

13. **Tooling** (`answers.md:9`): Python 3.12+, uv, `pyproject.toml` with a `src/gamer/` layout and a `gamer` console script. Dev dependencies are `pytest`, `pytest-asyncio` (`asyncio_mode = "auto"`), `httpx`, and `ruff`. Static files ship inside the package (`src/gamer/static/`).

## What We're NOT Doing

- WebSockets, server-sent events, or long-polling.
- Reconnect tokens, `localStorage` seat recovery, timeouts, forfeits, session cleanup, or rematches (`answers.md:5`).
- Hot-seat play (`answers.md:8`).
- Spectators, even though `GET /api/sessions/{code}` is readable by anyone. No UI is built for watching.
- Auth, persistence, AI opponents, chat, matchmaking, rankings, or games other than Othello (`SPEC.md:63-70`).
- Protocol negotiation or diffs: always a full snapshot with a fixed `v: 1`.
- Browser or end-to-end tests. The client is checked by hand.
- Plugin discovery (entry points). Registration is explicit.
- An OpenAPI-driven client. FastAPI's `/docs` is a free side effect, not something we rely on.

## Open Risks

- **Unbounded memory**: sessions are never removed, including finished and abandoned ones. That's fine for a local tool, but a long-running server slowly grows. Cleanup is out of scope for v1.
- **Orphaned seats**: if a player reloads mid-game, their seat is lost for good and the opponent waits indefinitely. This follows from `answers.md:5`, but it may feel like a bug in manual testing.
- **Polling latency and load**: a 1 s interval means up to 1 s of delay and one request per second per tab. That's fine locally. The interval is a single client constant.
- **Lobby races**: two players may both click the last open seat. The second one gets a `409` and the lobby must show it cleanly.
- **Envelope and FastAPI ergonomics**: FastAPI wants typed bodies, while the move `payload` is game-specific (`dict[str, Any]`) and parsed by the game. Pydantic must not reject or coerce it. Keep it untyped at the core level.
- **Static file caching**: browsers may cache old ES modules during development. We may need `Cache-Control: no-cache` on static responses.
- **Async test setup**: the pytest-asyncio and httpx `ASGITransport` versions must be compatible. Pin minimum versions in `pyproject.toml`.
