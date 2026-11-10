# Design Discussion

## Current State

Greenfield. `demos/python/gamer/` contains only:
- `SPEC.md` — requirements R1–R6 (`SPEC.md:10-52`), Othello rules
  (`SPEC.md:54-61`), out of scope (`SPEC.md:63-70`)
- `CLAUDE.md` — scope rule: reference only files in this folder
- `docs/skills/` — QRSPI phase skills
- `thoughts/qrspi/2026-11-10-game-server/` — task, questions, answers

There is no application code, `pyproject.toml`, or tests.

## Desired End State

Running `uv run gamer` (or `uv run uvicorn gamer.app:app`) starts a single
local process on `http://127.0.0.1:8000`:

1. `/` — **game directory** listing the registered games (v1: Othello).
2. `/games/othello` — **lobby** for Othello. Lists open sessions waiting for
   a second player and has a "Create game" button.
3. `/games/othello/sessions/{session_id}` — **game view**, a shareable URL.
   The first visitor creates the game and takes Black. The second visitor to
   an open session takes White. Later visitors are told the session is full.
4. Both players see the board, whose turn it is, the disc counts, legal moves
   highlighted for the player to move, and the result when the game ends.
   The client polls the server about once per second, so an opponent's move
   shows up within about a second. The mover sees the result immediately in
   the response to their move request.
5. Refreshing the tab reclaims the seat via a token in `sessionStorage`,
   which is kept per tab. Closing the tab gives up the seat. The server
   does not notice or report that the tab was
   closed (see decision 7).

**How to verify:**
- `uv run pytest` passes:
  - Othello unit tests cover the opening position, flips in all 8
    directions, illegal moves, passes, game end, and win/draw.
  - Integration tests use FastAPI `TestClient` (plain HTTP) to cover
    creating, joining, moving, rejecting out-of-turn and illegal moves,
    polling for an opponent's move, reconnecting, and playing a full game to
    completion.
- Manual check: two browser tabs play a full Othello game end to end.
- The extensibility check passes: adding a trivial test-only game to the
  registry makes it appear in the directory and playable through the same
  protocol, with no changes to the server core (R2, `SPEC.md:20`).

## Patterns to Follow

No existing code to follow. Constraints come from the spec and answers:

- **Rules live only in game modules** (`SPEC.md:27-28`). The server core
  never imports `games.othello` directly. It goes through the registry and
  the `Game` interface.
- **The server is the source of truth** (`SPEC.md:35-36`). Clients send
  intentions (`POST .../moves`). The server validates and applies them, and
  clients learn the result by polling. Clients never compute game outcomes.
- **Game logic is pure and testable without I/O** (`SPEC.md:29`). There is
  no asyncio, FastAPI, or JSON transport code in `games/*/logic.py`.
- **Stay within this folder** (`CLAUDE.md`). Do not copy patterns, configs,
  or code from other projects in the repo.

**Anti-patterns to avoid:**
- Game-specific `if game_id == "othello"` branches in the server or the
  generic client.
- Blocking calls inside async handlers. The game logic is fast and pure, so
  calling it directly from the event loop is fine. File or network I/O is not.
- Sync `def` route handlers that touch session state. FastAPI runs them in a
  threadpool, which breaks the single-event-loop atomicity that decision 6
  relies on. Every handler that touches session state is `async def`.
- Long-polling or held-open requests. Every request returns immediately.

## Design Decisions

1. **Stack**: Python 3.12, FastAPI + Uvicorn, `uv`, `pytest`. The client is
   vanilla HTML/CSS/JS ES modules with no build step, served by FastAPI
   `StaticFiles` (answers 1, 5, 7). **No WebSockets.** All client↔server
   traffic is plain HTTP request/response, and clients poll periodically
   for updates (this revises answer 1).

2. **Package layout** (detailed in Structure phase):
   ```
   src/gamer/
     app.py            # FastAPI app, routes, static mounts
     sessions.py       # Session, SessionManager (in-memory registry)
     protocol.py       # message shapes (pydantic models)
     games/
       __init__.py     # REGISTRY: dict[str, Game] — explicit registration
       base.py         # Game protocol, IllegalMove, GameStatus
       othello/
         logic.py      # pure rules
         static/view.js
     static/           # index.html, lobby.html, game.html, common.js, css
   tests/
   ```

3. **Game interface** (`games/base.py`): each game is one object that
   implements:
   - `id`, `name`, `seats` (Othello: `["black", "white"]`)
   - `initial_state() -> State`
   - `legal_moves(state, seat) -> list[Move]`
   - `apply_move(state, seat, move) -> State`, which raises `IllegalMove`
     for illegal or out-of-turn moves
   - `status(state) -> GameStatus` (`to_move`, `finished`, `winner | None`,
     `scores`)
   - `to_public(state) -> dict`, a JSON-safe view of the state for clients

   State is an immutable value (frozen dataclass/tuples). `apply_move` returns
   a new state, which keeps tests and reasoning simple. `apply_move` handles
   Othello passes automatically: if the next player has no legal move, the
   turn goes back to the mover.

4. **Registration**: an explicit `REGISTRY` in `games/__init__.py`. Adding a
   game means one new package plus one registry line, which satisfies
   `SPEC.md:20-21`. Auto-discovery via entry points is not needed in v1.

5. **HTTP API with periodic polling**: every endpoint is JSON over HTTP.
   Session endpoints identify the player by an `X-Player-Token` header.
   - Directory and lobby:
     - `GET /api/games` lists the registered games.
     - `GET /api/games/{game}/sessions` lists open sessions.
     - `POST /api/games/{game}/sessions` creates a session. It returns
       `{session_id, seat, token}`.
     - `POST /api/sessions/{id}/join` returns `{seat, token}`. It returns
       409 if the session is full.
   - Play:
     - `GET /api/sessions/{id}/state` returns `{version, lifecycle,
       public_state, status, legal_moves, seats}`. `legal_moves` is for the
       caller's seat (empty if it's not their turn). `seats` shows each
       seat's occupancy (empty or taken).
     - `POST /api/sessions/{id}/moves` takes `{move, version}` and returns
       the new state in the same shape as `GET .../state`. It returns 400
       for an illegal move, 409 for out of turn or a stale `version`, 403
       for a bad token, and 404 for an unknown session.
   - **Poll intervals**: the game view polls `GET .../state` every 1s, and
     the lobby polls `GET .../sessions` every 2s. Both are client-side
     constants, easy to tune.
   - **`version`**: an integer that goes up on every state change (join or
     move). A move must quote the `version` the client rendered. This stops
     a double click or an outdated board from sending a move against state
     the player hasn't seen. The client can also skip re-rendering when the
     `version` is unchanged.
   - A full state response is small (an 8×8 board), so v1 needs no
     `If-None-Match`, `?since=` or 304 optimization.

6. **Concurrency model**: a single asyncio event loop with an in-memory
   `SessionManager`. Handlers are `async def`, and none of them await
   between reading and writing session state (validate → apply →
   bump `version` has no await points). That makes each request atomic on
   the event loop, so no locks are needed. Each request is short and
   independent, so a slow or vanished client cannot block anyone else
   (R1, `SPEC.md:14-15`).

7. **Identity & stateless clients** (answer 3): there are no accounts.
   Creating or joining a session returns a random `secrets.token_urlsafe`
   token tied to a seat. The client stores `{session_id: token}` in
   `sessionStorage` and sends it on every session request.
   `sessionStorage` is per tab, so two tabs in one browser can hold the two
   seats of a game (answer 6). Refreshing keeps the seat, and closing the
   tab gives it up. Reclaiming a seat after closing the tab is part of the
   deferred disconnect work.
   - **The server keeps no per-client state.** The token is all it needs to
     identify a seat. Each request is handled on its own merits, and the
     server records nothing about when or how often a client polls.
   - **No disconnect detection.** The server has no concept of a seat being
     "connected" or "disconnected". The only waiting state shown is
     "waiting for opponent" while the second seat is still empty. This is
     deferred to a separate follow-up.
   - **Reconnecting** is just polling again with the stored token, and
     there is no handshake.
   - Two tabs using the same token are harmless: they share one seat, and
     the server's turn and `version` checks stop double moves.

8. **Session lifecycle**: `waiting` (one seat filled) → `playing` (all seats
   filled) → `finished`. Sessions stay in memory until the server stops.
   There is no automatic cleanup, because deciding that a session is
   abandoned needs the client tracking we are deferring. The lobby lists
   only `waiting` sessions. Nothing survives a restart (`SPEC.md:67`).

9. **Seat assignment**: the creator gets the first seat (Black, so the
   creator moves first). The joiner gets the next free seat. Random color
   assignment can come later.

10. **Client architecture**: the generic `game.html` + `common.js` handles the
    poll loop (`setInterval` + `fetch`), token storage, sending moves, the
    status bar, and errors. It stops polling once the game is finished and
    the final state has been shown. It loads the game's
    view with `import('/games/{id}/static/view.js')`, which exports
    `render(container, publicState, legalMoves, onMove)`. The Othello view
    draws the board and calls `onMove({row, col})` when a highlighted square
    is clicked. The view contains no rule logic: legality comes from the
    server's `legal_moves`.

## What We're NOT Doing

- Auth, accounts, or profiles. Tokens are seat claims, not identity.
- Persistence: no database and no saving games to disk.
- AI opponents, spectators, chat, matchmaking, rankings, or rematch flow.
- Hot-seat play (two seats from one client).
- Any game besides Othello, apart from a test-only stub game used to prove
  extensibility.
- A front-end framework, bundler, Node/npm, or TypeScript.
- Deployment config: no Docker or TLS, and the server binds to `127.0.0.1`
  by default.
- Move timers or clocks.
- WebSockets, Server-Sent Events, long-polling, or any other push channel.
  Clients only poll.
- **Deferred to a separate follow-up:**
  - presence/disconnect detection (last-seen tracking, "opponent
    disconnected" status)
  - cleanup of abandoned or finished sessions

## Open Risks

- **Update latency**: an opponent's move can take up to one poll interval
  (~1s) to appear. That is fine for turn-based play, but it is a visible
  trade-off of choosing polling over push.
- **Abandoned sessions accumulate**: with no cleanup, `waiting` sessions
  whose creator left stay in the lobby until the server restarts. That is
  acceptable for local v1 and goes away with the deferred presence work.
- **Silent opponent**: if the opponent closes their tab, the remaining
  player just sees "opponent's turn" indefinitely.
- **Dynamic `import()` of game views**: this relies on predictable static
  mount paths per game. A wrong mount shows up only as a blank board, so the
  client needs a visible error when the view fails to load.
- **Generic state shape**: `to_public` returns a game-defined dict. If a
  future game needs per-seat hidden information (e.g. card games), this has
  to become `to_public(state, seat)`. We note this now but do not build it.
