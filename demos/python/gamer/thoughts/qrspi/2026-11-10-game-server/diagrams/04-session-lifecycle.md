# Design — Session Lifecycle

`Session.lifecycle` is derived from seat occupancy and `game.status(state)`.
It is not stored separately. `version` goes up on every transition and on
every applied move (design decision 8).

```mermaid
stateDiagram-v2
    [*] --> waiting : POST /api/games/{game}/sessions<br/>creator takes first seat (Black)<br/>version = 1

    waiting --> waiting : GET .../state (poll)<br/>no change
    waiting --> playing : POST /api/sessions/{id}/join<br/>second seat filled, version++

    playing --> playing : POST .../moves (legal, in turn, current version)<br/>apply_move, version++
    playing --> playing : rejected move<br/>400 / 409, no change
    playing --> finished : POST .../moves<br/>status(state).finished == true, version++

    finished --> finished : GET .../state (poll)<br/>clients stop polling after rendering
    finished --> [*] : server stops<br/>(no cleanup in v1)

    waiting --> [*] : server stops
    playing --> [*] : server stops

    note right of waiting
        Listed in lobby.
        Join returns 409 once full.
    end note
    note right of finished
        Further moves raise NotYourTurn (409).
    end note
```
