# Structure: URL Monitor CLI (C#)

Three vertical slices, each independently buildable and testable.

## Slice 1: CLI + Single URL Check

**Goal:** Parse arguments, load config, perform one HTTP check, print result.

**Files:**
- `Config.cs` -- CLI arg parsing, YAML config loading with YamlDotNet
- `Checker.cs` -- HttpClient GET, CheckResult record, Classify()
- `Notifier.cs` -- Iso8601Now(), LogInfo(), EmitTransition()
- `Program.cs` -- Wire args -> config -> single check -> print

**Verification:**
```bash
dotnet run -- --config config/example.yaml --verbose
# Should print one check result per URL and exit
```

**Tests:**
- `ClassifyTests.cs` -- All Classify() cases (200=Up, 503=Down, error=Down, etc.)

## Slice 2: State Tracking + Transitions

**Goal:** Load/save JSON state, reconcile against config, detect and emit transitions.

**Files:**
- `State.cs` -- StateStore, UrlState, JSON serialization, Reconcile()
- `Stats.cs` -- UrlStats, RecordCheck(), FormatUrlStats()
- Update `Program.cs` -- Load state, run one cycle, save state, detect transitions

**Verification:**
```bash
dotnet run -- --config config/example.yaml --verbose
# Run twice -- second run should show transitions (or not, if status unchanged)
dotnet run -- --config config/example.yaml --stats
# Should print accumulated stats from state file
```

**Tests:**
- `StatsTests.cs` -- Accumulation, formatting, state round-trip, legacy compatibility

## Slice 3: Continuous Monitoring + Shutdown

**Goal:** Loop with interruptible sleep, graceful Ctrl+C shutdown, stats on exit.

**Files:**
- `Monitor.cs` -- Main loop, CancellationToken, Task.Delay sleep
- Update `Program.cs` -- CancelKeyPress handler, Monitor.Run()

**Verification:**
```bash
dotnet run -- --config config/example.yaml --verbose
# Should run continuously, Ctrl+C prints stats and exits cleanly
```

**Tests:**
- Manual: Ctrl+C behavior, state file persistence across runs
