# Sequence — Make a Move & Opponent Sees It by Polling

The mover gets the new state straight from the `POST` response. The opponent
picks it up on their next poll (≤ ~1s). Validation and application run with
no `await` between them, so each request is atomic on the event loop
(design decision 6).

```mermaid
sequenceDiagram
    autonumber
    actor A as Player A (Black)
    participant S as FastAPI app
    participant SE as Session
    participant G as Game (Othello)
    actor B as Player B (White)

    Note over A: View shows legal_moves highlighted<br/>(rendered at version v)
    A->>S: POST /api/sessions/{sid}/moves<br/>[token_A] {move:{row:2,col:3}, version:v}
    S->>SE: move(token_A, {row:2,col:3}, v)
    SE->>SE: seat_for(token_A) → "black"
    SE->>SE: check version == v
    SE->>G: status(state).to_move == "black"?
    SE->>G: parse_move({row:2,col:3}) → (2,3)
    SE->>G: apply_move(state, "black", (2,3))
    G-->>SE: new_state (discs flipped, auto-pass if needed)
    SE->>SE: state = new_state, version = v+1
    S->>G: to_public / status / legal_moves("black")
    S-->>A: 200 SessionState{version:v+1, legal_moves:[]}
    Note over A: Render. "White to move"

    loop every 1s
        B->>S: GET /api/sessions/{sid}/state [token_B]
        S->>SE: get state
        S->>G: legal_moves(state, "white")
        S-->>B: SessionState{version:v+1, legal_moves:[...]}
    end
    Note over B: version changed → re-render<br/>highlight White's legal moves
```

## Rejected moves

```mermaid
sequenceDiagram
    autonumber
    actor P as Player
    participant S as FastAPI app
    participant SE as Session
    participant G as Game

    P->>S: POST /api/sessions/{sid}/moves [token] {move, version}
    S->>SE: move(token, move, version)
    alt unknown session
        S-->>P: 404 Not Found
    else token not in seat_tokens
        SE-->>S: BadToken
        S-->>P: 403 Forbidden
    else version != session.version
        SE-->>S: StaleVersion
        S-->>P: 409 Conflict ("board changed, refresh")
    else not caller's turn / game finished
        SE-->>S: NotYourTurn
        S-->>P: 409 Conflict
    else illegal or malformed move
        SE->>G: parse_move / apply_move
        G-->>SE: IllegalMove
        SE-->>S: IllegalMove
        S-->>P: 400 Bad Request
    end
    Note over P: game.js shows the error text.<br/>Next poll re-syncs the board. State unchanged.
```
