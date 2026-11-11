# Sequence Diagrams — Main Flows

Companion to `design.md`. Every request and response body uses the `{"v": 1, "type", "payload"}` envelope (Design Decision 9). The diagrams show only the `type` and the key payload fields.

## 1. Browse Directory and Lobby

```mermaid
sequenceDiagram
    actor A as Player A
    participant C as Client A (app.js)
    participant API as FastAPI routes
    participant R as SessionRegistry

    A->>C: open http://127.0.0.1:8000/#/
    C->>API: GET /api/games
    API-->>C: type=games [{id: othello, name: Othello}]
    A->>C: click Othello (#/othello)
    loop every 1s while on the lobby view
        C->>API: GET /api/games/othello/sessions
        API->>R: open_sessions("othello")
        R-->>API: sessions with status waiting
        API-->>C: type=sessions [{code, players}]
    end
```

## 2. Create a Session and Join from the Lobby

```mermaid
sequenceDiagram
    actor A as Player A
    participant CA as Client A
    participant API as FastAPI routes
    participant R as SessionRegistry
    participant S as Session
    participant G as Othello Game
    participant CB as Client B
    actor B as Player B

    A->>CA: enter name "Ann", click Create
    CA->>API: POST /api/games/othello/sessions {name: Ann}
    API->>R: create(othello, "Ann")
    R->>G: initial_state()
    G-->>R: State
    R->>S: new Session(code K7QX2M, seat 0 = Ann)
    R-->>API: Session, Seat(player_id pA)
    API-->>CA: type=joined {code, player_id: pA, seat: 0, state}
    CA->>CA: keep pA in memory, go to #/othello/K7QX2M
    Note over CA: shows "Waiting for opponent", polls state

    B->>CB: lobby lists K7QX2M, click Join as "Bob"
    CB->>API: POST /api/sessions/K7QX2M/join {name: Bob}
    API->>R: get(K7QX2M)
    API->>S: join("Bob")
    S->>S: seat 1 = Bob, version + 1, status = playing
    S-->>API: Seat(player_id pB)
    API-->>CB: type=joined {player_id: pB, seat: 1, state}

    CA->>API: GET /api/sessions/K7QX2M (next poll)
    API-->>CA: type=state {version 1, status playing, current_player 0}
    CA->>CA: version changed, re-render board
```

## 3. Join via a Shared Link

The `#/{game}/{code}` route has no `player_id` in memory, so the client joins first. A full session returns `409`.

```mermaid
sequenceDiagram
    actor B as Player B
    participant CB as Client B
    participant API as FastAPI routes
    participant S as Session

    B->>CB: open /#/othello/K7QX2M
    CB->>CB: no player_id for K7QX2M, ask for name
    CB->>API: POST /api/sessions/K7QX2M/join {name: Bob}
    alt seat free
        API->>S: join("Bob")
        S-->>API: Seat(pB)
        API-->>CB: 200 type=joined {player_id: pB, seat: 1, state}
        CB->>CB: start polling, render game view
    else session full or finished
        API-->>CB: 409 type=error {code: session_full}
        CB->>B: show "Session full"
    else unknown code
        API-->>CB: 404 type=error {code: session_not_found}
        CB->>B: show "Session not found"
    end
```

## 4. Make a Move (Happy Path and Rejections)

```mermaid
sequenceDiagram
    actor A as Player A
    participant CA as Client A
    participant API as FastAPI routes
    participant S as Session
    participant G as Othello Game
    participant CB as Client B

    A->>CA: click a highlighted square (row 2, col 3)
    CA->>API: POST /api/sessions/K7QX2M/moves {player_id: pA, move: {row 2, col 3}}
    API->>S: move(pA, payload)
    S->>S: pA maps to seat 0
    S->>G: parse_move(payload)
    G-->>S: Move(2, 3)
    S->>G: apply_move(state, seat 0, move)
    alt legal and seat 0's turn
        G-->>S: new State
        S->>S: state = new State, version + 1
        S->>G: snapshot(state)
        G-->>S: board, current_player 1, legal_moves, scores, status
        API-->>CA: 200 type=state {version 2, ...}
        CA->>CA: re-render
    else illegal or out of turn
        G-->>S: raise IllegalMove
        API-->>CA: 409 type=error {code: illegal_move}
    else malformed payload
        G-->>S: raise InvalidMove (from parse_move)
        API-->>CA: 400 type=error {code: invalid_move}
    else unknown player_id
        S-->>API: raise UnknownPlayer
        API-->>CA: 403 type=error {code: unknown_player}
    end

    CB->>API: GET /api/sessions/K7QX2M (poll within 1s)
    API-->>CB: type=state {version 2, current_player 1}
    CB->>CB: version changed, re-render, enable Bob's legal moves
```

## 5. Automatic Pass and Game Over (inside the Othello module)

The core sees only a new state and a snapshot. Passing and game end are decided entirely in `apply_move`.

```mermaid
sequenceDiagram
    participant S as Session
    participant G as Othello Game

    S->>G: apply_move(state, seat, move)
    G->>G: place disc, flip lines
    G->>G: does the opponent have legal moves?
    alt opponent can move
        G-->>S: State(current = opponent)
    else opponent cannot move, mover can
        G-->>S: State(current = mover, last_event "White passed")
    else neither can move
        G-->>S: State(current = None)
        Note over S,G: snapshot reports status finished,<br/>winner = seat with more discs, or null for a draw
    end
```

## 6. Polling Loop (client side)

```mermaid
sequenceDiagram
    participant T as setInterval 1s
    participant C as app.js
    participant API as FastAPI routes
    participant V as games/othello.js

    loop while game view is open and status is not finished
        T->>C: tick
        C->>API: GET /api/sessions/{code}
        API-->>C: type=state {version N, ...}
        alt N == last rendered version
            C->>C: skip render
        else N changed
            C->>V: render(container, state, {mySeat, onMove})
        end
    end
    Note over C: stops polling when status is finished,<br/>after showing the result
```
