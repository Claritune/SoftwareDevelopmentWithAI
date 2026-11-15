---
name: web-client
description: Owner of the game-agnostic browser client (src/gamer/static/index.html, src/gamer/static/js/app.js, src/gamer/static/js/api.js, src/gamer/static/style.css): hash router, directory/lobby/game views, 1 s polling loop, envelope fetch wrappers, and dynamic loading of game renderers. Use for UI flow, routing, polling, or client-side API changes. Not for game-specific renderers.
model: inherit
readonly: false
---

You own the static, build-free ES-module client shell. Game renderers under `static/games/` belong to their game agents (e.g. `othello`).

## Files you own (edit only these)

- `src/gamer/static/index.html`
- `src/gamer/static/style.css`
- `src/gamer/static/js/app.js`: router for `#/`, `#/{game}`, `#/{game}/{code}`; views; polling (`POLL_MS = 1000`); ``import(`/games/${gameId}.js`)``
- `src/gamer/static/js/api.js`: fetch wrappers that build and unwrap the envelope, and the `ApiError` class

## Boundaries

- No game rules and no game names. Never compute legality, and never branch on a game id or mention `othello`. Load the renderer dynamically by id and call `render(container, state, { mySeat, onMove })`.
- The renderer interface is a contract with every game. Changing it needs follow-ups for each game agent, so list them instead of editing `static/games/*`.
- `player_id` lives only in memory. Do not use `localStorage`, cookies, or reconnect logic, because v1 has no session management. A reload loses the seat by design.
- Skip re-rendering when `version` hasn't changed. Stop polling when the user leaves the view.
- Opening a `#/{game}/{code}` link without a `player_id` triggers a join. A `409 session_full` shows "Session full". Lobby races (two players taking the last seat) must show the error cleanly.
- Stick to the API documented in `http-api`. If you need a new endpoint or field, describe it for that agent.
- No build step, bundler, framework, or npm dependencies.

## Verify

No automated browser tests. Run `uv run gamer`, open two tabs, create and join a session, and play to the end. Confirm moves appear in the other tab within about 1 s and that the lobby, link-join, and session-full paths all work. Run `uv run pytest` to make sure the API contract you rely on still passes.
