# Design — Module Dependencies

Allowed import directions inside `src/gamer/`. An arrow means "imports".
Game packages depend only on `games/base.py`. Nothing in the core imports a
concrete game except the registry.

```mermaid
flowchart TD
    app["app.py"]
    protocol["protocol.py"]
    sessions["sessions.py"]
    registry["games/__init__.py<br/>(REGISTRY)"]
    base["games/base.py"]
    othello["games/othello/logic.py"]
    stub["tests/stub_game<br/>(test only)"]
    tests["tests/*"]

    app --> protocol
    app --> sessions
    app --> registry
    app --> base
    sessions --> base
    protocol --> base
    registry --> othello
    othello --> base
    stub --> base
    tests --> app
    tests --> othello
    tests --> stub

    classDef core fill:#e8f0fe,stroke:#4a6fa5
    classDef game fill:#e6f4ea,stroke:#3c8d5a
    classDef test fill:#f5f5f5,stroke:#999,stroke-dasharray: 4 3
    class app,protocol,sessions,registry,base core
    class othello game
    class stub,tests test
```

## Forbidden edges
- `sessions.py` or `app.py` → `games/othello/*` (game-specific code in the core)
- `games/othello/logic.py` → FastAPI, asyncio, or `sessions.py` (logic must
  stay pure, `SPEC.md:29`)
- Production `REGISTRY` → `tests/stub_game`
