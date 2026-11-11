# Task

Build "Gamer", a local-only Python server that hosts real-time, turn-based multiplayer games, with a browser-based HTML client. Players pick a game from a directory, start or join a session, and play against each other. The server is the authority on game state and checks every move. Game rules live in pluggable modules behind a common interface, so new games can be added without changing the server core. Version 1 ships one game, Othello. There are no accounts or authentication, and nothing is persisted.

Source: `SPEC.md`
