# Answers: URL Monitor CLI (C#)

## Scope

1. **Long-lived foreground process.** Runs continuously until Ctrl+C. No one-shot mode for now -- `--stats` is the closest (loads saved state and prints it).
2. **Sequential per-cycle.** All URLs are checked one at a time within each cycle. Parallel checks can be a future enhancement but add complexity around error reporting and stats ordering.
3. **`--stats` only for now.** Shows accumulated stats from the saved state file. A `--status` mode could be added later but is not in scope.

## Technical

4. **Manual parsing.** Keeps it simple and avoids the `System.CommandLine` dependency (which is still in preview). Matches the C++ solution's approach.
5. **`HttpClient` directly.** For a CLI tool, `IHttpClientFactory` adds DI overhead without much benefit. Single `HttpClient` instance (or one per check, noting the trade-offs) is fine.
6. **Synchronous is acceptable** for the initial version. The C++ solution is synchronous. Using `Task.Delay` for interruptible sleep is the one async touch point, and `.Wait()` is pragmatic here even though it blocks.
7. **YamlDotNet** is the right choice. It's mature, well-maintained, and handles our simple config schema easily.
8. **No.** Removed URLs have their stats dropped. If re-added, they start fresh as Unknown. This matches the C++ behavior.

## Output

9. **Notifications and stats to stdout, errors to stderr.** `LogInfo` -> stdout, `LogError` -> stderr. Transition messages go to stdout.
10. **Always UTC.** ISO 8601 format with `Z` suffix. Consistent, unambiguous, matches the C++ solution.
11. **New status only.** Format: `TIMESTAMP DOWN  url  (detail)`. Previous status is implicit from the transition event.

## Testing

12. **Unit tests for classification and stats.** Test `Classify()` with various `CheckResult` inputs, test stats accumulation and formatting, test state round-trip serialization. No mock HTTP server for now -- that would be an integration test concern.
