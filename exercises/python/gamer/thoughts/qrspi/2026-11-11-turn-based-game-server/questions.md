# Clarifying Questions

## Project Type
greenfield

## Goal Summary
Gamer is a local-only Python game server that hosts turn-based multiplayer games, with a browser-based HTML client. The server holds the game state, checks every move, and runs several sessions in parallel. Each game's rules sit in their own module behind a common interface, so a game can be added without touching the server core. Version 1 ships only Othello, with no authentication and no persistence.

## Existing Constraints
- All work must stay inside the project directory. Nothing may be read, modified, or run in parent, sibling, or external directories (`AGENTS.md`).
- Game logic must be unit-testable without a running server or client (`SPEC.md` R3).
- Out of scope for v1: auth, deployment beyond the LAN, persistence across restarts, AI opponents, spectators, chat, matchmaking, rankings, and games other than Othello (`SPEC.md`).
- Phase artifacts go under `thoughts/qrspi/<id>/`. Research is skipped because the project is greenfield (`SPEC.md` Process).

## Questions

1. **Transport and server framework**: Should the client and server talk over WebSockets with server push, or over HTTP with polling? And should the server use plain `asyncio` + `websockets` (with a separate static file server), or a framework that serves both the HTML client and the real-time channel (FastAPI/Starlette + uvicorn, or aiohttp)?
   - *Why it matters*: This choice sets the concurrency model, the shape of the connection handler, the dependency list, how updates reach both players (R4), and whether the server needs one process and port or two.
   - *Default if unanswered*: WebSockets on **aiohttp**, with one process serving the static client, a JSON game-directory endpoint, and a `/ws` WebSocket endpoint. Every connection gets its own asyncio task, so a slow client cannot block the others (R1).

2. **Session joining**: How do two players find each other? Options are a lobby that lists open sessions for each game, a shareable session code or link (`/#/othello/AB12`), automatic pairing with the next waiting player, or a combination.
   - *Why it matters*: This decides the session registry design, which lobby messages the server sends (a live-updating list or a one-off lookup), and which views the client needs.
   - *Default if unanswered*: Both a lobby and a code. A player creates a session and gets a short code. The lobby for each game lists open sessions live, and a player joins by clicking one or opening the code link. A session starts once enough players have joined.

3. **Disconnects and session lifecycle**: If a player drops mid-game, should the server hold the seat for reconnection (and for how long), declare a forfeit, or end the session? And once a game finishes, can the players start a rematch, or does the session close?
   - *Why it matters*: Holding seats needs a reconnect token per seat, a timeout, and a "paused" session state. Forfeit or abandon is much simpler. A rematch changes whether a session is one game or a series.
   - *Default if unanswered*: The seat is held for **60 seconds**. The client keeps a seat token in `sessionStorage` and uses it to reconnect automatically. When the timeout expires, the opponent wins by forfeit. A finished session offers a "Rematch" button that resets the board with colors swapped. Otherwise the session is removed once both players leave.

4. **Message protocol**: Should messages be a generic JSON envelope (`{type, session_id, payload}`) where only `payload` is game-specific? Does the server send the full state after every move, or only diffs? Should the server compute and send the list of legal moves, so the client never needs to know the rules? And do we version the protocol now?
   - *Why it matters*: This sets the boundary between the core and the games (R2/R3). If the server sends legal moves, each new game needs only a renderer and no rules on the client. Diffs and versioning add complexity that may not be worth it at this scale.
   - *Default if unanswered*: A generic envelope with a small fixed set of core message types (`list_games`, `create`, `join`, `move`, `leave`, `state`, `error`). The server sends a **full state snapshot** after every change, including `legal_moves`, `current_player`, `scores`, `status`, and `winner`, produced by the game module. Each message carries a `"v": 1` field, but there is no negotiation.

5. **Client technology**: Should the client be plain HTML/CSS/JS (ES modules, no build step) served as static files, or use a framework such as React or Svelte with a bundler?
   - *Why it matters*: A build step brings a Node toolchain into a Python project. It also decides how each game's view is plugged into the client: a per-game JS module, or components.
   - *Default if unanswered*: Plain HTML/CSS/vanilla JS with ES modules and no build step. Each game has its own renderer module (`static/games/othello.js`) that a small client core loads by game id.

6. **Same-device play (hot-seat)**: Should two players sharing one browser be supported, or is it always one client per player?
   - *Why it matters*: With hot-seat, one connection controls both seats, so the server must allow that and the client must change its "whose turn / is it me" logic. Without it, every seat maps to exactly one connection.
   - *Default if unanswered*: **One client per player** in v1. Two players on the same machine can still use two browser tabs. Hot-seat is left as a possible later feature.

7. **Python version, tooling, and testing**: Which Python version should we target, and which project and dependency tool (`uv`, `pip` + `venv`, Poetry)? Do we want only unit tests for the game logic, or also integration tests that drive the server over WebSockets, and automated browser tests for the client?
   - *Why it matters*: This decides the project layout (`pyproject.toml`, `src/` layout), which language features are available (`match`, `TaskGroup`, newer typing), and how much test infrastructure the Plan has to include.
   - *Default if unanswered*: **Python 3.12+**, managed with **uv** through a `pyproject.toml` with a `src/gamer/` layout, `pytest` + `pytest-asyncio`, `ruff` for linting and formatting, and full type hints. Tests cover the Othello logic with unit tests and the server with in-process WebSocket integration tests (two simulated clients playing a game). No browser tests in v1. The client is checked by hand.
