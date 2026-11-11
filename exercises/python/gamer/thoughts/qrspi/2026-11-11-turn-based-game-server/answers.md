# Answers

1. **Transport and server framework**: HTTP with polling, no WebSockets. Clients poll the server for session state. The HTTP framework was not specified and is left to the Design phase.
2. **Session joining**: Both. There is a live lobby of open sessions for each game, plus a shareable session code or link.
3. **Disconnects and session lifecycle**: No session management. If a player goes away, the session waits indefinitely for their next move. There are no reconnect tokens, timeouts, forfeits, or session cleanup. A rematch was not requested.
4. **Message protocol**: A generic JSON envelope where only the payload is game-specific. The server returns a full state snapshot (including `legal_moves`, `current_player`, `scores`, `status`, `winner`, all produced by the game module) and every message carries a `"v": 1` field.
5. **Client technology**: Plain HTML/CSS/vanilla JS with ES modules and no build step. Each game has its own renderer module.
6. **Same-device play (hot-seat)**: Not supported. There is one client per player, though two browser tabs on the same machine still work.
7. **Python version, tooling, and testing**: Python 3.12+, uv, `pyproject.toml` with a `src/gamer/` layout, `pytest` + `pytest-asyncio`, and `ruff`. Tests are unit tests for the game logic plus in-process integration tests for the server. Because of answer 1, the integration tests use the HTTP API rather than WebSockets. There are no browser tests.
