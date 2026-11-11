# Architecture Diagram

Companion to `design.md`. Shows runtime components and the boundaries between them.

## Runtime Components

One `uv run gamer` process serves both the static client and the JSON API. All state lives in memory on a single asyncio event loop (Design Decisions 2, 3).

```mermaid
flowchart LR
    subgraph Browser["Browser (one tab per player)"]
        direction TB
        Router["app.js<br/>hash router + 1s polling loop"]
        Api["api.js<br/>fetch + v:1 envelope"]
        Renderer["games/othello.js<br/>render(container, state, opts)"]
        Router --> Api
        Router -->|"dynamic import by game id"| Renderer
    end

    subgraph Server["gamer process (uvicorn, single event loop)"]
        direction TB
        Static["StaticFiles<br/>/static, /"]
        Routes["FastAPI routes<br/>/api/..."]
        Errors["Exception handler<br/>domain errors to error envelope"]
        Registry["SessionRegistry<br/>code to Session"]
        Session["Session<br/>seats, version, state"]
        GamesMap["GAMES mapping<br/>id to Game"]
        Othello["othello.Game<br/>pure rules"]

        Routes --> Registry
        Routes --> GamesMap
        Registry --> Session
        Session -->|"apply_move / snapshot"| Othello
        GamesMap --> Othello
        Routes -.raises.-> Errors
    end

    Browser -->|"GET html, js"| Static
    Api -->|"GET / POST JSON"| Routes
```

## Trust and Responsibility Boundaries

```mermaid
flowchart TB
    subgraph Client["Client: untrusted, rule-free"]
        C1["Renders snapshot"]
        C2["Turns a click into a move payload"]
        C3["Holds player_id in memory only"]
    end

    subgraph Core["Server core: game-agnostic"]
        S1["Envelope validation, v == 1"]
        S2["player_id to seat mapping"]
        S3["Session lifecycle: waiting, playing, finished"]
        S4["version counter, lobby listing"]
    end

    subgraph Game["Game module: pure, no I/O"]
        G1["parse_move, apply_move"]
        G2["Legality, turn order, auto-pass"]
        G3["snapshot: board, legal_moves, scores, winner"]
    end

    Client -- "move payload (opaque to core)" --> Core
    Core -- "seat index + parsed move" --> Game
    Game -- "new State or IllegalMove" --> Core
    Core -- "core fields + game snapshot" --> Client
```

Rules that follow from these boundaries:

- The client never decides whether a move is legal. It only highlights `legal_moves` from the snapshot.
- The core never inspects `board` or the move payload, and never imports a specific game.
- The game never sees names or `player_id`s, only seat indexes.
