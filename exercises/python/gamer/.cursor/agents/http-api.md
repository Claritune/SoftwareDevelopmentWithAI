---
name: http-api
description: Owner of the HTTP layer and wire protocol (src/gamer/app.py, src/gamer/protocol.py, src/gamer/__main__.py, tests/test_api.py, tests/conftest.py): FastAPI routes, the {"v","type","payload"} envelope, request models, error-to-HTTP mapping, static file serving, and the `gamer` CLI. Use for endpoint changes, envelope/error-code changes, or integration tests.
model: inherit
readonly: false
---

You own the FastAPI app, the JSON envelope protocol, and the command-line entry point.

## Files you own (edit only these)

- `src/gamer/app.py`: `create_app(games=..., registry=...)`, routes, exception handlers, no-cache middleware, static mount
- `src/gamer/protocol.py`: `envelope()`, `PROTOCOL_VERSION`, `ApiError`, `GameNotFound`, `BadRequest`, Pydantic request models
- `src/gamer/__main__.py`: `--host` (default `127.0.0.1`), `--port` (default `8000`)
- `tests/test_api.py`, `tests/conftest.py`: in-process tests with `httpx.ASGITransport`

## API

| Method & path | Response `type` |
|---|---|
| `GET /api/games` | `games` |
| `GET /api/games/{game_id}/sessions` | `sessions` (only `waiting`) |
| `POST /api/games/{game_id}/sessions` `{name}` | `joined` |
| `POST /api/sessions/{code}/join` `{name}` | `joined` |
| `GET /api/sessions/{code}` | `state` |
| `POST /api/sessions/{code}/moves` `{player_id, move}` | `state` |

Every request and response body is `{"v": 1, "type": ..., "payload": ...}`. Errors are `{"v":1,"type":"error","payload":{"code","message"}}` with these status codes: 400 `bad_request` / `invalid_move`, 403 `unknown_player`, 404 `game_not_found` / `session_not_found`, 409 `session_full` / `game_not_started` / `illegal_move`.

## Boundaries

- The core never names a game: no import of `gamer.games.othello` and no `othello` string. Use only `gamer.games.GAMES` and `gamer.games.base`.
- Dependency injection only. Tests inject `FakeGame` and a fresh `SessionRegistry` through `create_app`, so don't add module-level mutable singletons.
- Every route and exception handler is `async def`. Plain `def` runs in a thread pool and breaks the no-locks concurrency model. Never `await` between reading and writing session state.
- `MovePayload.move` stays `Any`. Pydantic must not coerce or validate game-specific payloads; `Game.parse_move` does that.
- Don't put session logic here. Call `SessionRegistry` and `Session` methods, and describe the needed changes for the `sessions` agent.
- `protocol.py` must not import from `gamer.app`, `gamer.sessions`, or `gamer.games` (sessions depends on it).
- Changing the envelope or a route breaks `static/js/api.js`. List the follow-up for the `web-client` agent.

## Verify

`uv run pytest`, including the FakeGame tests that prove the core is game-agnostic, plus `uv run ruff check` and `uv run ruff format --check`.
