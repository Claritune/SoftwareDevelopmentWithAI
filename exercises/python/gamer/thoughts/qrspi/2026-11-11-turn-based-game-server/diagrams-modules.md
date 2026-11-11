# Module Diagram

Companion to `design.md`. Shows the planned package layout, the import directions, and the key types. The exact file split is settled in the Structure phase.

## Package Dependencies

Arrows mean "imports". The rule: nothing under `gamer.games` imports from the server core, and the core imports only `gamer.games` (the `GAMES` mapping and `base`), never `othello` directly.

```mermaid
flowchart TB
    main["gamer.__main__<br/>CLI: --host, --port"]
    app["gamer.app<br/>create_app(games, registry)"]
    protocol["gamer.protocol<br/>Envelope, error codes"]
    sessions["gamer.sessions<br/>Session, SessionRegistry"]
    games_init["gamer.games<br/>GAMES mapping"]
    base["gamer.games.base<br/>Game Protocol, InvalidMove, IllegalMove"]
    othello["gamer.games.othello"]
    static["gamer/static/<br/>index.html, js/, games/"]

    main --> app
    app --> protocol
    app --> sessions
    app --> games_init
    app -.serves.-> static
    sessions --> base
    games_init --> othello
    games_init --> base
    othello --> base

    tests_unit["tests/games/test_othello.py"] --> othello
    tests_sessions["tests/test_sessions.py"] --> sessions
    tests_int["tests/test_api.py<br/>uses FakeGame"] --> app
```

## Client Modules

```mermaid
flowchart LR
    index["index.html"] --> appjs["js/app.js<br/>router, views, polling"]
    appjs --> apijs["js/api.js<br/>envelope fetch wrappers"]
    appjs -->|"import('./games/' + id + '.js')"| othellojs["games/othello.js<br/>export render()"]
```

## Key Types

```mermaid
classDiagram
    class Game {
        <<Protocol>>
        +id: str
        +name: str
        +min_players: int
        +max_players: int
        +initial_state() State
        +parse_move(payload: dict) Move
        +apply_move(state, seat: int, move) State
        +snapshot(state) dict
    }

    class OthelloGame {
        +id = "othello"
        +min_players = 2
        +max_players = 2
    }

    class OthelloState {
        <<frozen dataclass>>
        +board: tuple
        +current: Optional~int~
        +last_event: Optional~str~
    }

    class Seat {
        +player_id: str
        +name: str
    }

    class Session {
        +code: str
        +game: Game
        +state: State
        +seats: list~Seat~
        +version: int
        +status() str
        +join(name) Seat
        +move(player_id, payload) None
        +to_payload() dict
    }

    class SessionRegistry {
        -sessions: dict~str, Session~
        +create(game, name) tuple~Session, Seat~
        +get(code) Session
        +open_sessions(game_id) list~Session~
    }

    class InvalidMove {
        <<exception>>
    }
    class IllegalMove {
        <<exception>>
    }

    Game <|.. OthelloGame
    OthelloGame ..> OthelloState
    SessionRegistry "1" o-- "*" Session
    Session "1" *-- "1..max_players" Seat
    Session --> Game
    Game ..> InvalidMove : raises
    Game ..> IllegalMove : raises
```

## Session Status

The status is `waiting` until every seat is filled. After that it follows the game's `snapshot()["status"]`.

```mermaid
stateDiagram-v2
    [*] --> waiting: create (seat 0 taken)
    waiting --> waiting: join (seats still free)
    waiting --> playing: join fills last seat
    playing --> playing: legal move (version + 1)
    playing --> finished: game reports finished
    finished --> [*]: kept in memory forever (no cleanup)
```
