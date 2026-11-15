# Gamer (C++)

A local turn-based game server for multiplayer games (v1: Othello) with a
browser client. This is a C++20 port of `demos/python/gamer`. The HTTP API,
the JSON shapes and the HTML/JS client are the same.

## Build and run

You need CMake 3.24 or newer and a C++20 compiler (Clang, GCC or MSVC 2022).
CMake downloads the dependencies when you configure:
[cpp-httplib](https://github.com/yhirose/cpp-httplib),
[nlohmann/json](https://github.com/nlohmann/json) and GoogleTest.

macOS / Linux:

```sh
cmake -S . -B build
cmake --build build -j
ctest --test-dir build --output-on-failure
./build/gamer                  # http://127.0.0.1:8000
```

Windows (Developer PowerShell):

```powershell
cmake -S . -B build
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
.\build\Release\gamer.exe
```

Options: `gamer --host 0.0.0.0 --port 9000`. Static files are served from the
source tree, so run the binary from a checkout.

## Layout

| Path | Role |
|---|---|
| `src/gamer/game.h` | Game interface: the `GameRules` concept (typed rules) and the type-erased `Game` the core uses |
| `src/gamer/games/othello/` | Othello rules plus its `static/view.js` |
| `src/gamer/games/registry.cpp` | The game directory. Register a new game here |
| `src/gamer/sessions.*` | Sessions, seats, tokens, versioning, move validation |
| `src/gamer/protocol.*` | JSON shapes of the API |
| `src/gamer/app.*` | HTTP routes, error mapping, static mounts |
| `src/gamer/static/` | Browser client (copied unchanged from the Python version) |
| `tests/` | GoogleTest suite. `stub_game/` proves that adding a game doesn't touch the core |

## API

| Method | Path | Result |
|---|---|---|
| GET | `/api/games` | `[{id, name}]` |
| GET | `/api/games/{game_id}/sessions` | open (waiting) sessions |
| POST | `/api/games/{game_id}/sessions` | 201 `{session_id, seat, token}` |
| POST | `/api/sessions/{id}/join` | `{session_id, seat, token}`, or 409 if full |
| GET | `/api/sessions/{id}/state` | session state (`X-Player-Token` optional) |
| POST | `/api/sessions/{id}/moves` | body `{move, version}`, returns the new state |

Errors return `{"detail": ...}`:

| Status | Cause |
|---|---|
| 400 | Illegal move |
| 403 | Bad or missing token |
| 404 | Unknown game or session |
| 409 | Session full, stale version, or not your turn |
| 422 | Malformed body |

## Adding a game

1. Write a class that satisfies `gamer::GameRules`. Look at
   `tests/stub_game/` for a minimal example.
2. Add its `static/view.js` that exports `render(container, publicState, legalMoves, onMove)`.
3. Add `make_game(MyGame{})` to `default_registry()`, and add the `.cpp` to `CMakeLists.txt`.

## Differences from the Python version

- **Threads instead of an event loop.** httplib handles each connection on a
  worker thread, so a slow client only ties up its own thread. One mutex in
  `App` serialises all session access, which matches the Python version's
  single-threaded behaviour. Handlers hold it only while computing, never
  during network I/O.
- `tests/test_concurrency.cpp` is new. It plays several games in parallel and
  races joins against one session.
