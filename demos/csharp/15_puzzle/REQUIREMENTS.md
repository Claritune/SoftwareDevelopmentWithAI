# 15 Puzzle Requirements

## 1. Product Summary

The product is a polished native desktop implementation of the classic 15 puzzle. It uses a fixed 4 x 4 board containing tiles numbered 1 through 15 and one empty cell. The first release targets macOS and is implemented in C# with Avalonia UI.

The player rearranges tiles by sliding them into the empty cell until the tiles are ordered from 1 to 15, with the empty cell in the bottom-right corner.

## 2. Goals

- Provide a responsive, reliable version of the classic 15 puzzle.
- Ensure every generated puzzle is solvable and not already solved.
- Support complete gameplay using either pointer or keyboard input.
- Track elapsed time and move count consistently.
- Preserve local best results between application launches.
- Expose meaningful labels and state to macOS screen readers.

## 3. Target Platform and Technology

- **Operating system:** macOS.
- **Application type:** Native desktop application.
- **Language and runtime:** C# on a supported .NET release.
- **UI framework:** Avalonia UI.
- **Network dependency:** None. All game features must work offline.
- **Data storage:** Local application data only.

The exact supported macOS and .NET versions must be recorded in the implementation README once the project toolchain is selected.

## 4. Gameplay Rules

### 4.1 Board

- The board is always 4 columns by 4 rows.
- It contains each numbered tile from 1 through 15 exactly once and one empty cell.
- The solved order is 1 through 15 in row-major order, followed by the empty cell.
- A tile can move only when it is horizontally or vertically adjacent to the empty cell.
- A legal move slides exactly one tile into the empty cell.
- Diagonal movement and movement of non-adjacent tiles are not allowed.

### 4.2 New Game

- Starting a new game generates a randomized, mathematically solvable layout.
- A generated layout must not be the solved layout.
- New layouts should not be predictably repeated during normal play.
- Starting a new game resets the move count to zero and the timer to zero.
- The timer remains stopped until the player's first legal move.
- If a game has at least one legal move and is not solved, requesting a new game must display a confirmation dialog.
- Cancelling the confirmation must preserve the board, elapsed time, move count, and timer state.
- No confirmation is required before the first move or after a solved game.

### 4.3 Move Count

- Each legal tile slide increments the move count by exactly one.
- Invalid input does not change the move count.
- A new game resets the move count to zero.

### 4.4 Timer

- The timer starts when the first legal move is completed.
- The timer stops when the puzzle is solved.
- The timer pauses while the application is minimized or suspended and resumes when the application becomes active.
- Time spent in the new-game confirmation dialog is not counted.
- Elapsed time is displayed with a resolution of one second.
- The stored completion time must use a monotonic elapsed-time source so wall-clock changes do not affect a result.

### 4.5 Completion

- After every legal move, the application checks whether the board is solved.
- On completion, the application stops the timer and displays the final elapsed time and move count.
- A completion is considered for both local leaderboards.
- The player can start another game from the completion state.

## 5. Input Requirements

### 5.1 Pointer Input

- Clicking or tapping a tile adjacent to the empty cell performs one move.
- Activating a non-adjacent tile has no effect.
- Tiles have a clear hover state where pointer hover is available.

### 5.2 Keyboard Input

- The complete game flow, including dialogs and leaderboards, must be usable without a pointer.
- Arrow keys move a numbered tile into the empty cell in the direction of the arrow. For example, Left moves the tile to the right of the empty cell leftward into it.
- An arrow key that cannot produce a legal move has no effect.
- Keyboard and pointer moves follow identical move-count, timer, and completion rules.
- Standard macOS keyboard navigation must reach and activate New Game, Best Scores, dialog actions, and leaderboard close actions.

## 6. User Interface Requirements

The main window must show:

- The 4 x 4 game board.
- Current move count.
- Current elapsed time.
- A New Game command.
- A Best Scores command.

Additional requirements:

- Numbered tiles and the empty cell must be visually distinct.
- Legal game state must remain readable at all supported window sizes.
- The board must preserve a square aspect ratio when the window is resized.
- Controls must not overlap, clip essential text, or cause the board geometry to shift during play.
- The current game must remain visible and unchanged after the Best Scores view is closed.
- Destructive replacement of an active game must use a modal confirmation with explicit Continue and Cancel actions; Cancel is the default safe action.
- The application must provide visible focus indicators for keyboard navigation.
- The application must use a consistent macOS-appropriate visual style while following Avalonia conventions.

## 7. Best Scores

### 7.1 Leaderboards

- The application maintains two separate local leaderboards:
  - Fastest completion times.
  - Fewest moves.
- Each leaderboard stores at most 10 entries.
- Each entry includes elapsed time, move count, and completion date.
- The fastest-times leaderboard sorts by elapsed time ascending, then move count ascending, then completion date ascending.
- The fewest-moves leaderboard sorts by move count ascending, then elapsed time ascending, then completion date ascending.
- A single completed game may appear in both leaderboards.
- The Best Scores view clearly identifies the two ranking categories and their order.
- If no scores exist, the view displays a clear empty state.

### 7.2 Persistence

- Leaderboards persist across normal application restarts.
- Data is stored in the user's standard macOS application-data location.
- No personal identity is collected; entries do not require player names.
- Missing or malformed score data must not prevent the application from starting or playing a new game.
- Score writes must avoid leaving a partially written data file after an interrupted save.

## 8. Accessibility

- Every numbered tile exposes an accessible name containing its number.
- The empty cell exposes an accessible name that identifies it as empty.
- The board exposes enough row and column information for a screen-reader user to understand tile positions.
- Move count, elapsed time, and solved status expose meaningful accessible labels and values.
- New Game, Best Scores, and all dialog actions expose descriptive accessible names.
- Focus order is logical and predictable.
- Status announcements must not continuously announce every timer tick.
- Puzzle completion must be announced to assistive technology.
- Information required to play must not be conveyed by color alone.

## 9. Reliability and Performance

- The application must launch to an interactive board without requiring network access.
- A legal move must produce visible feedback within 100 ms under normal desktop load.
- Input must not permit multiple simultaneous moves or corrupt board state.
- The UI must remain responsive during board generation, score loading, and score saving.
- An unexpected persistence failure may omit score storage but must not invalidate the completed game or terminate the application.

## 10. Acceptance Criteria

The first release is accepted when all of the following are demonstrated on a supported macOS system:

1. At least 1,000 generated boards pass an automated solvability check, contain all required values exactly once, and are not initially solved.
2. For every board state, only tiles orthogonally adjacent to the empty cell can be moved.
3. A legal move updates the board and increments the move count once; an invalid move changes neither.
4. The timer starts on the first legal move, pauses for minimization, suspension, and the new-game confirmation, and stops on completion.
5. Pointer and arrow-key input can each complete a puzzle and produce the same state transitions.
6. Starting a new game during active play requires confirmation, and cancelling preserves the exact game state.
7. Solving a puzzle reports the correct final time and move count and updates each qualifying leaderboard.
8. Both leaderboards apply their specified sorting, tie-breaking, and 10-entry limits.
9. Scores survive an application restart, and corrupt score data does not block startup or gameplay.
10. All gameplay, dialogs, and score views can be operated using only the keyboard.
11. A macOS screen reader identifies numbered tiles, the empty cell, primary commands, game statistics, and puzzle completion.
12. The board remains square and all essential UI remains visible at the documented minimum window size.

## 11. Out of Scope for the First Release

- Board sizes other than 4 x 4.
- Automated hints or puzzle-solving algorithms.
- Undo and redo.
- Image-based tile sets.
- Sound effects and move animations beyond essential visual feedback.
- Online accounts, cloud synchronization, telemetry, or online leaderboards.
- Multiplayer modes.
- Windows, Linux, iOS, and Android distribution.
- Custom player names or profiles.

## 12. Delivery Requirements

- The repository includes source code, automated tests, and build/run instructions.
- Core puzzle rules and solvability logic are testable without launching the UI.
- Persistence behavior is testable using an isolated temporary data location.
- The release build is packaged as a macOS application using the architecture supported by the selected development machine and documented toolchain.
- Third-party dependencies and their purposes are documented.

## 13. Assumptions and Deferred Decisions

- The product uses a single built-in visual theme for the first release.
- The minimum window size and exact macOS/.NET support matrix will be set after an Avalonia prototype verifies layout and packaging.
- Code signing, notarization, and public App Store distribution are not required unless added as separate release requirements.
- Localization is deferred; the first release uses English UI text.