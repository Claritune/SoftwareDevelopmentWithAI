# Design — Domain Model & Game Interface

Core types from `structure.md`. `Game` is a `typing.Protocol`, and game
states are immutable (frozen dataclasses).

```mermaid
classDiagram
    direction LR

    class Game {
        <<Protocol>>
        +id: str
        +name: str
        +seats: tuple[Seat, ...]
        +static_dir: Path
        +initial_state() S
        +legal_moves(state: S, seat: Seat) list[M]
        +apply_move(state: S, seat: Seat, move: M) S
        +status(state: S) GameStatus
        +to_public(state: S) dict
        +parse_move(raw: dict) M
        +move_to_public(move: M) dict
    }

    class GameStatus {
        <<frozen>>
        +to_move: Seat | None
        +finished: bool
        +winner: Seat | None
        +scores: dict[Seat, int]
    }

    class IllegalMove {
        <<exception>>
    }

    class Othello {
        +id = "othello"
        +seats = ("black", "white")
    }

    class OthelloState {
        <<frozen>>
        +board: tuple[tuple[str, ...], ...]
        +to_move: Seat | None
    }

    class Session {
        +id: str
        +game: Game
        +state: S
        +version: int
        +seat_tokens: dict[str, Seat]
        +lifecycle() Lifecycle
        +seat_for(token) Seat | None
        +join() tuple[Seat, str]
        +move(token, raw_move: dict, version: int) None
    }

    class SessionManager {
        -sessions: dict[str, Session]
        -registry: dict[str, Game]
        +create(game_id) tuple[Session, Seat, str]
        +get(session_id) Session
        +list_open(game_id) list[Session]
    }

    class SessionErrors {
        <<exceptions>>
        SessionFull
        SessionNotFound
        BadToken
        StaleVersion
        NotYourTurn
    }

    Othello ..|> Game : implements
    Othello ..> OthelloState : creates / returns
    Game ..> GameStatus : returns
    Game ..> IllegalMove : raises
    SessionManager "1" o-- "*" Session
    SessionManager ..> Game : looks up in registry
    Session --> Game : delegates rules
    Session ..> SessionErrors : raises
```

## API models (`protocol.py`)

```mermaid
classDiagram
    direction LR
    class GameInfo {
        +id: str
        +name: str
    }
    class SessionSummary {
        +session_id: str
        +game_id: str
    }
    class SeatAssignment {
        +session_id: str
        +seat: Seat
        +token: str
    }
    class MoveRequest {
        +move: dict
        +version: int
    }
    class SessionState {
        +session_id: str
        +game_id: str
        +version: int
        +lifecycle: Lifecycle
        +public_state: dict
        +status: GameStatus
        +legal_moves: list[dict]
        +seats: dict[Seat, bool]
        +your_seat: Seat | None
    }
```

## HTTP endpoints

| Method & path | Request | Response | Errors |
|---|---|---|---|
| `GET /api/games` | none | `list[GameInfo]` | none |
| `GET /api/games/{game}/sessions` | none | `list[SessionSummary]` (waiting only) | 404 game |
| `POST /api/games/{game}/sessions` | none | `SeatAssignment` | 404 game |
| `POST /api/sessions/{id}/join` | none | `SeatAssignment` | 404, 409 full |
| `GET /api/sessions/{id}/state` | optional token | `SessionState` | 403, 404 |
| `POST /api/sessions/{id}/moves` | token + `MoveRequest` | `SessionState` | 400, 403, 404, 409 |
