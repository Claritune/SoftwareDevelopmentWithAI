# Sequence — Refresh Reclaims the Seat

The server keeps no per-client state, so "reconnecting" is just polling
again with the token in `sessionStorage`. That store is per tab: it survives
a refresh, but closing the tab loses the token and the seat. The server cannot
see that the tab was refreshed or closed, and the opponent sees no change (design decision 7).

```mermaid
sequenceDiagram
    autonumber
    actor A as Player A (browser)
    participant LS as sessionStorage
    participant S as FastAPI app
    participant SE as Session

    Note over A: Tab refreshed mid-game.<br/>The server notices nothing.
    A->>S: GET /games/othello/sessions/{sid}
    S-->>A: game.html (+ view.js)
    A->>LS: getToken(sid)
    alt token found
        LS-->>A: token_A
        A->>S: GET /api/sessions/{sid}/state [X-Player-Token: token_A]
        S->>SE: seat_for(token_A)
        SE-->>S: "black"
        S-->>A: SessionState{your_seat:"black", legal_moves:[...]}
        Note over A: Resume polling as Black
    else no token, session waiting
        LS-->>A: null
        A->>S: POST /api/sessions/{sid}/join
        S-->>A: {seat, token} → setToken
    else no token, session full
        LS-->>A: null
        A->>S: GET /api/sessions/{sid}/state (no token)
        S-->>A: SessionState{your_seat:null}
        Note over A: Show "Session full"
    end

    Note over A,S: Each tab has its own sessionStorage, so two tabs<br/>in one browser can hold Black and White.
```
