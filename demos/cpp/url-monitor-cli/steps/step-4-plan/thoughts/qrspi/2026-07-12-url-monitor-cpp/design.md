# Design Discussion

## Current State
Empty greenfield project with only `goal.md`. No application code, no build system, no dependencies. Target language: C++17.

## Desired End State
A compiled C++ CLI binary (`url-monitor`) that:
- Accepts one or more URLs as positional arguments
- Performs HTTP health checks on a configurable interval
- Tracks consecutive failures per URL (configurable threshold)
- Prints DOWN/UP transition notifications to stdout
- Logs routine checks to stderr or an optional log file
- Runs in a foreground loop until SIGINT (Ctrl+C)
- Shuts down gracefully on signal

Verification: `./url-monitor https://httpbin.org/status/200 --interval 5` prints check logs to stderr and stays running; killing a test server triggers a DOWN notification on stdout.

## Patterns to Follow
- **Modern C++17**: use `std::optional`, `std::string_view`, structured bindings, `<chrono>` for time
- **CMake 3.14+** with FetchContent for dependency management
- **Source layout**: `src/` for application code, `tests/` for test code, `include/` if headers need to be separate
- **Single-responsibility files**: one class/concern per `.cpp`/`.h` pair

## Design Decisions

1. **Build system**: CMake with FetchContent — pulls cpr, CLI11, and Catch2 at configure time. No system-level package installs beyond cmake.

2. **HTTP client**: cpr (C++ Requests) — wraps libcurl with a clean API. `cpr::Get(url, timeout)` returns status code and elapsed time.

3. **CLI parsing**: CLI11 — header-only, type-safe, auto-generates `--help`.

4. **State tracking**: Simple struct per URL holding `consecutive_failures` count and `is_down` boolean. Transition fires when `consecutive_failures` crosses the threshold (going down) or a success occurs while `is_down` is true (coming back up).

5. **Logging**: `std::cerr` for routine check output. `std::ofstream` append for `--log-file`. No logging library — the output format is simple enough.

6. **Signal handling**: `std::signal(SIGINT, handler)` sets an `std::atomic<bool>` flag checked in the poll loop.

7. **No concurrency**: Sequential URL checks in a `for` loop. Simpler code, acceptable for <50 URLs.

8. **Test strategy**: Unit tests for the state machine (transition logic) using Catch2. Integration test optional — hard to test HTTP without a mock server.

## What We're NOT Doing
- No async/parallel checks
- No config file (YAML/JSON) — CLI args only
- No Slack/email/webhook notifications — stdout only
- No persistent state (SQLite, files) — in-memory only
- No retry with backoff — simple consecutive failure count
- No HTTP response body inspection — status code only
- No TLS certificate validation options
- No Docker/packaging

## Open Risks
- cpr's FetchContent pull can be slow on first configure (~30s to download libcurl + cpr)
- Signal handling in C++ is limited — only async-signal-safe operations in handler (setting an atomic bool is fine)
- `std::this_thread::sleep_for` is the simplest sleep but doesn't wake early on signal — acceptable lag up to one interval before shutdown
