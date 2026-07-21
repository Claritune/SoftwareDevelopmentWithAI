# Design Discussion

## Current State

Greenfield project. The repository contains only the goal document, QRSPI workflow artifacts, and Cursor agent configuration — no application source code, build files, tests, or dependency manifests.

**What exists today:**

| Artifact | Purpose |
|---|---|
| `goal.md:3` | One-line product goal: URL uptime monitor with scheduled checks and down/up notifications |
| `.cursor/hooks.json:4-16` | Agent hooks that block `rm` shell commands and the Delete tool |
| `.cursor/hooks/block-rm.sh:6-12` | Denies `rm` with a policy message |
| `.cursor/hooks/block-delete.sh:6-10` | Denies file deletion via the Delete tool |
| `thoughts/qrspi/2026-07-14-url-monitor-cli/answers.md` | Resolved architectural decisions from the Question phase |

There are no documented C++ coding standards, no existing module layout, and no CI configuration. The project directory name (`url_monitor_cli_cpp`) is the only hint at implementation language.

## Desired End State

A single C++17 executable (`urlmon`) that:

1. Reads a YAML config file specifying URLs to monitor, a global check interval, and optional per-URL timeouts.
2. Runs as a foreground long-lived process, checking each URL sequentially on schedule.
3. Classifies each URL as **up** or **down** — **only HTTP 200 is success**; all other outcomes are down.
4. Persists last-known state and cumulative response statistics per URL in a JSON sidecar file.
5. Logs state transitions (down → up, up → down) to stdout with ISO 8601 timestamps.
6. Handles `SIGINT`/`SIGTERM` gracefully — finishes the current check, saves state, prints stats summary, exits cleanly.

**Verification checklist:**

- [ ] `./urlmon --config config.yaml` starts, loads config, and enters the check loop.
- [ ] Pointing at `https://httpbin.org/status/200` logs periodic checks with no transition events.
- [ ] Pointing at `https://httpbin.org/status/404` or `/status/503` triggers a `DOWN` log line once (non-200 = down).
- [ ] Pointing at an unreachable host triggers a `DOWN` log line with curl error detail.
- [ ] When the URL recovers to HTTP 200, a single `UP` log line appears.
- [ ] Restarting the process while a URL is down does **not** re-emit the `DOWN` notification.
- [ ] After several check cycles, `./urlmon --stats --config config.yaml` prints per-URL counters for each HTTP status and curl error type seen.
- [ ] Stats counters survive restart (loaded from state file).
- [ ] `Ctrl+C` exits within one check cycle, preserves state on disk, and prints a stats summary.
- [ ] `./urlmon --help` documents available flags.

## Patterns to Follow

**From existing constraints (agent workflow only — not application patterns):**

- `.cursor/hooks.json:4-16` — Destructive operations are restricted in the agent environment. During implementation, prefer editing files over deleting and recreating them. This does not affect runtime behavior of `urlmon`.

**Conventions to establish (no prior codebase to match):**

- **Flat module layout under `src/`** — one concern per translation unit (`config`, `checker`, `state`, `stats`, `notifier`, `monitor`, `main`). Keeps v1 simple; no premature layering.
- **Header/implementation pairs** — `.hpp` for public interfaces, `.cpp` for definitions. Minimal header-only except third-party JSON.
- **RAII everywhere** — libcurl handles wrapped in a small `HttpClient` class; no raw `CURL*` leaking across modules.
- **Explicit error types** — return `std::optional<T>` or a lightweight `Result<T, Error>` for operations that can fail (config load, HTTP check, state I/O). Avoid exceptions for expected failures.
- **No global mutable state** — pass a `MonitorContext` struct holding config, state store, and shutdown flag.

**Patterns to avoid:**

- Do not introduce a plugin/notification-channel abstraction in v1 — stdout logging is the only channel; a simple free function or small class is enough.
- Do not add a thread pool or async I/O — sequential checks match v1 scope and simplify state management.
- Do not embed a full logging framework (spdlog, etc.) — a thin `log_info`/`log_error` wrapper around `std::cout`/`std::cerr` suffices.

## Design Decisions

1. **Executable name**: `urlmon` — short, descriptive, matches CLI convention.

2. **Build system**: CMake 3.16+ with a single `urlmon` target. Find libcurl via `find_package(CURL REQUIRED)`. Pull in **yaml-cpp** and **nlohmann/json** via `FetchContent` to avoid system-package variance during development.

3. **Config format (YAML)**:
   ```yaml
   check_interval_seconds: 60
   urls:
     - url: https://example.com
       timeout_seconds: 10        # optional, default 10
     - url: https://api.example.com/health
   ```
   - Global `check_interval_seconds` (required, minimum 5).
   - `urls` is a non-empty list; each entry has `url` (required) and optional `timeout_seconds`.
   - No notification settings block in v1 — notifications are always stdout.

4. **CLI surface**:
   - `--config <path>` (default: `./config.yaml`) — path to YAML config.
   - `--state-file <path>` (default: derived — replace config extension with `.state.json`, e.g. `config.yaml` → `config.state.json`).
   - `--verbose` — log every check result, not just transitions.
   - `--stats` — print the accumulated per-URL response statistics from the state file and exit (does not enter the monitor loop).
   - `--help` — usage text.
   - Process exits non-zero on config parse errors or missing config file.

5. **HTTP checking (libcurl)**:
   - Method: `GET` (not HEAD) — some endpoints don't support HEAD; body is discarded after headers.
   - Follow redirects (up to 5).
   - Timeout: per-URL `timeout_seconds` mapped to `CURLOPT_TIMEOUT`.
   - Capture: HTTP status code, curl error code, total time.
   - Classification logic:
     - **Up** only if HTTP status == 200.
     - **Down** for every other outcome: curl error (timeout, DNS, connection, SSL), status == 0, or any HTTP status other than 200 (including 3xx, 4xx, and 5xx).
   - Reuse one `CURL*` handle across checks within a cycle (reset between requests).

6. **Response statistics**:
   - For every check, increment a counter for the observed outcome per URL.
   - Two counter maps per URL: `http_status` (keyed by numeric HTTP status code, e.g. `200`, `404`, `503`) and `curl_error` (keyed by curl error name, e.g. `operation_timedout`, `couldnt_resolve_host`, `ssl_connect_error`).
   - Counters are cumulative across the process lifetime and persisted, so they survive restarts.
   - Also track `total_checks`, `up_checks`, and `down_checks` per URL for a quick uptime ratio.
   - `--stats` and the shutdown summary render these as a per-URL table to stdout.

7. **State persistence (JSON sidecar)**:
   ```json
   {
     "version": 1,
     "urls": {
       "https://example.com": {
         "status": "up",
         "last_checked": "2026-07-14T10:00:00Z",
         "stats": {
           "total_checks": 120,
           "up_checks": 118,
           "down_checks": 2,
           "http_status": { "200": 118, "503": 2 },
           "curl_error": { "operation_timedout": 0 }
         }
       }
     }
   }
   ```
   - Keyed by exact URL string from config.
   - Written atomically: write to temp file, then rename (avoids corrupt state on crash mid-write).
   - On first run (no state file): initialize all URLs as `unknown` with zeroed stats; first check sets baseline **without** emitting a transition notification, but **does** count toward stats. Only subsequent status changes trigger logs.
   - On config change (URL added/removed): new URLs start as `unknown` with zeroed stats; removed URLs are dropped from state (and their stats discarded) on save.

8. **Monitor loop**:
   ```
   load config → load state → install signal handlers
   loop until shutdown requested:
     for each url in config.urls (sequential):
       result = checker.check(url)
       new_status = classify(result)              # up iff HTTP 200
       stats.record(url, result)                  # count status code / curl error
       if new_status != previous_status AND previous_status != unknown:
         notifier.emit_transition(url, previous, new, result)
       update state[url] = new_status
     save state
     sleep until next interval OR shutdown signal
   on shutdown: save state, print stats summary, exit 0
   ```
   - Sleep implemented with `std::condition_variable` + timed wait so signals wake the thread promptly.

9. **Notification format (stdout)**:
   ```
   2026-07-14T10:05:00Z DOWN  https://example.com  (HTTP 503, 1234ms)
   2026-07-14T10:10:00Z UP    https://example.com  (HTTP 200, 456ms)
   ```
   - Fixed-width status column for readability.
   - Verbose mode adds a line per check regardless of transition.

10. **Stats output format (stdout)** — used by `--stats` and the shutdown summary:
   ```
   https://example.com   checks=120  up=118  down=2  uptime=98.3%
     HTTP  200: 118   503: 2
     curl  (none)
   ```
   - One block per URL; HTTP status and curl-error counters listed only for observed keys.

11. **Project layout**:
   ```
   url_monitor_cli_cpp/
   ├── CMakeLists.txt
   ├── README.md
   ├── config/
   │   └── example.yaml
   ├── src/
   │   ├── main.cpp
   │   ├── config.{hpp,cpp}
   │   ├── checker.{hpp,cpp}
   │   ├── state.{hpp,cpp}
   │   ├── stats.{hpp,cpp}
   │   ├── notifier.{hpp,cpp}
   │   └── monitor.{hpp,cpp}
   └── tests/
       ├── test_classify.cpp    # unit test for up/down logic (200-only rule)
       └── test_stats.cpp       # unit test for counter accumulation + serialization
   ```

12. **Testing strategy**: Focused unit tests for the status-classification function (200-only rule) and the stats accumulator (counting + JSON round-trip), both pure logic with no network. Manual/integration verification via httpbin.org endpoints. No mock HTTP server in v1.

## What We're NOT Doing

- External notification channels (email, Slack, webhooks, push).
- Web dashboard or REST API for status.
- Historical uptime metrics, SLA reporting, or time-series storage.
- Concurrent/parallel URL checks or connection pooling beyond curl handle reuse.
- Per-URL check intervals (global interval only in v1).
- Authentication, multi-user support, or encrypted config.
- Daemonization, PID files, or systemd unit generation (user manages process lifecycle).
- IPv6-specific handling beyond what libcurl provides by default.
- Retry/backoff within a single check cycle (one attempt per URL per cycle).
- Config hot-reload (restart required to pick up config changes).

## Open Risks

| Risk | Mitigation |
|---|---|
| **yaml-cpp / nlohmann FetchContent build time** | Pin versions in CMake; document expected first-build duration in README. |
| **False positives on flaky networks** | v1 accepts this; future versions could add consecutive-failure threshold. Document in README. |
| **Strict 200-only rule flags 3xx/401/403 as down** | Document clearly: any non-200 (including redirects and auth-required) counts as down. Redirect following means a final 200 after redirects still counts as up. Users must point at endpoints that ultimately return 200. |
| **Unbounded stats growth** | Counters are keyed by status code / error name (small bounded key space), so per-URL stats size is capped regardless of runtime. |
| **State file/config URL mismatch after edits** | State reconciliation on load handles add/remove; document that URL string changes reset history. |
| **libcurl/OpenSSL not installed on target machine** | README lists build and runtime dependencies; CMake fails early with clear message if curl not found. |
| **No coding-style guide exists yet** | Establish conventions in this design; first implementation pass sets the precedent. |
