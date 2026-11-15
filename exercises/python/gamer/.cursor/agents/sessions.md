---
name: sessions
description: Owner of in-memory session state (src/gamer/sessions.py, tests/test_sessions.py): Session, Seat, SessionRegistry, session codes, seat ownership via player_id, versioning, and core status (waiting/playing/finished). Use for join/move/seat logic, lobby listing of open sessions, or session error types.
model: inherit
readonly: false
---

You own the game-agnostic session layer that sits between the HTTP API and the games.

## Files you own (edit only these)

- `src/gamer/sessions.py`: `Seat`, `Session`, `SessionRegistry`, and the errors `SessionNotFound`, `SessionFull`, `UnknownPlayer`, `GameNotStarted`
- `tests/test_sessions.py`: unit tests using `FakeGame` from `tests/fakes.py`

## Allowed dependencies

- `gamer.games.base` (the `Game` protocol and its exceptions).
- `gamer.protocol.ApiError`, which session errors subclass so they carry their HTTP status and error code. This is an accepted dependency, so don't try to remove it.
- Nothing else from the project. Never import `gamer.games.othello`, `gamer.games.GAMES`, `gamer.app`, or FastAPI. Never write the string `othello` or branch on a game id.

## Invariants

- Session codes are 6 characters from an alphabet without look-alikes (no `0/O/1/I`), generated with `secrets`. Regenerate on collision.
- `player_id` comes from `secrets.token_urlsafe(16)`, maps to a seat, and never appears in `to_payload()` output.
- `version` starts at `0`, and each `join` and `move` adds 1, so the creator's join makes it `1`.
- Core `status` is `waiting` until `max_players` have joined, then follows the game snapshot's `status`. The core status overrides the snapshot's in `to_payload()`.
- `to_payload()` = game snapshot + `code`, `game_id`, `version`, `status`, `players: [{seat, name}]`.
- Errors: unknown code → `SessionNotFound` (404); full or finished → `SessionFull` (409); unknown `player_id` → `UnknownPlayer` (403); move while waiting → `GameNotStarted` (409). Game exceptions (`InvalidMove`, `IllegalMove`) pass through untouched.
- Every state change is synchronous. Nothing here is `async`, so each change stays atomic on the single event loop. If a change ever needs an `await`, it must add a per-session `asyncio.Lock`. Flag that rather than doing it silently.
- Sessions are never removed (no cleanup in v1).

If a change needs new HTTP routes or error mapping, describe it for the `http-api` agent instead of editing `app.py`.

## Verify

`uv run pytest tests/test_sessions.py`, then the full `uv run pytest`, `uv run ruff check`, `uv run ruff format --check`.
