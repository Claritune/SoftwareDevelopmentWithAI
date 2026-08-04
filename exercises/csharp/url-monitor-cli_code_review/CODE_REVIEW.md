# Code Review: URL Monitor CLI (C#)

**Reviewer:** Senior .NET Developer
**Date:** 2026-08-04
**Scope:** Full solution review -- `src/UrlMonitor/` and `tests/UrlMonitor.Tests/`

---

## Overall Assessment

The solution is well-structured and follows the specified architecture closely. Module decomposition is clean, the code uses modern C# features appropriately (records, pattern matching, nullable reference types), and the test coverage hits the core classification and stats logic. However, there are several issues ranging from resource management problems to silent error handling that should be addressed before this goes into production use.

## What Works Well

- **Clean module separation.** Each file has a clear, single responsibility. Config does config, Checker does checking, Notifier does output. Easy to navigate.
- **Good use of records.** `UrlSpec`, `CheckResult`, and `CliArgs` are natural fits for immutable value types.
- **Atomic state writes.** The temp-file-then-rename pattern in `SaveState()` prevents corrupted state files from partial writes. This is the right approach.
- **Graceful shutdown.** The `CancellationToken` + `Console.CancelKeyPress` pattern is correct and idiomatic for .NET CLI tools.
- **State reconciliation.** Adding new URLs and removing stale ones when the config changes is handled correctly.
- **Test quality.** The classify tests cover the edge cases well (200 with error, 0 with no error, etc.). The stats round-trip test catches serialization bugs early.

---

## High-Impact Issues

### 1. Silent exception swallowing in SaveState()

**File:** `State.cs`, line ~87
**Severity:** High

```csharp
catch (Exception) { }
```

The entire `SaveState()` method is wrapped in a try/catch that silently discards all exceptions. If the disk is full, the state directory is deleted, or permissions change, the tool will continue running with no indication that state is not being persisted. On the next restart, all accumulated stats and status history could be lost.

**Recommendation:** At minimum, log the error via `Notifier.LogError()`. Consider also tracking consecutive save failures and warning more aggressively if state hasn't been saved for multiple cycles.

### 2. New HttpClient per check

**File:** `Checker.cs`, line ~19
**Severity:** High

```csharp
var client = new HttpClient { ... };
```

A new `HttpClient` is created for every `Check()` call. In .NET, `HttpClient` is designed to be long-lived and reused. Creating one per request leads to socket exhaustion because disposed `HttpClient` instances leave sockets in `TIME_WAIT` state. Under continuous monitoring with short intervals, this will eventually cause `SocketException` failures.

**Recommendation:** Create a single `HttpClient` instance (or one per unique timeout value) and reuse it. If timeout needs to vary per URL, set it on the `HttpRequestMessage` or use `CancellationToken`-based timeouts instead of the `HttpClient.Timeout` property.

### 3. Synchronous .Result / .Wait() on async methods

**File:** `Checker.cs`, line ~29; `Monitor.cs`, line ~32
**Severity:** Medium-High

```csharp
var response = client.GetAsync(url).Result;
Task.Delay(...).Wait();
```

Using `.Result` and `.Wait()` on async methods blocks the calling thread and can cause thread pool starvation. In a simple sequential CLI this may not cause immediate problems, but it's an anti-pattern that will bite if the tool is ever enhanced to check URLs concurrently. It also means exceptions are wrapped in `AggregateException`, requiring extra unwrapping logic.

**Recommendation:** Make the entire call chain async: `async Task Main`, `async Task Run`, `await client.GetAsync()`, `await Task.Delay()`. This is straightforward and eliminates the thread-blocking concern.

### 4. No duplicate URL validation

**File:** `Config.cs`, `Validate()` method
**Severity:** Medium

The config validator checks that the URL list is non-empty and that timeouts are >= 1, but it does not check for duplicate URLs. If the same URL appears twice in the config, it will be checked twice per cycle, and stats will be accumulated into the same state entry -- but the second check's result overwrites the first's status. This creates confusing behavior: the URL shows double the expected check count, and the displayed status depends on which entry was processed last.

**Recommendation:** Add a duplicate check in `Validate()`:
```csharp
var duplicates = config.Urls.GroupBy(u => u.Url).Where(g => g.Count() > 1);
if (duplicates.Any())
{
    Console.Error.WriteLine($"Error: duplicate URL: {duplicates.First().Key}");
    Environment.Exit(1);
}
```

### 5. --stats shows stale URLs

**File:** `Program.cs`, line ~22
**Severity:** Medium

```csharp
if (cliArgs.StatsOnly)
{
    var store = State.LoadState(stateFilePath);
    Console.Write(Stats.FormatAllStats(store));
    return 0;
}
```

The `--stats` path loads the state file directly and prints it without reconciling against the current config. If URLs have been removed from the config, their stats still appear in the output. This is misleading -- a user sees stats for URLs that are no longer being monitored and may assume they're still active.

**Recommendation:** Load config, reconcile, then print stats. This ensures the output reflects the current monitoring scope.

---

## Medium-Impact Issues

### 6. State version field is never validated

**File:** `State.cs`, `LoadState()` method
**Severity:** Medium-Low

The `StateStore` has a `Version` field that is read from and written to JSON, but it is never checked. If the state format changes in a future version (e.g., restructuring stats, adding new fields), there is no migration path and no warning. Loading a version 2 state file into version 1 code would silently produce incorrect data.

**Recommendation:** Add a version check after deserialization:
```csharp
if (store.Version > 1)
{
    Notifier.LogError($"State file version {store.Version} is newer than supported (1). Starting fresh.");
    return new StateStore();
}
```

### 7. No URL scheme validation

**File:** `Config.cs`, `Validate()` method
**Severity:** Medium-Low

URLs are accepted as-is from the config file. A URL like `ftp://example.com`, `example.com` (no scheme), or even `not-a-url` will pass validation and only fail when `HttpClient` tries to send the request. The error message at that point is a low-level exception rather than a clear config validation error.

**Recommendation:** Validate that each URL starts with `http://` or `https://` and is parseable by `Uri.TryCreate()`:
```csharp
if (!Uri.TryCreate(url.Url, UriKind.Absolute, out var uri) ||
    (uri.Scheme != "http" && uri.Scheme != "https"))
{
    Console.Error.WriteLine($"Error: invalid URL (must be http/https): {url.Url}");
    Environment.Exit(1);
}
```

### 8. String parsing for HTTP status keys without error handling

**File:** `State.cs`, `HttpStatusDictConverter.Read()`
**Severity:** Medium-Low

```csharp
var key = int.Parse(reader.GetString()!);
```

JSON object keys are always strings, so when deserializing `Dictionary<int, long>`, the converter uses `int.Parse()` on the key string. If a state file is manually edited or corrupted to have a non-numeric key (e.g., `"abc": 5`), this throws an unhandled `FormatException` that crashes the process instead of falling back to empty state.

**Recommendation:** Use `int.TryParse()` and skip invalid entries:
```csharp
if (!int.TryParse(reader.GetString(), out var key))
{
    reader.Read(); // skip the value
    continue;
}
```

---

## Lower-Impact Notes

### Code style
- The `Checker.ClassifyHttpError()` method does string matching on exception messages, which is locale-dependent and fragile. Consider checking `HttpRequestException.InnerException` types instead.
- `Stats.RecordCheck()` uses `ContainsKey` + indexer pattern. Could use `TryGetValue` or collection expression patterns for slightly cleaner code.
- The YAML deserialization uses intermediate `YamlConfigDocument` and `YamlUrlEntry` classes. These could potentially be eliminated by deserializing directly into the domain types with proper YamlDotNet configuration.

### Naming
- `MonitorConfig` is clear. `CliArgs` as a record is fine.
- `EmitTransition` vs `EmitVerboseCheck` -- the distinction is clear but could be unified with a single `EmitCheck(bool isTransition)` method.

### Potential enhancements (not bugs)
- Consider adding a `--check-once` mode for scripting/CI usage
- The `FormatDetail` method in Notifier could show both HTTP status and error when both are present (currently shows only error if one exists)
- Stats formatting hardcodes column widths. Could benefit from dynamic alignment for long URLs.

---

## Decoupling Gaps

1. **Checker depends on concrete HttpClient.** There is no interface or abstraction for HTTP calls, making it impossible to unit test `Check()` without hitting the network. A `Func<string, int, CheckResult>` parameter or an `IHttpChecker` interface would allow injecting a test double.

2. **Notifier uses static Console.WriteLine.** All output goes directly to the console. If we wanted to test transition emission or redirect output, there's no seam. Passing a `TextWriter` or using an `INotifier` interface would improve testability.

3. **Monitor.Run() is tightly coupled.** It calls `Checker.Check()`, `State.SaveState()`, and `Notifier.EmitTransition()` directly. This makes it hard to test the monitoring logic without performing real HTTP requests and file I/O.

4. **Config.LoadConfig() calls Environment.Exit().** Validation errors terminate the process instead of throwing exceptions. This makes the config loading logic untestable -- any invalid config kills the test runner.

---

## Test Coverage Gaps

### Covered
- Status classification (all edge cases)
- Stats accumulation and formatting
- State serialization round-trip
- Legacy state file compatibility
- State reconciliation (add/remove URLs)
- Corrupt state file recovery

### Not Covered
- CLI argument parsing (`ParseArgs`) -- no tests for valid/invalid arg combinations
- Config YAML loading and validation -- no tests for missing file, invalid YAML, validation failures
- HTTP checking (`Check()`) -- would need network mocking or `IHttpChecker` interface
- Monitor loop behavior -- start, cycle, transition detection, shutdown sequence
- Notifier output format -- no assertion on timestamp format or transition message structure
- Atomic file write behavior -- no test that temp+rename actually works
- `DeriveStateFilePath()` -- simple function but untested edge cases (paths with dots, no extension, etc.)

---

## Recommended Fixes (Priority Order)

1. **Replace empty catch in SaveState with error logging** -- 5 min fix, prevents silent data loss
2. **Extract HttpClient to a shared instance** -- 10 min refactor, prevents socket exhaustion
3. **Add duplicate URL validation** -- 5 min fix in Validate()
4. **Reconcile state in --stats mode** -- 2 line change in Program.cs
5. **Make the pipeline async** -- 30 min refactor, eliminates thread-blocking anti-pattern
6. **Add URL scheme validation** -- 5 min fix in Validate()
7. **Add int.TryParse guard in converter** -- 5 min fix, prevents crash on corrupt state
8. **Add version validation in LoadState** -- 5 min fix, future-proofing

---

## Summary

| Category              | Rating     |
|----------------------|------------|
| Architecture         | Good       |
| Code clarity         | Good       |
| Error handling       | Needs work |
| Resource management  | Needs work |
| Test coverage        | Adequate   |
| Input validation     | Needs work |
| .NET best practices  | Needs work |
| Overall              | Functional but needs hardening |

The solution works correctly for the happy path and has a solid architectural foundation. The main concerns are around error handling (silent exception swallowing, missing input validation) and .NET-specific anti-patterns (HttpClient lifecycle, sync-over-async). These are all fixable without architectural changes -- the module structure supports incremental improvement.
