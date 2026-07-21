# Structure Outline

## Approach

Build the `urlmon` C++17 CLI in vertical slices, each runnable end-to-end from `main`. Start with a walking skeleton (build + CLI + config load), then add real HTTP checking, then the monitor loop with transition notifications, then persistent state, then statistics, and finally graceful shutdown and packaging. Each phase compiles, runs, and is independently verifiable. Pure logic (classification, stats) gets unit tests; network behavior is verified manually against httpbin.org.

Every phase crosses the layers it needs (types → module → wiring in `main`/`monitor`). Later phases build on earlier foundations, but if a later phase is dropped, earlier phases remain useful (e.g. Phase 3 is a working transient monitor even without persistence).

---

## Phase 1: Walking skeleton — build system, CLI, config load

Establish the CMake build, dependencies, and a runnable binary that parses CLI flags and loads/validates the YAML config, then prints the parsed config and exits.

**Files**: `CMakeLists.txt`, `src/main.cpp`, `src/config.hpp`, `src/config.cpp`, `config/example.yaml`, `README.md`

**Key changes**:
- CMake: `urlmon` target, C++17, `find_package(CURL REQUIRED)`, `FetchContent` for `yaml-cpp` + `nlohmann/json`, `enable_testing()`.
- `struct UrlSpec { std::string url; int timeout_seconds = 10; };`
- `struct Config { int check_interval_seconds; std::vector<UrlSpec> urls; };`
- `std::optional<Config> load_config(const std::string& path, std::string& error);` — parse + validate (interval ≥ 5, non-empty urls, each url present).
- `struct CliOptions { std::string config_path = "config.yaml"; std::optional<std::string> state_file; bool verbose = false; bool stats_only = false; bool help = false; };`
- `CliOptions parse_args(int argc, char** argv);`
- `int main(...)` — parse args, handle `--help`, load config, print summary, exit non-zero on config error.

**Verify**: `cmake -S . -B build && cmake --build build` succeeds; `./build/urlmon --config config/example.yaml` prints parsed URLs and interval; a malformed config exits non-zero with a clear message; `./build/urlmon --help` prints usage.

---

## Phase 2: HTTP checker + classification (200-only)

Add a libcurl-backed checker that performs a single GET and returns a structured result, plus the pure classification function (up iff HTTP 200). Wire a one-shot check pass into `main` behind the normal run path so each configured URL is checked exactly once and printed.

**Files**: `src/checker.hpp`, `src/checker.cpp`, `src/main.cpp` (wire one pass), `CMakeLists.txt` (add checker + test), `tests/test_classify.cpp`

**Key changes**:
- `enum class Status { Unknown, Up, Down };`
- `struct CheckResult { long http_status = 0; int curl_code = 0; std::string curl_error_name; double total_ms = 0; };`
- `class HttpClient { public: HttpClient(); ~HttpClient(); CheckResult check(const UrlSpec&); };` — RAII around `CURL*`, GET, follow redirects (max 5), per-URL timeout, discard body.
- `Status classify(const CheckResult& r);` — `Up` iff `r.curl_code == 0 && r.http_status == 200`, else `Down`.
- `tests/test_classify.cpp` — cover 200→Up; 301/404/500/503→Down; curl error→Down; status 0→Down.

**Verify**: `ctest --test-dir build` passes `test_classify`; running against a config with `https://httpbin.org/status/200` prints `UP`, and `/status/404`, `/status/503`, and an unreachable host print `DOWN` with detail.

---

## Phase 3: Monitor loop + transition notifications (in-memory state)

Add the scheduled loop that checks all URLs each interval and logs only status transitions, holding last-known status in memory (no persistence yet). This delivers a working transient monitor.

**Files**: `src/notifier.hpp`, `src/notifier.cpp`, `src/monitor.hpp`, `src/monitor.cpp`, `src/main.cpp` (enter loop), `CMakeLists.txt`

**Key changes**:
- `void log_info(const std::string&); void log_error(const std::string&);` — thin stdout/stderr wrappers with ISO 8601 timestamps.
- `void emit_transition(const std::string& url, Status prev, Status now, const CheckResult&);` — fixed-width `DOWN`/`UP` line.
- `struct MonitorContext { Config config; std::map<std::string, Status> status; bool verbose; };`
- `void run_monitor(MonitorContext& ctx, HttpClient& client);` — loop: check each URL, classify, emit on `prev != now && prev != Unknown`, update status, sleep interval. First cycle sets baseline silently.
- Interval sleep is a plain `sleep_for` for now (replaced in Phase 6).

**Verify**: Running against a stable 200 URL logs nothing after baseline (unless `--verbose`); toggling an endpoint between 200 and 503 (e.g. swap config entries) produces exactly one `DOWN` then one `UP` line on change; `--verbose` logs every check.

---

## Phase 4: Persistent state (JSON sidecar)

Persist last-known status per URL to a JSON sidecar and load it on startup so restarts don't re-notify. Reconcile config additions/removals against loaded state.

**Files**: `src/state.hpp`, `src/state.cpp`, `src/monitor.cpp` (load/save integration), `src/main.cpp` (resolve state path), `CMakeLists.txt`

**Key changes**:
- `struct UrlState { Status status = Status::Unknown; std::string last_checked; };`
- `struct StateStore { int version = 1; std::map<std::string, UrlState> urls; };`
- `StateStore load_state(const std::string& path);` — missing/invalid file → empty store.
- `bool save_state(const std::string& path, const StateStore&);` — atomic write (temp file + rename).
- `void reconcile(StateStore&, const Config&);` — add new URLs as `Unknown`, drop removed URLs.
- State path resolution: `--state-file` or derived from config path (`.state.json`).
- Monitor updates `last_checked` and saves after each cycle.

**Verify**: First run creates the state file; kill the process while a URL is `Down`, restart → no duplicate `DOWN` line; adding a URL to config introduces it as `Unknown` (silent baseline); removing a URL drops it from the state file on next save; killing mid-write never leaves a corrupt file.

---

## Phase 5: Response statistics

Accumulate per-URL counters for every response type (HTTP status codes and curl error names), persist them in the state file, and render them via `--stats` and the shutdown summary.

**Files**: `src/stats.hpp`, `src/stats.cpp`, `src/state.cpp` (serialize stats), `src/monitor.cpp` (record each check), `src/main.cpp` (`--stats` path), `CMakeLists.txt` (add stats + test), `tests/test_stats.cpp`

**Key changes**:
- `struct UrlStats { long total_checks = 0, up_checks = 0, down_checks = 0; std::map<long,long> http_status; std::map<std::string,long> curl_error; };`
- `void record(UrlStats&, const CheckResult&, Status);` — bump totals + the right counter map.
- `std::string format_stats(const std::string& url, const UrlStats&);` — block with uptime % and per-key counts.
- Extend `UrlState` with `UrlStats stats;`; extend `load_state`/`save_state` JSON (round-trip counters).
- `main`: when `stats_only`, load state, print `format_stats` for each URL, exit without looping.
- `tests/test_stats.cpp` — record a sequence of results, assert totals/maps; serialize→deserialize round-trip equality.

**Verify**: `ctest` passes `test_stats`; after several cycles `./urlmon --stats` prints per-URL counters matching observed responses; counters persist and continue accumulating across a restart; a URL that saw 200 and 503 shows both keys with correct counts.

---

## Phase 6: Graceful shutdown + packaging

Replace the naive sleep with an interruptible wait, handle `SIGINT`/`SIGTERM` to finish the current cycle, save state, print a stats summary, and exit 0. Finalize README and example config.

**Files**: `src/monitor.cpp`, `src/monitor.hpp`, `src/main.cpp`, `README.md`, `config/example.yaml`

**Key changes**:
- Global `std::atomic<bool> g_shutdown` + `std::condition_variable`; signal handler sets flag and notifies.
- `MonitorContext` gains a shutdown predicate; interval wait uses `cv.wait_for` so signals wake it promptly.
- On shutdown: break loop after current cycle (or immediately during sleep), `save_state`, print `format_stats` summary, return 0.
- README: build steps, dependencies (curl/OpenSSL), config schema, classification rule (200-only), stats/flags, lifecycle notes.

**Verify**: `Ctrl+C` during sleep exits within a fraction of a second; `Ctrl+C` mid-cycle exits after the current URL/cycle; on exit the state file is current and a stats summary prints; exit code is 0; README instructions reproduce a working build from clean.

---

## Testing Checkpoints

- **After P1**: Project builds; CLI + config parsing/validation work; `--help` and error paths correct.
- **After P2**: `test_classify` green; single GET checks classify correctly (200 = up, everything else = down) against httpbin.
- **After P3**: Loop logs only transitions (baseline silent); `--verbose` logs all checks. Working in-memory monitor.
- **After P4**: State persists; restarts don't re-notify; config add/remove reconciled; atomic writes safe.
- **After P5**: `test_stats` green; `--stats` and persisted counters accurately reflect all observed response types across restarts.
- **After P6**: Signal-driven graceful shutdown saves state and prints summary; README enables a clean-room build.
