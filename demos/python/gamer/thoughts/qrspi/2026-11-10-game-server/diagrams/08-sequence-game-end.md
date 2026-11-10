# Sequence — Final Move & Game Over

The last legal move leaves neither side able to move. `status()` reports
`finished`, both clients show the result, and polling stops.

```mermaid
sequenceDiagram
    autonumber
    actor A as Player A (Black)
    participant S as FastAPI app
    participant SE as Session
    participant G as Game (Othello)
    actor B as Player B (White)

    A->>S: POST /api/sessions/{sid}/moves [token_A] {move, version:v}
    S->>SE: move(...)
    SE->>G: apply_move(state, "black", move)
    G-->>SE: new_state (no legal moves for either side)
    SE->>SE: version = v+1
    S->>G: status(new_state)
    G-->>S: GameStatus{finished:true, to_move:null, winner:"black", scores:{black:40, white:24}}
    S-->>A: SessionState{lifecycle:"finished", status:{...}}
    Note over A: Show "Black wins 40–24"<br/>stop poll loop

    B->>S: GET /api/sessions/{sid}/state [token_B]
    S-->>B: SessionState{lifecycle:"finished", version:v+1, winner:"black"}
    Note over B: Show "Black wins 40–24"<br/>stop poll loop

    opt late or duplicate move
        B->>S: POST /api/sessions/{sid}/moves
        S-->>B: 409 Conflict (NotYourTurn, game finished)
    end

    Note over S: Session stays in memory until the server stops (no cleanup in v1)
```

Draw: `winner: null` with equal scores. The UI shows "Draw 32–32".
