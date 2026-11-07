# Fifteen Puzzle

A native macOS implementation of the classic 4 x 4 sliding puzzle, built with C# and Avalonia UI. Every generated board is solvable and unsolved, and the complete game can be operated by pointer or keyboard.

## Toolchain

- macOS on Apple silicon
- .NET SDK 10.0.302 or a compatible .NET 10 SDK
- Avalonia UI 12.1.1
- C# with nullable reference types enabled

The current development and release target is macOS 14 or newer on arm64. Signing, notarization, and App Store distribution are outside the first release scope.

## Build and Run

```sh
dotnet restore FifteenPuzzle.slnx
dotnet build FifteenPuzzle.slnx
dotnet test FifteenPuzzle.slnx
dotnet run --project src/FifteenPuzzle.App/FifteenPuzzle.App.csproj
```

Arrow keys slide a numbered tile in the direction pressed. Pointer users can activate any tile adjacent to the empty cell. New Game asks for confirmation after play has started, while Best Scores leaves the current game intact.

## Architecture

- `FifteenPuzzle.Core` contains board rules, solvable generation, monotonic timing, game-session state, and leaderboard ranking.
- `FifteenPuzzle.Infrastructure` provides system clocks, random generation, the macOS data path, and versioned JSON persistence.
- `FifteenPuzzle.App` contains Avalonia views, view models, dialogs, lifecycle handling, and composition.
- `FifteenPuzzle.Core.Tests` verifies board, generator, timer, session, and ranking behavior.
- `FifteenPuzzle.Infrastructure.Tests` verifies persistence in isolated temporary directories.

Core has no Avalonia, file-system, or operating-system dependency.

## Local Data

Scores are stored in the standard application-data directory resolved by .NET, under:

```text
FifteenPuzzle/scores.json
```

The file contains no player identity. Invalid or unsupported files are quarantined with a `.corrupt` suffix and do not prevent the game from starting. Saves use a same-directory temporary file followed by atomic replacement.

## Dependencies

- **Avalonia UI:** native desktop windowing, controls, styling, and macOS integration.
- **CommunityToolkit.Mvvm:** observable properties and generated commands.
- **System.Text.Json:** versioned local score serialization.
- **Microsoft.Extensions.Logging.Abstractions:** recoverable infrastructure diagnostics.
- **xUnit:** automated domain and persistence tests.

The game has no network dependency and does not collect telemetry.