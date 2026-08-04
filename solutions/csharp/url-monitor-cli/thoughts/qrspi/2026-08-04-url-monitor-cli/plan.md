# Plan: URL Monitor CLI (C#)

## Phase 1: Project Setup

1. Create solution structure:
   - `dotnet new sln` at project root
   - `src/UrlMonitor/` with console app project targeting net10.0
   - `tests/UrlMonitor.Tests/` with xUnit test project
   - Add `YamlDotNet` NuGet package

2. Create `config/example.yaml` with sample URLs

**Verify:** `dotnet build` succeeds with zero warnings

## Phase 2: Slice 1 -- CLI + Checker

1. Implement `Config.cs`:
   - `ParseArgs()` -- manual switch-based parsing
   - `LoadConfig()` -- YamlDotNet deserialization with snake_case convention
   - `Validate()` -- interval >= 5, urls non-empty, timeout >= 1
   - `DeriveStateFilePath()` -- config.yaml -> config.state.json

2. Implement `Checker.cs`:
   - `CheckResult` record, `Status` enum
   - `Check()` -- HttpClient GET with timeout
   - `Classify()` -- Up only if no error AND HTTP 200
   - `StatusName()` -- enum to lowercase string

3. Implement `Notifier.cs`:
   - `Iso8601Now()`, `LogInfo()`, `LogError()`
   - `EmitTransition()`, `EmitVerboseCheck()`

4. Wire in `Program.cs` -- parse args, load config, single check cycle

5. Write `ClassifyTests.cs` -- all Classify edge cases

**Verify:** `dotnet test` -- ClassifyTests pass. `dotnet run -- --help` prints usage.

## Phase 3: Slice 2 -- State + Stats

1. Implement `Stats.cs`:
   - `UrlStats` class with counters and dictionaries
   - `RecordCheck()` -- accumulate into stats
   - `FormatUrlStats()`, `FormatAllStats()` -- string formatting

2. Implement `State.cs`:
   - `UrlState`, `StateStore` classes with JSON attributes
   - Custom `JsonConverter` for `Dictionary<int,long>` keys
   - `LoadState()` -- file read with corrupt-file fallback
   - `SaveState()` -- atomic temp+rename
   - `Reconcile()` -- add new, remove stale

3. Update `Program.cs` for `--stats` mode

4. Write `StatsTests.cs` -- accumulation, formatting, round-trip, legacy

**Verify:** `dotnet test` -- all tests pass. Manual test of `--stats` mode.

## Phase 4: Slice 3 -- Monitor Loop

1. Implement `Monitor.cs`:
   - `Run()` -- main loop with CancellationToken
   - `RunCheckCycle()` -- iterate URLs, check, classify, emit
   - Interruptible sleep via `Task.Delay().Wait()`
   - Shutdown: log, save state, print stats

2. Update `Program.cs`:
   - `Console.CancelKeyPress` handler
   - `CancellationTokenSource` wiring
   - Call `Monitor.Run()`

**Verify:** `dotnet run -- --config config/example.yaml --verbose` runs continuously. Ctrl+C shows stats and exits with code 0.

## Phase 5: Documentation

1. Write `README.md` -- build/run/test instructions
2. Write `CODE_REVIEW.md` -- review findings
3. Write QRSPI thought artifacts
