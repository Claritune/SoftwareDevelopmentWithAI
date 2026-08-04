# Design: URL Monitor CLI (C#)

## Current State

Greenfield -- no existing C# code. We have a working C++ reference implementation that defines the architecture and behavior.

## Desired End State

A fully functional C# CLI tool (`url-monitor`) that:
- Reads a YAML config file specifying URLs and check intervals
- Monitors each URL with HTTP GET requests on a timer
- Tracks Up/Down status per URL, emitting notifications on transitions
- Persists state (status + stats) to a JSON sidecar file
- Handles graceful shutdown on Ctrl+C
- Provides `--stats` mode to query accumulated data

## Architecture Decisions

### Module decomposition (matching C++)
- **Config** -- CLI args + YAML loading. No `System.CommandLine`, manual parsing. `YamlDotNet` for deserialization.
- **Checker** -- Wraps `HttpClient`. Returns `CheckResult` record. `Classify()` is a pure function.
- **Monitor** -- Owns the loop. Takes `CancellationToken` for shutdown. Calls Checker, updates State, invokes Notifier.
- **Notifier** -- Static methods for output. `LogInfo`/`LogError` with timestamps. `EmitTransition` for status changes.
- **State** -- JSON sidecar via `System.Text.Json`. Atomic writes (temp file + rename). Reconciliation against config.
- **Stats** -- Counter accumulation per URL. Formatting for display.

### Data types
Using C# records for immutable value types (`UrlSpec`, `CheckResult`, `CliArgs`). Classes for mutable state (`UrlStats`, `UrlState`, `StateStore`, `MonitorConfig`).

### Serialization
- Config: `YamlDotNet` with `UnderscoredNamingConvention` to match `check_interval_seconds` YAML keys
- State: `System.Text.Json` with `JsonPropertyName` attributes and custom converters for `Dictionary<int,long>` (HTTP status codes keyed by int)

### Async model
The tool is fundamentally synchronous with one async touch point: `Task.Delay()` for interruptible sleep. Using `.Wait()` to keep the synchronous model. Full async/await would be cleaner but adds complexity without material benefit for a sequential checker.

## What We're NOT Building

- No parallel URL checks (concurrency)
- No retry logic on failures
- No exponential backoff
- No webhook/email/Slack notifications
- No web dashboard or API
- No Docker packaging
- No Windows service / systemd integration
- No `System.CommandLine` integration
- No dependency injection

## Open Risks

1. **HttpClient per-request pattern** -- Creating `new HttpClient()` per check can exhaust sockets. Should use a singleton. Noted as known tech debt.
2. **Synchronous blocking** -- `.Wait()` and `.Result` on async calls can cause thread pool starvation under load. Acceptable for a simple sequential CLI but would be a problem if we added parallelism.
3. **No config hot-reload** -- Config is read once at startup. Requires restart to pick up changes.
4. **State file corruption** -- Atomic write (temp+rename) protects against partial writes, but the empty catch block in `SaveState` could hide persistent I/O failures.
