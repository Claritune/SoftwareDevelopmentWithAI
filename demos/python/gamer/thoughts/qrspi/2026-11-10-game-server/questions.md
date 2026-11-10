# Clarifying Questions

## Project Type
greenfield

## Goal Summary
A local Python server hosting turn-based multiplayer games, Othello first, with
each game in its own logic module behind a common interface. Players connect
from separate browser-based HTML clients that show a game directory and a
per-game view. The server is the source of truth and validates every move. V1
has no authentication and runs locally only.

## Existing Constraints
- `SPEC.md` — requirements R1–R6, Othello rules, and the out-of-scope list
  (no auth, no persistence, no AI opponents, no spectators/chat, Othello only)
- `CLAUDE.md` — only reference files inside `demos/python/gamer/`
- `docs/skills/` — QRSPI phase skills. Greenfield, so Research is skipped
- No coding rules, stack choices, or scaffolding exist yet

## Questions

1. **Transport & server stack**: Should clients talk to the server over
   WebSockets (server pushes moves instantly) or plain HTTP with polling? And
   should one framework (e.g. FastAPI or aiohttp) serve both the HTML client and
   the game connection, or should we use bare `asyncio` + `websockets` with a
   separate static file server?
   - *Why it matters*: This sets the concurrency model (async event loop vs
     threads), the dependency list, how the client gets opponent moves, and
     whether there is one process to run or two.
   - *Default if unanswered*: FastAPI + Uvicorn. One process serves the static
     HTML client and a WebSocket endpoint, all on asyncio.

2. **Session discovery & joining**: How do two players end up in the same game?
   (a) a lobby that lists open sessions per game and lets players join them,
   (b) the creator shares a session code or URL, or (c) automatic pairing of
   the next two players who pick the same game.
   - *Why it matters*: This decides which server state we keep (a session
     registry with open/full/finished states), which messages the protocol
     needs (list, create, join), and what the directory page shows.
   - *Default if unanswered*: (a) plus (b). The directory shows the games, each
     game page lists open sessions with a "Create" button, and every session
     has a shareable URL.

3. **Disconnects & session lifecycle**: When a player closes the tab or loses
   the connection mid-game, what happens? Hold their seat so they can
   reconnect (for how long?), forfeit right away, or abandon the session? And
   when do finished or empty sessions get cleaned up?
   - *Why it matters*: Reconnection needs a player token kept on the client
     and seat reservation on the server. Forfeit or abandon is much simpler.
     This also affects how players are identified, since there is no auth.
   - *Default if unanswered*: The server gives each player a random token
     stored in `localStorage`. Reconnecting with the token within the server's
     lifetime reclaims the seat. The opponent sees "waiting for opponent". A
     session is removed when both players leave or the game ends.

4. **Game module interface boundary**: How much of each game lives on the
   server versus the client? Should the server send only the raw game state
   (board, turn, scores) while a game-specific JS view renders it? Or should
   the server also send derived data like the list of legal moves, so clients
   stay rule-free? And should a game be one Python module, or a package that
   bundles its Python logic with its HTML/JS view?
   - *Why it matters*: This defines the common game interface (R3), the
     message protocol, and what "adding a new game" really takes: one Python
     file, or a Python file plus a front-end view.
   - *Default if unanswered*: Each game is a package (`games/othello/`) with
     pure-Python logic (`init_state`, `legal_moves`, `apply_move`, `status`)
     and its own static view (`othello.js`). The server includes legal moves
     in every state update so the client can highlight them without knowing
     the rules.

5. **Client technology**: Plain HTML/CSS/vanilla JS served as static files
   with no build step, or a front-end framework (React/Vue/Svelte) with a
   build toolchain?
   - *Why it matters*: Adding Node/npm and a build step changes the repo
     layout, how the project is run, and how complex the project is to set up
     and demo.
   - *Default if unanswered*: Vanilla HTML/CSS/JS ES modules, no build step,
     served by the Python server.

6. **Hot-seat play**: Should two players be able to share one browser tab
   (taking turns on the same screen), or does every player always use their
   own client?
   - *Why it matters*: Hot-seat play means one connection controls both seats.
     That changes how seats are tied to connections and how the server checks
     whose turn it is.
   - *Default if unanswered*: Not supported in v1. One client per seat. Two
     tabs on the same machine work for local testing.

7. **Python tooling & testing**: Which Python version and project tooling
   (e.g. `uv` + `pyproject.toml`, `pytest`), and how far should automated
   tests go: game logic only, or also server/WebSocket integration tests?
   - *Why it matters*: This sets the repo scaffolding and the test harness
     later phases will use. Integration tests need an async test client and
     shape how the server is structured for testability.
   - *Default if unanswered*: Python 3.12, `uv`, `pytest`. Full unit coverage
     of Othello logic, plus integration tests for the session flow (create,
     join, move, game over) using FastAPI's test client.
