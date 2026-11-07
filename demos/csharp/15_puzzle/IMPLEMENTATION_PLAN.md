# 15 Puzzle Implementation Plan

## 1. Delivery Strategy

Build the application in dependency order so each milestone produces a testable result:

1. Establish the solution, toolchain, and automated test baseline.
2. Implement and verify the Core domain without Avalonia.
3. Implement and verify local score persistence.
4. Build the MVVM application shell and playable board.
5. Add dialogs, lifecycle behavior, leaderboards, and accessibility.
6. Validate the complete macOS application and document delivery.

Each milestone must pass its validation gate before work proceeds to the next one. Core rules, timing, and ranking remain independent of Avalonia throughout implementation.

## 2. Milestone 0: Toolchain and Solution Baseline

### Tasks

- Select an installed supported .NET SDK and compatible stable Avalonia release.
- Record the selected .NET, Avalonia, and minimum macOS versions.
- Create the solution and five projects described in [DESIGN.md](DESIGN.md):
  - `FifteenPuzzle.Core`
  - `FifteenPuzzle.Infrastructure`
  - `FifteenPuzzle.App`
  - `FifteenPuzzle.Core.Tests`
  - `FifteenPuzzle.Infrastructure.Tests`
- Add project references with the dependency direction defined in the design.
- Add Avalonia, CommunityToolkit.Mvvm, logging abstractions, and xUnit dependencies only to the projects that require them.
- Enable nullable reference types, implicit usings, deterministic builds, and warnings appropriate for the selected SDK.
- Add a repository-level build command and test command to the README.
- Add a minimal CI workflow, if CI is available for the repository, that restores, builds, and runs tests.

### Deliverables

- A solution that restores and builds on the development Mac.
- Empty test projects that are discovered by `dotnet test`.
- A README toolchain section with exact versions and commands.

### Validation Gate

- `dotnet build` succeeds without errors.
- `dotnet test` discovers both test assemblies and succeeds.
- `FifteenPuzzle.Core` has no Avalonia, storage, or operating-system dependency.

## 3. Milestone 1: Board Model and Puzzle Generation

### Tasks

- Implement `BoardPosition`, `MoveDirection`, and `PuzzleBoard`.
- Validate board construction: exactly 16 cells containing each value from 0 through 15 once.
- Implement solved-state detection and immutable cell snapshots.
- Implement tile-number moves and direction moves through shared adjacency rules.
- Add `IRandomSource`, `IPuzzleGenerator`, and `SolvablePuzzleGenerator`.
- Implement Fisher-Yates shuffling and the even-width inversion solvability rule.
- Supply deterministic fake and seeded random sources in tests.

### Tests

- Accept the canonical solved board and representative valid unsolved boards.
- Reject missing, duplicate, out-of-range, short, and long cell collections.
- Test legal and illegal tile moves with the empty cell at corners, edges, and center positions.
- Test all four direction mappings, including the requirement that `Left` moves the tile right of the empty cell leftward.
- Verify invalid moves preserve every cell and the empty position.
- Verify solved detection only for canonical order.
- Generate at least 1,000 seeded boards and independently verify that every board is complete, solvable, and not solved.

### Validation Gate

- All board and generation tests pass.
- Public cell data cannot be used to mutate board state.
- Generation completes comfortably within the 100 ms interaction budget in a local benchmark or timed test.

## 4. Milestone 2: Timer and Game Session

### Tasks

- Implement `IMonotonicClock` and `GameTimer`.
- Make start, pause, resume, stop, and reset transitions idempotent where specified.
- Implement `GameStatus`, `MoveResult`, and `GameSession`.
- Route tile and direction input through one private move pipeline.
- Start the timer only after the first legal move.
- Increment the move count only after legal moves.
- Detect completion after each legal move and freeze the final elapsed time.
- Define pause and resume behavior without changing the game status.

### Tests

- Use a manually advanced fake monotonic clock; do not use real delays.
- Verify ready, running, paused-running, and solved behavior.
- Verify invalid first input does not start the timer.
- Verify active intervals accumulate exactly and paused intervals are excluded.
- Verify reset clears elapsed time and moves and installs a new board.
- Verify a solving move increments once, transitions once, and freezes time.
- Verify moves after completion cannot mutate the solved session.
- Verify `HasActiveGame` is true only after a legal move and before completion.

### Validation Gate

- Core session and timer tests pass deterministically.
- No duration calculation uses `DateTime`, `DateTimeOffset`, or an Avalonia UI timer.

## 5. Milestone 3: Leaderboard Domain

### Tasks

- Implement `ScoreEntry`, `LeaderboardSnapshot`, and `Leaderboard`.
- Implement fastest-time ordering: elapsed time, move count, completion date.
- Implement fewest-moves ordering: move count, elapsed time, completion date.
- Limit each projection to 10 entries.
- Retain the de-duplicated union of entries qualifying for either projection.
- Keep ranking and truncation out of repository implementations.

### Tests

- Cover every primary ordering and tie-breaker.
- Cover fewer than, exactly, and more than 10 entries.
- Verify one result may qualify for both lists.
- Verify a result may qualify for only one list.
- Verify identical entries are de-duplicated.
- Verify adding a non-qualifying result does not alter retained entries.

### Validation Gate

- Ranking tests pass independent of storage and UI.
- Both public lists are read-only and contain no more than 10 entries.

## 6. Milestone 4: Infrastructure and Persistence

### Tasks

- Implement `SystemMonotonicClock`, `SystemWallClock`, and `SystemRandomSource`.
- Implement `IAppDataPathProvider` and the macOS application-data path provider.
- Implement the version 1 JSON persistence model and `JsonScoreRepository`.
- Validate every loaded entry before returning it to Core.
- Treat a missing file as an empty leaderboard.
- Quarantine malformed JSON, unsupported versions, and invalid entries with a `.corrupt` suffix when possible.
- Save through a sibling temporary file, flush it, and atomically replace the destination.
- Log recoverable load, quarantine, and save failures without allowing them to terminate startup or gameplay.

### Tests

- Use a unique temporary directory and injected path provider per test.
- Verify missing-file behavior and a complete round trip.
- Verify the exact schema version and preservation of milliseconds, move count, and UTC completion date.
- Verify malformed JSON, unsupported versions, and invalid entries return an empty result.
- Verify corrupt-file quarantine when the file system permits it.
- Simulate a failed/interrupted save and verify the destination remains either the old complete document or the new complete document.
- Verify cancellation tokens are honored by load and save operations.

### Validation Gate

- Infrastructure integration tests pass without reading or writing real user data.
- No persistence exception needs to cross into the Avalonia event loop.

## 7. Milestone 5: Avalonia Prototype and Application Shell

### Tasks

- Create `App`, `MainWindow`, and the composition root.
- Create `MainWindowViewModel` and immutable `TileViewModel` snapshots.
- Bind the 4 x 4 board, move count, elapsed time, New Game, and Best Scores controls.
- Implement tile activation through `MoveTileCommand`.
- Translate arrow keys in `MainWindow` and invoke `MoveDirectionCommand`.
- Refresh displayed elapsed time once per second while the domain timer is running.
- Preserve a square board with stable tile geometry across window sizes.
- Add hover, pressed, disabled, and visible keyboard-focus states.
- Choose and document the minimum window dimensions after testing the prototype.

### Tests

- Add view-model tests for equivalent pointer and direction transitions.
- Verify tile snapshots reflect board positions, movable state, and empty state.
- Verify invalid commands cause no observable session change.
- Verify input serialization prevents overlapping moves.
- Add Avalonia headless tests for bindings and keyboard command routing.
- Manually resize the window at and above the proposed minimum dimensions.

### Validation Gate

- A complete puzzle can be played using pointer input or arrow keys.
- Move count and elapsed display track the same `GameSession` state.
- The board remains square and essential controls do not overlap or clip at the documented minimum size.
- Legal input produces visible feedback within 100 ms under normal desktop load.

## 8. Milestone 6: Dialogs, Pause Coordination, and Completion

### Tasks

- Implement `IDialogService` and `AvaloniaDialogService`.
- Implement New Game and Completion dialogs with explicit default and cancel behavior.
- Add separate pause reasons for application inactivity and new-game confirmation.
- Forward Avalonia activation and deactivation events from `App` to the view model.
- Require confirmation only when `GameSession.HasActiveGame` is true.
- Preserve the exact session when confirmation is cancelled.
- On completion, create the score with `IWallClock.UtcNow`, update the in-memory leaderboard, attempt persistence, and show the completion dialog even if saving fails.
- Restore input state and focus after every dialog or recoverable exception.

### Tests

- Verify New Game before the first move and after completion requires no confirmation.
- Verify active-game cancel preserves cells, count, status, elapsed time, and resumed timer behavior.
- Verify active-game continue replaces the board and resets timer and count.
- Verify overlapping inactivity and confirmation pauses resume only after both reasons clear.
- Verify deactivation before the first move does not start the timer on activation.
- Verify completion is retained and shown when repository saving throws.
- Verify repeated input is disabled while a dialog or persistence transition is active.

### Validation Gate

- Timer lifecycle acceptance scenarios pass with a fake clock.
- Modal cancellation is safe by default and fully keyboard operable.
- Persistence failure cannot invalidate or hide a completed game.

## 9. Milestone 7: Best Scores Experience

### Tasks

- Implement `BestScoresViewModel` and `BestScoresDialog`.
- Present Fastest Times and Fewest Moves as clearly ordered categories.
- Show elapsed time, move count, and completion date for every row.
- Add empty states for both categories.
- Ensure opening and closing scores does not pause or mutate the current session.
- Provide a keyboard-reachable close action and Escape behavior.

### Tests

- Verify formatting and ordering from a supplied `LeaderboardSnapshot`.
- Verify empty-state visibility.
- Verify opening and closing the dialog preserves the current game and allows elapsed time to continue.
- Add headless tests for focus order, close action, and Escape behavior.

### Validation Gate

- Stored scores survive an application restart and display in both required projections.
- The complete Best Scores flow is usable without a pointer.

## 10. Milestone 8: Accessibility and macOS Validation

### Tasks

- Add accessible names for numbered tiles, the empty cell, primary commands, statistics, and dialog actions.
- Include row and column information in tile accessible names.
- Expose solved status through a deliberate completion announcement.
- Avoid live announcements for timer refreshes.
- Verify information needed to play is not represented by color alone.
- Verify logical focus order and visible focus in the main window and all dialogs.
- Test application activation, minimization, and restoration on macOS.

### Validation

- Run Avalonia headless accessibility and focus tests.
- Complete one game using only the keyboard.
- Use VoiceOver to inspect all tiles, the empty cell, move count, elapsed time, commands, dialogs, scores, and completion announcement.
- Verify the minimum-size and resized layouts on the supported macOS version.

### Validation Gate

- Acceptance criteria 10 through 12 are demonstrated and recorded in a manual smoke-test checklist.

## 11. Milestone 9: Packaging and Release Readiness

### Tasks

- Run the complete build and automated test suite in Release configuration.
- Publish for the architecture supported by the development machine.
- Package the published output as a macOS application bundle.
- Verify launch without network access and with no existing score directory.
- Verify upgrade behavior with valid, missing, and corrupt version 1 score files.
- Complete the macOS smoke-test checklist against the packaged application.
- Document build, test, run, publish, data location, dependency purposes, and known release limitations.
- Confirm that signing, notarization, and App Store distribution remain out of scope.

### Validation Gate

- The packaged application launches to an interactive, solvable board.
- All automated tests pass in Release configuration.
- All 12 acceptance criteria in [REQUIREMENTS.md](REQUIREMENTS.md) have automated evidence, manual evidence, or both.

## 12. Recommended Pull Request Sequence

Keep changes reviewable and preserve a passing main branch with this sequence:

1. Solution scaffold and toolchain documentation.
2. Board rules and deterministic puzzle generation.
3. Monotonic timer and game-session state machine.
4. Leaderboard ranking and retention.
5. JSON repository and macOS data path.
6. Avalonia shell, playable board, and keyboard input.
7. Dialogs, pause coordination, and completion flow.
8. Best Scores UI and persistence integration.
9. Accessibility, lifecycle, and responsive-layout hardening.
10. Packaging documentation and release smoke tests.

Each pull request should include the tests for its behavior and should leave `dotnet build` and `dotnet test` passing.

## 13. Definition of Done

A task is complete when:

- Its behavior is implemented at the ownership boundary identified in the design.
- Automated tests cover expected behavior, edge cases, and recoverable failures appropriate to the change.
- The solution builds without new warnings or errors.
- Public UI behavior is keyboard accessible and has appropriate accessible names.
- No unrelated refactoring or dependency is included.
- Relevant README, toolchain, or smoke-test documentation is updated.

The first release is complete only after the packaged macOS application passes the full acceptance checklist, not merely when the unit test suite passes.