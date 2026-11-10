# Gamer — Turn-Based Game Server

## Goal

Build a simple game server in Python that hosts interactive, turn-based,
multiplayer games (Othello, and others later). Players connect through an HTML
client, pick a game from the server's game directory, and play against each
other in real time.

## Requirements

### R1. Multi-client server
- The server accepts connections from multiple clients at the same time.
- Each connected client is handled independently. One slow or disconnected
  client must not block the others.

### R2. Game directory
- The server offers a list of available games.
- Version 1 offers one game: **Othello**.
- Adding a game later must not require changes to the server core, only a new
  game module plus its registration.

### R3. Pluggable game logic
- Each game lives in its own logic module.
- A game module owns its rules: initial state, legal moves, applying a move,
  whose turn it is, and detecting game over and the winner.
- The server core does not know the rules of any game. It talks to games
  through a common interface.
- Game logic can be unit tested without a running server or client.

### R4. Concurrent multiplayer sessions
- Multiple players can play at once, each through their own client.
- The server can run several game sessions in parallel (for example, several
  Othello matches between different pairs of players).
- The server is the source of truth for game state and validates every move.
  Clients cannot make illegal moves or move out of turn.
- After every move, all players in the session see the updated state.

### R5. HTML client
- A browser-based client provides:
  - a **game directory** view listing the games the server offers, and
  - a **game view** for each game (v1: an Othello board).
- From the client a player can pick a game, start or join a session, make
  moves, and see the opponent's moves as they happen.
- The client shows whose turn it is, the score or status, and the result when
  the game ends.

### R6. Local-only, no authentication (v1)
- Everything runs locally (server and clients on the same machine or local
  network).
- No user accounts, login, or authentication. A player is identified by a
  display name or a session-assigned id.

## Othello (v1 game)

- Standard 8×8 board, standard starting position (four discs in the center).
- Two players: Black moves first, then White.
- A move is legal only if it flips at least one opposing disc.
- If a player has no legal move, their turn is passed.
- The game ends when neither player can move. The player with more discs wins;
  equal counts is a draw.

## Out of Scope (v1)

- Authentication, accounts, and persistent user profiles
- Deployment beyond localhost or the local network
- Persisting games across server restarts
- AI or computer opponents
- Spectators, chat, matchmaking, rankings
- Games other than Othello

## Open Questions (for the QRSPI Questions phase)

1. **Transport**: WebSockets for real-time push, or HTTP with polling?
2. **Server framework**: plain `asyncio` + `websockets`, or a framework such as
   FastAPI / aiohttp that also serves the HTML client?
3. **Session joining**: how do two players find each other? Options include a
   lobby list of open sessions, a shareable session code or link, or automatic
   pairing.
4. **Disconnects**: if a player drops mid-game, should the session be held open
   for reconnection, forfeited, or abandoned?
5. **Client tech**: plain HTML/CSS/JS with no build step, or a framework?
6. **Message protocol**: the shape of client↔server messages (JSON schema,
   versioning), and how much of it is generic versus game-specific.
7. **Same-device play**: should two players sharing one browser (hot-seat) be
   supported, or always one client per player?

## Process

This project follows the QRSPI methodology (Questions → Research → Design →
Structure → Plan → Worktree → Implement → PR). Phase skills are in
[`docs/skills/`](docs/skills/). Phase artifacts go under
`thoughts/qrspi/<id>/`.

Since this is a greenfield project, the Research phase is skipped. The
Questions phase produces clarifying questions and answers, and then the
Design phase follows.
