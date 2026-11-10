# Architecture — Components & Runtime

One local process (FastAPI + Uvicorn on `127.0.0.1:8000`) serves the static
client and the JSON API. Browsers poll it over plain HTTP. There are no
WebSockets, and the server keeps no per-client state (design decisions 1, 5,
6, 7).

```mermaid
flowchart LR
    subgraph Browser["Browser (one per player)"]
        direction TB
        IDX["index.html / index.js<br/>Game directory"]
        LOB["lobby.html / lobby.js<br/>Open sessions, polls every 2s"]
        GAME["game.html / game.js<br/>Poll loop every 1s, sends moves"]
        COMMON["common.js<br/>api(), getToken/setToken, poll()"]
        VIEW["games/othello/static/view.js<br/>render(container, state, legalMoves, onMove)"]
        LS[("sessionStorage (per tab)<br/>{session_id: token}")]
        IDX --> COMMON
        LOB --> COMMON
        GAME --> COMMON
        GAME -- "dynamic import()" --> VIEW
        COMMON <--> LS
    end

    subgraph Server["Python process: FastAPI + Uvicorn (single asyncio loop)"]
        direction TB
        APP["app.py: create_app(registry)<br/>page routes, /api routes, static mounts"]
        PROTO["protocol.py<br/>pydantic request/response models"]
        SM["sessions.py<br/>SessionManager → Session (in memory)"]
        REG["games/__init__.py<br/>REGISTRY: dict[str, Game]"]
        BASE["games/base.py<br/>Game protocol, GameStatus, IllegalMove"]
        OTH["games/othello/logic.py<br/>pure rules, OTHELLO"]
        STATIC[["static/ and games/*/static/<br/>HTML / JS / CSS files"]]
        APP --> PROTO
        APP --> SM
        APP --> REG
        SM -- "via Game protocol only" --> BASE
        REG --> OTH
        OTH -. implements .-> BASE
        APP -- StaticFiles --> STATIC
    end

    COMMON -- "HTTP JSON<br/>X-Player-Token header" --> APP
    Browser -- "GET pages & assets" --> APP
```

## Key properties
- **Rules live only in game modules.** `app.py` and `sessions.py` never
  import `games.othello`. They reach games only through `REGISTRY` and the
  `Game` protocol.
- **The server is the source of truth.** Clients send intentions (moves),
  the server validates and applies them, and clients learn the outcome by
  polling.
- **Stateless clients.** The token maps to a seat and nothing more. The
  server tracks no presence or last-seen time.
- **In-memory only.** Nothing survives a restart, and there is no cleanup
  in v1.
