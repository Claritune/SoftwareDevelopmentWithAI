# Code review — Gamer (phases 1–4)

Scope: the four commits on `main` ahead of `origin/main` (`b78a52d` through `497993c`). Server rules, sessions, and HTTP behavior match the spec and the design. The findings below are client and test gaps. Reload losing a seat is intentional (no reconnect), not a defect.

## Medium

### 1. A late poll can paint an older snapshot

`show` in `src/gamer/static/js/app.js` treats any version other than the last one as newer:

```210:218:src/gamer/static/js/app.js
  const show = (state) => {
    if (state.version === lastVersion) return;
    lastVersion = state.version;
    status.textContent = describe(state, mine.seat);
    result.replaceChildren(...(state.status === "finished"
      ? [el("p", { class: "result" }, describe(state, mine.seat))]
      : []));
    renderer.render(board, state, { mySeat: mine.seat, onMove });
  };
```

Polls do not overlap with each other, but a `GET /api/sessions/{code}` already in flight does overlap the move `POST`. If the POST response is applied first and the older GET arrives after it, the board, status, and result banner rewind. Polling then continues, because the stop check uses the fetched body, not the version on screen.

On this server the window is small: handlers do not `await` between read and write, so the earlier request usually finishes first. It gets real as soon as a handler yields, and it is already possible if the two responses reorder. The bad case is an auto-pass. The rewound board is still your turn, so a second click is a real extra move, not a 409.

`lastVersion` should ignore a snapshot whose version is less than or equal to the one already shown. There is no browser test for this; the design explicitly skips those.

### 2. Lobby actions can take more than one seat

Create and Join in `showLobby` (`src/gamer/static/js/app.js`) do not ignore a second click while a request is in flight. The game view's `sending` flag does not cover the lobby.

- Double-clicking **Create session** creates two sessions and navigates to the last one. The first stays in the lobby forever (sessions are never removed).
- Clicking **Join** on two different rows can take a seat in both. The hash ends on one session. The other is `playing` with a player who will never move, and the opponent waits indefinitely.

Create checks `routeToken` before changing the hash. Join does not, so a late join also pulls you back into that session after you have navigated away.

## Low

### 3. A failed link-join removes the form

The share-link path in `showGame` catches every error and replaces the whole view with a single paragraph (`src/gamer/static/js/app.js`, the `nameForm("Join", ...)` handler). "Session full" and "Session not found" match the design. Any other failure (network, 500) does the same, so there is no input left to retry without reloading. `nameForm` already renders `err.message` into the form; this inner `catch` never lets that run.

### 4. Poll errors are silent

`poll` swallows every rejection and retries (`src/gamer/static/js/app.js`). The game view stays blank until the first successful `GET`, and a 404 after a server restart (in-memory sessions are gone) looks the same as a slow load. Nothing tells you the session is gone.

### 5. Polling GETs do not opt out of caching

`no_cache_static` in `src/gamer/app.py` sets `Cache-Control: no-cache` only when the path does **not** start with `/api/`. `src/gamer/static/js/api.js` uses default `fetch` for `GET /api/sessions/{code}` and the lobby list. Chrome will usually refetch these (no `Last-Modified`, so no heuristic freshness). A cache that does reuse them will pin the board or the lobby on an old snapshot, which breaks the one-second update the client is built around. `cache: "no-store"` on those GETs, or `no-store` on `/api/`, closes it.

### 6. The board is wider than a phone

`.othello-board` is `repeat(8, 48px)` plus gaps (`src/gamer/static/style.css`), about 406px. `main` is padded and capped at 640px, so a ~320px viewport scrolls sideways. Lobby controls are a non-wrapping flex row, so the name field and Create button overflow the same way.

### 7. The full-game test allows an early finish

`test_self_play_invariants` and `test_two_players_finish_othello` stop as soon as `current` is `None` / `status == "finished"`, then check the winner against the scores. A regression that ended the game on ply 1 would still pass. The per-move disc-count invariant is the part that actually pins the rules. Neither test asserts that play continued until neither side had a move, or that the API game reached a full terminal count.

## Not defects

- **Reload drops `player_id`.** The seat map is memory-only on purpose. A refresh mid-game cannot rejoin a full session.
- **No locks.** Handlers mutate session state with no `await` in between, which is the documented single-loop model.
- **Othello rules.** Start position, flips, auto-pass, game over, draw, and "move after finish" match the spec and are covered in `tests/games/test_othello.py`.
- **Seat 0 on create** is hardcoded in `joined(...)` because `SessionRegistry.create` always joins an empty session. Correct today; the index returned by `join` is discarded.
