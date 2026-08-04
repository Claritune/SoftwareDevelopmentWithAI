# Implementation Plan

## Overview

Build a .NET 8 foreground CLI that monitors one or more HTTP(S) URLs on independent, non-overlapping schedules, emits only UTC `UP`/`DOWN` transitions, and shuts down cooperatively on Ctrl+C. Implement it in the three vertical slices from `structure.md`, with deterministic xUnit coverage around parsing, HTTP classification, state transitions, scheduling, output serialization, and cancellation.

The project is greenfield, so `answers.md` is the accepted input in place of `research.md`. Product defaults are fixed at a 10-second interval, 10-second request timeout, and 3 consecutive failures. Pin `System.CommandLine` 2.0.10, the current stable package supporting .NET 8 and async `Task<int>` actions.

## Phase 1: Monitor One URL End to End

### Changes

#### 1. Solution and application project

**File**: `UrlMonitor.sln`
**Action**: create

- Create with `dotnet new sln --name UrlMonitor`.
- Add the application and test projects after creating them.

**File**: `src/UrlMonitor/UrlMonitor.csproj`
**Action**: create

- Create a `net8.0` console application with nullable reference types and implicit usings enabled.
- Add `System.CommandLine` package version `2.0.10`.
- Keep framework-dependent output as the default; do not add self-contained, single-file, trimming, tool-package, or runtime identifier settings.

#### 2. Typed monitoring outcomes and transitions

**File**: `src/UrlMonitor/Monitoring/CheckResult.cs`
**Action**: create

- Add immutable `CheckResult(bool IsHealthy, int? StatusCode, TimeSpan Elapsed, string Detail)`.
- Keep `Detail` as a stable user-facing category produced by the HTTP boundary, such as `HTTP 200`, `Request timed out`, `DNS failure`, or `Connection failure`; do not expose stack traces or depend on platform-specific exception messages.

**File**: `src/UrlMonitor/Monitoring/HealthTransition.cs`
**Action**: create

- Add `HealthState` with `Unknown`, `Up`, and `Down`.
- Add immutable `HealthTransition(HealthState State, CheckResult Result, DateTimeOffset Timestamp)`.

#### 3. HTTP checking boundary

**File**: `src/UrlMonitor/Monitoring/HttpUrlChecker.cs`
**Action**: create

- Co-locate an `IUrlChecker` interface exposing `Task<CheckResult> CheckAsync(Uri url, TimeSpan timeout, CancellationToken cancellationToken)` so monitor-loop tests can use a deterministic fake without adding an unplanned file.
- Implement `HttpUrlChecker` around an injected shared `HttpClient`; do not construct or dispose a client per request.
- For each request, create a linked cancellation source from application cancellation and apply `CancelAfter(timeout)`.
- Measure elapsed time with `Stopwatch.GetTimestamp()` / `Stopwatch.GetElapsedTime()` and dispose the response.
- Classify 200-399 as healthy and other received statuses as unhealthy.
- Distinguish request timeout from application cancellation: catch linked-token cancellation only when the application token was not canceled and return an unhealthy timeout result; propagate cancellation when the application token is canceled.
- Return typed results for expected HTTP outcomes rather than throwing.

#### 4. Health state machine

**File**: `src/UrlMonitor/Monitoring/HealthTracker.cs`
**Action**: create

- Own `HealthState` and consecutive-failure count for one URL; no shared mutable state.
- Use the phase default threshold of 3.
- Implement `HealthTransition? Observe(CheckResult result, DateTimeOffset timestamp)` with these exact rules: first success from `Unknown` emits `Up`; failures increment the count; reaching 3 from `Unknown` or `Up` emits `Down`; additional failures while `Down` emit nothing; one success from `Down` emits `Up`; any success resets failures; success while `Up` emits nothing.
- Expose state only if tests need to assert it; favor transition assertions over mutable internals.

#### 5. Single-target scheduling loop

**File**: `src/UrlMonitor/Monitoring/UrlMonitor.cs`
**Action**: create

- Implement a monitor instance that owns one URL, interval, timeout, checker, tracker, notification sink, UTC clock delegate, and delay delegate.
- Co-locate the minimal internal clock/delay delegate boundaries rather than introducing framework-heavy abstractions. Production uses `TimeProvider.System.GetUtcNow` and `Task.Delay`; tests inject controlled delegates.
- Implement `Task RunAsync(CancellationToken cancellationToken)` as a sequential loop: check immediately, observe, optionally write a transition, then await the interval.
- Start the delay only after the check and notification complete, guaranteeing no overlap for the URL.
- Allow `OperationCanceledException` caused by the supplied token to end the loop normally; never convert shutdown into an unhealthy result or notification.

#### 6. Transition output

**File**: `src/UrlMonitor/Output/ConsoleNotificationSink.cs`
**Action**: create

- Co-locate an `INotificationSink` interface used by `UrlMonitor`.
- In Phase 1 the sink may be bound to the single monitored URL; Phase 2 will move the URL into `WriteAsync` for shared use.
- Write one complete line per transition to an injected `TextWriter`.
- Use an invariant UTC ISO 8601 timestamp and stable layout: `[timestamp] UP    url (detail, Nms)` or `[timestamp] DOWN  url (detail, Nms)`.
- Round elapsed milliseconds consistently and emit no routine-check lines.

#### 7. CLI composition and process entry point

**File**: `src/UrlMonitor/CliApplication.cs`
**Action**: create

- Build a `RootCommand` with one required positional URL argument in Phase 1 and generated help.
- Validate that the value is an absolute `http` or `https` URI. Unsupported schemes, malformed URLs, or missing values must prevent monitor construction.
- Use constants `DefaultInterval = 10 seconds`, `DefaultTimeout = 10 seconds`, and `DefaultFailureThreshold = 3`.
- Configure an async `SetAction((ParseResult, CancellationToken) => Task<int>)`, invoke with `ParseResult.InvokeAsync`, and pass the caller token through the full graph.
- Inject stdout, stderr, shared `HttpClient`, and a narrow monitor-runner factory/delegate so CLI tests can prove parsing without starting a real infinite loop.
- Return `0` for normal cancellation/help, `2` for argument or option validation errors, and reserve `1` for unexpected top-level failures added in Phase 3.
- Let `System.CommandLine` generate help, but ensure validation diagnostics are concise and directed to the injected stderr writer.

**File**: `src/UrlMonitor/Program.cs`
**Action**: create

- Create one process-lifetime `HttpClient` and `CancellationTokenSource`.
- Handle `Console.CancelKeyPress`, set `eventArgs.Cancel = true`, and cancel the source.
- Call `CliApplication.RunAsync(args, cancellationToken)` and return its exit code.
- Dispose process-owned resources after all monitoring work has completed.

#### 8. Test project and Phase 1 tests

**File**: `tests/UrlMonitor.Tests/UrlMonitor.Tests.csproj`
**Action**: create

- Create from the .NET 8 xUnit template and add a project reference to the application.
- Preserve the template's test SDK, xUnit runner, and coverage collector package references; do not add mocking or dependency-injection frameworks.
- Add both projects to `UrlMonitor.sln`.

**File**: `tests/UrlMonitor.Tests/HealthTrackerTests.cs`
**Action**: create

- Cover first-success `UP`, failures below threshold, threshold `DOWN` from `Unknown`, threshold `DOWN` after `Up`, suppression of repeated `DOWN`, one-success recovery, suppression of repeated `UP`, and reset of partial failures after success.
- Assert transition timestamp and original `CheckResult` are preserved.

**File**: `tests/UrlMonitor.Tests/HttpUrlCheckerTests.cs`
**Action**: create

- Use a small custom `HttpMessageHandler` fake.
- Cover healthy boundaries 200 and 399, unhealthy boundaries 400 and 599, response disposal, timeout classification, and propagation of application cancellation.
- Assert status code, health flag, stable detail, and non-negative elapsed time.

**File**: `tests/UrlMonitor.Tests/UrlMonitorTests.cs`
**Action**: create

- Use scripted checker results, a captured sink, fixed UTC clock, and controlled delay delegate.
- Prove the first check is immediate, transition-only writes, delay occurs after completion, no overlapping check begins, and cancellation during check or delay exits without a failure transition.

**File**: `tests/UrlMonitor.Tests/CliApplicationTests.cs`
**Action**: create

- Cover missing URL, malformed URL, relative URL, unsupported scheme, one valid URL, generated help, stderr routing, validation exit `2`, and canceled valid invocation returning `0`.
- Assert invalid input never invokes the injected monitor runner.

### Verification

#### Automated

- [x] `dotnet restore UrlMonitor.sln` restores `System.CommandLine` 2.0.10 and test dependencies.
- [x] `dotnet build UrlMonitor.sln --configuration Debug --no-restore` compiles with zero errors and warnings.
- [x] `dotnet test tests/UrlMonitor.Tests/UrlMonitor.Tests.csproj --configuration Debug --no-build` passes all Phase 1 tests.
- [x] `dotnet run --project src/UrlMonitor/UrlMonitor.csproj -- --help` shows the required URL argument and exits `0`.
- [x] `dotnet run --project src/UrlMonitor/UrlMonitor.csproj -- not-a-url` writes a concise stderr diagnostic and exits `2`.

#### Manual

- [ ] Run `dotnet run --project src/UrlMonitor/UrlMonitor.csproj -- https://example.com`; confirm one initial `UP`, no per-check output over at least two intervals, and stable URL/detail formatting.
- [ ] Press Ctrl+C during an interval and during an in-flight request; confirm the process exits cleanly with no `DOWN`, cancellation error, or stack trace.

---

## Phase 2: Monitor Multiple URLs on Independent Cadences

### Changes

#### 1. Validated targets and interval mapping

**File**: `src/UrlMonitor/Monitoring/MonitorTarget.cs`
**Action**: create

- Add immutable `MonitorTarget(Uri Url, TimeSpan Interval)`.
- Put interval mapping in a focused static method accessible to CLI tests: zero interval values map every URL to the 10-second default; one positive value broadcasts; exactly one positive value per URL maps positionally; every other count is invalid.
- Keep URL parsing and positive-integer validation at the CLI boundary so `MonitorTarget` receives validated values.

#### 2. Concurrent coordination

**File**: `src/UrlMonitor/Monitoring/MonitorCoordinator.cs`
**Action**: create

- Accept a factory that creates one independently stateful monitor loop per `MonitorTarget`.
- Implement `Task RunAsync(IReadOnlyList<MonitorTarget> targets, CancellationToken cancellationToken)` by creating all loops before awaiting `Task.WhenAll`.
- Do not use fire-and-forget tasks, sequentially await targets, or share `HealthTracker` instances.
- Treat token-driven cancellation as normal completion only after all target loops have observed cancellation.

#### 3. Multi-URL CLI parsing and composition

**File**: `src/UrlMonitor/CliApplication.cs`
**Action**: modify

- Change the positional argument to `Argument<string[]>` with one-or-more arity.
- Add repeatable `Option<int[]> --interval`; keep one integer per occurrence so `--interval 10 --interval 60` preserves positional order.
- Add validators for positive interval values and the cross-field mapping count. Error text must state that intervals may be omitted, supplied once, or supplied once per URL.
- Parse all URLs in order, call `MapTargets`, compose one `HealthTracker` and one `UrlMonitor` per target, and run them through `MonitorCoordinator`.
- Refactor the test runner boundary to accept the validated target list while preserving stderr and exit-code behavior.

#### 4. Shared serialized output

**File**: `src/UrlMonitor/Output/ConsoleNotificationSink.cs`
**Action**: modify

- Change the interface and implementation to `Task WriteAsync(Uri url, HealthTransition transition, CancellationToken cancellationToken)` so one sink can serve all loops.
- Protect each complete write/flush operation with a private `SemaphoreSlim` and release it in `finally`.
- Pass cancellation while waiting for the output lock; do not leave partial lines or a held semaphore after cancellation.

#### 5. Phase 2 tests

**File**: `tests/UrlMonitor.Tests/CliApplicationTests.cs`
**Action**: modify

- Add multiple valid URLs, default mapping, one-value broadcast, exact positional mapping, mismatched count, zero/negative intervals, repeated-option order, and help-text examples.
- Assert no monitor starts when any URL, interval, or mapping is invalid.

**File**: `tests/UrlMonitor.Tests/MonitorCoordinatorTests.cs`
**Action**: create

- Use gated monitor-loop fakes to prove all targets start before any completes, one task per target is awaited, cancellation reaches all loops, and one target's cadence/state is not shared with another.
- Keep per-URL non-overlap assertions in `UrlMonitorTests`; coordinator tests focus on cross-target concurrency and completion.

**File**: `tests/UrlMonitor.Tests/ConsoleNotificationSinkTests.cs`
**Action**: create

- Verify exact UTC line formatting for `UP` and `DOWN`.
- Use a deliberately yielding `TextWriter` and concurrent writes to prove lines are serialized and not character-interleaved.
- Verify cancellation while waiting for the lock does not corrupt subsequent output.

### Verification

#### Automated

- [ ] `dotnet build UrlMonitor.sln --configuration Debug` compiles with zero errors and warnings.
- [ ] `dotnet test tests/UrlMonitor.Tests/UrlMonitor.Tests.csproj --configuration Debug --no-build` passes all Phase 1 and Phase 2 tests.
- [ ] `dotnet run --project src/UrlMonitor/UrlMonitor.csproj -- https://example.com https://example.org --interval 0` exits `2` with a positive-value diagnostic.
- [ ] `dotnet run --project src/UrlMonitor/UrlMonitor.csproj -- https://example.com https://example.org --interval 5 --interval 10 --interval 15` exits `2` with the mapping-count diagnostic.

#### Manual

- [ ] Start local endpoints with `python3 -m http.server 8000` and `python3 -m http.server 8001` in separate terminals, then run the monitor against `http://localhost:8000 http://localhost:8001 --interval 5 --interval 10`; confirm both initial `UP` lines appear and each loop continues independently.
- [ ] Trigger near-simultaneous transitions by stopping both servers; confirm complete notification lines never interleave.
- [ ] Press Ctrl+C while both targets are active; confirm both loops stop and the process exits cleanly.

---

## Phase 3: Harden Operations and Document Distribution

### Changes

#### 1. Global monitor settings

**File**: `src/UrlMonitor/Monitoring/MonitorSettings.cs`
**Action**: create

- Add immutable `MonitorSettings(TimeSpan Timeout, int FailureThreshold)`.
- Construct it only from validated CLI values; use 10 seconds and 3 when the corresponding options are omitted.

#### 2. Configurable threshold

**File**: `src/UrlMonitor/Monitoring/HealthTracker.cs`
**Action**: modify

- Replace the hard-coded threshold with `HealthTracker(int failureThreshold)`.
- Reject non-positive constructor values with `ArgumentOutOfRangeException` as an invariant guard, while user-facing validation remains in the CLI.
- Preserve all Phase 1 transition semantics and independent count per URL.

#### 3. Complete HTTP failure classification

**File**: `src/UrlMonitor/Monitoring/HttpUrlChecker.cs`
**Action**: modify

- Preserve normal `HttpClient` redirect handling and classify the final response received by the client.
- Catch expected `HttpRequestException` transport failures and produce stable unhealthy details. Inspect an inner `SocketException` only to distinguish DNS lookup failures from general connection failures; do not surface localized exception text.
- Keep non-success HTTP status results separate from transport failures.
- Preserve the cancellation precedence: if application cancellation is requested, rethrow `OperationCanceledException`; otherwise linked-token cancellation is a request timeout result.
- Do not catch programming errors or unexpected exceptions as site failures.

#### 4. Apply global settings to every loop

**File**: `src/UrlMonitor/Monitoring/UrlMonitor.cs`
**Action**: modify

- Accept `MonitorSettings` or its timeout value alongside each target; pass the global timeout into every HTTP check.
- Ensure cancellation during an in-flight request exits without calling `HealthTracker.Observe` and without scheduling another delay.

#### 5. Final CLI options and top-level error behavior

**File**: `src/UrlMonitor/CliApplication.cs`
**Action**: modify

- Add `Option<int> --timeout` with default 10 and `Option<int> --failure-threshold` with default 3.
- Validate both as positive whole numbers and describe their global scope in help text.
- Build one `MonitorSettings` and pass it to every target monitor; create a separate `HealthTracker(settings.FailureThreshold)` per URL.
- Catch token-driven cancellation at the action boundary and return `0` without output.
- Catch unexpected top-level exceptions, write one concise stderr line prefixed with `Error:`, and return `1`; do not print stack traces in normal CLI output.
- Preserve `2` for parse/validation failures and ensure neither expected endpoint failures nor threshold transitions affect process exit status.

#### 6. Complete CLI and behavior tests

**File**: `tests/UrlMonitor.Tests/CliApplicationTests.cs`
**Action**: modify

- Cover timeout and threshold defaults, valid custom values, zero/negative values, settings propagation to every target, unexpected runner exception to stderr/exit `1`, and cancellation to silent exit `0`.
- Verify `--help` documents defaults, repeatable interval mapping, global settings, and positional URL order.

**File**: `tests/UrlMonitor.Tests/HttpUrlCheckerTests.cs`
**Action**: modify

- Add DNS failure, connection failure, final redirected response, and unexpected-exception propagation cases.
- Use controlled handlers for status/transport/cancellation tests and a minimal loopback HTTP server only for redirect-following behavior, avoiding external DNS/network dependencies.
- Verify timeout and application shutdown remain distinguishable under an in-flight request.

**File**: `tests/UrlMonitor.Tests/UrlMonitorTests.cs`
**Action**: modify

- Add custom timeout propagation, custom threshold behavior through the composed loop, cancellation before observation, and cancellation preventing subsequent delay/check cases.

#### 7. User documentation

**File**: `README.md`
**Action**: modify

- Replace or clearly supersede the illustrative `--log-file` example so excluded functionality is not presented as supported.
- Add prerequisites, restore/build/test commands, and `dotnet run --project src/UrlMonitor/UrlMonitor.csproj -- ...` examples for default, broadcast, and positional intervals.
- Document defaults: interval 10 seconds, timeout 10 seconds, failure threshold 3.
- Document URL requirements, positive whole-second options, interval-count rules, 200-399 health classification, threshold/recovery semantics, transition-only UTC stdout, stderr usage, and exit codes 0/1/2.
- State that interval delay begins after a check completes, each URL has at most one in-flight request, redirects are classified by final response, and Ctrl+C cancels in-flight work cleanly.
- Document framework-dependent publishing with `dotnet publish src/UrlMonitor/UrlMonitor.csproj --configuration Release`, the output directory convention, the requirement for a compatible installed .NET runtime, and invoking the published executable with `--help`.
- Keep configuration files, logging, services, packaged tools, self-contained binaries, and other excluded features out of the usage contract.

### Verification

#### Automated

- [ ] `dotnet restore UrlMonitor.sln` succeeds from a clean package state.
- [ ] `dotnet build UrlMonitor.sln --configuration Release --no-restore` compiles with zero errors and warnings.
- [ ] `dotnet test UrlMonitor.sln --configuration Release --no-build` passes all state, parsing, HTTP, scheduling, output, and cancellation tests without external-network dependencies.
- [ ] `dotnet run --project src/UrlMonitor/UrlMonitor.csproj -- --help` shows all defaults and mapping rules and exits `0`.
- [ ] Invalid invocations for each URL/interval/timeout/threshold rule exit `2` and write only concise stderr diagnostics.
- [ ] `dotnet publish src/UrlMonitor/UrlMonitor.csproj --configuration Release --no-build` produces framework-dependent output.
- [ ] Run the published executable from `src/UrlMonitor/bin/Release/net8.0/publish/UrlMonitor --help`; confirm it starts and exits `0`.

#### Manual

- [ ] Start `python3 -m http.server 8000`, monitor `http://localhost:8000 --interval 2 --timeout 1 --failure-threshold 3`, and observe one initial `UP`.
- [ ] Stop the local server; observe no output for the first two failures and exactly one `DOWN` on the third failure.
- [ ] Leave it stopped for another interval; confirm no repeated `DOWN`.
- [ ] Restart the server; observe exactly one recovery `UP`, then no routine output.
- [ ] Stop/restart during an active request and press Ctrl+C; confirm no cancellation-related transition, stderr message, or stack trace.
- [ ] Compare README commands and output examples with actual `--help` and smoke-test behavior.

## Dependencies and Ordering

1. Execute phases strictly in the order defined by `structure.md`; each phase depends on the previous phase's passing checkpoint.
2. Within Phase 1, project scaffolding blocks source and test compilation; typed result/transition files and interfaces can then be implemented in parallel, followed by the monitor loop, CLI composition, and tests.
3. Within Phase 2, `MonitorTarget` and `MonitorCoordinator` can be implemented in parallel; CLI and shared-output refactors depend on their signatures. Test files can be added alongside their owning component.
4. Within Phase 3, `MonitorSettings` and `HealthTracker` changes can run in parallel with HTTP classification changes; final CLI composition depends on both. README updates should follow verified behavior.
5. Complete each phase's automated and manual checks before beginning the next phase. Do not batch all tests until the end.

## Decisions and Scope Boundaries

- Use .NET 8 and pin `System.CommandLine` 2.0.10; rely on current `RootCommand`, validators, async `SetAction`, `ParseResult.GetValue`, and `InvokeAsync` APIs.
- Use 10 seconds as both the omitted interval and timeout default; use 3 as the omitted failure threshold.
- Use exit code `0` for help/clean shutdown, `1` for unexpected application failure, and `2` for parse/validation failure.
- Keep test seams narrow and co-located where the structure did not allocate separate interface files; do not add a DI container or mocking framework.
- Use a shared `HttpClient`, one state tracker and sequential loop per URL, `Task.WhenAll` across URLs, and a serialized shared output sink.
- Include only HTTP GET monitoring, CLI options, stdout/stderr notification behavior, framework-dependent publishing, and tests/documentation described by the design and structure.
- Exclude configuration files, environment settings, persistent logs/history, retries inside a check, response-body checks, authentication, custom headers, service mode, dynamic reconfiguration, external notifications, self-contained packaging, NuGet tool packaging, containers, and CI/CD.
- No `research.md` is required because the repository explicitly marks the task greenfield; `answers.md` supplies the resolved discovery decisions.
