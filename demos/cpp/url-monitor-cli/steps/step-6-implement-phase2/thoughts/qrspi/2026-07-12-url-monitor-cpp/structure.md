# Structure Outline

## Approach
Build the URL monitor in two vertical phases. Phase 1 delivers a working CLI that performs a single check round with transition detection (proving the core logic works end-to-end). Phase 2 adds the poll loop, logging, and graceful shutdown (making it a real monitoring tool).

## Phase 1: Single Check Round with Transition Detection

Delivers: CMake project skeleton, CLI argument parsing, HTTP health check, state machine with DOWN/UP transition logic, stdout notifications, unit tests for transition logic.

After this phase, the user can run `./url-monitor https://example.com` and see a single check result with transition output.

**Files**:
- `CMakeLists.txt` — project definition, FetchContent for cpr, CLI11, Catch2
- `src/main.cpp` — entry point, CLI setup, orchestrates single check round
- `src/checker.h` / `src/checker.cpp` — HTTP health check (wraps cpr::Get)
- `src/monitor.h` / `src/monitor.cpp` — state machine per URL (tracks failures, detects transitions)
- `src/config.h` — struct holding parsed CLI options
- `tests/test_monitor.cpp` — Catch2 tests for transition logic

**Key changes**:
- `struct CheckResult { int status_code; long elapsed_ms; bool success; std::string error; }`
- `CheckResult check_url(const std::string& url, int timeout_seconds)`
- `struct UrlState { int consecutive_failures; bool is_down; }`
- `struct Transition { enum Type { DOWN, UP }; Type type; std::string url; std::string reason; }`
- `std::optional<Transition> update_state(UrlState& state, const CheckResult& result, int threshold)`

**Verify**:
- `cmake -B build && cmake --build build` compiles without errors
- `./build/url-monitor --help` prints usage
- `./build/url-monitor https://httpbin.org/status/200` performs one check, prints result to stderr
- `ctest --test-dir build` — all unit tests pass

---

## Phase 2: Continuous Monitoring with Logging

Delivers: Poll loop with configurable interval, signal handling for graceful shutdown, file logging support, formatted timestamps.

After this phase, the tool runs continuously, printing transitions to stdout and logs to stderr/file.

**Files**:
- `src/main.cpp` — add poll loop, signal handler
- `src/logger.h` / `src/logger.cpp` — timestamp formatting, stderr/file output
- `src/monitor.h` / `src/monitor.cpp` — add `run_loop()` orchestration
- `tests/test_monitor.cpp` — add tests for repeated state updates

**Key changes**:
- `std::atomic<bool> g_running{true}` — signal flag
- `void signal_handler(int)` — sets `g_running = false`
- `void run_monitor_loop(const Config& config)` — main loop: check all URLs, log results, sleep, repeat
- `std::string format_timestamp()` — ISO 8601 UTC timestamp
- `void log_check(...)` — write to stderr and optionally to file

**Verify**:
- `./build/url-monitor https://httpbin.org/status/200 --interval 5` runs continuously, logs to stderr
- Ctrl+C stops cleanly (prints shutdown message)
- `./build/url-monitor https://httpbin.org/status/503 --failure-threshold 2 --interval 2` triggers DOWN after 2 checks
- `--log-file test.log` appends check logs to file
- `ctest --test-dir build` — all tests still pass

## Testing Checkpoints

| After Phase | What should be true |
|-------------|---------------------|
| Phase 1 | Binary compiles, `--help` works, single check executes, transition logic unit-tested |
| Phase 2 | Continuous loop runs, Ctrl+C shuts down, transitions print to stdout, logs to stderr/file |
