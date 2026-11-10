# Answers

The user accepted all defaults from `questions.md`.

1. **Transport & server stack**: FastAPI + Uvicorn. One process serves the
   static HTML client and a WebSocket endpoint, all on asyncio.
   *(Revised: polling instead of WebSockets. See Revisions below.)*
2. **Session discovery & joining**: A lobby plus shareable links. The directory
   shows the games, each game page lists open sessions with a "Create" button,
   and every session has a shareable URL.
3. **Disconnects & session lifecycle**: The server gives each player a random
   token stored in `localStorage`. Reconnecting with the token within the
   server's lifetime reclaims the seat. The opponent sees "waiting for
   opponent". A session is removed when both players leave or the game ends.
   *(Revised: no presence tracking or cleanup in v1. See Revisions below.)*
4. **Game module interface boundary**: Each game is a package
   (`games/othello/`) with pure-Python logic (`init_state`, `legal_moves`,
   `apply_move`, `status`) and its own static view (`othello.js`). The server
   includes legal moves in every state update so the client can highlight them
   without knowing the rules.
5. **Client technology**: Vanilla HTML/CSS/JS ES modules, no build step, served
   by the Python server.
6. **Hot-seat play**: Not supported in v1. One client per seat. Two tabs on
   the same machine work for local testing.
7. **Python tooling & testing**: Python 3.12, `uv`, `pytest`. Full unit
   coverage of Othello logic, plus integration tests for the session flow
   (create, join, move, game over) using FastAPI's test client.

## Revisions

- **2026-11-10, answer 1 (Transport)**: During design review the user chose
  **no WebSockets**. Clients poll the server periodically over plain HTTP
  (game view ~1s, lobby ~2s). FastAPI + Uvicorn stays as the server stack.
  See `design.md` decisions 1, 5, 6, 7.
- **2026-11-10, answer 3 (Disconnects & lifecycle)**: The user chose
  **stateless client connections for now**. The server does not track
  presence or detect disconnects, and does not clean up abandoned sessions.
  The token still identifies a seat, so reopening the URL reclaims it.
  Disconnect handling and cleanup are deferred to a separate follow-up. See
  `design.md` decisions 7, 8.
- **2026-11-10, answer 3 (token storage)**: During planning the user chose
  **`sessionStorage` instead of `localStorage`**. `localStorage` is shared by
  every tab in a browser, so a second tab would take over the first tab's
  seat and break two-tab local testing (answer 6). With `sessionStorage`, a
  refresh keeps the seat and closing the tab gives it up. See `design.md`
  decision 7.
