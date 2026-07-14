# Implementation Plan

## Overview

Build `urlmon`, a single C++17 CLI executable that monitors a YAML-configured list of URLs on a schedule, classifies each as up (HTTP 200 only) or down (everything else), logs state transitions to stdout, persists last-known state plus cumulative response statistics in a JSON sidecar, and shuts down gracefully on SIGINT/SIGTERM.

Build commands used throughout:

```bash
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

**Environment note**: the dev machine has CMake 4.4. CMake 4 refuses to configure sub-projects whose `cmake_minimum_required` is below 3.5, which includes the pinned `yaml-cpp 0.8.0`. Set `CMAKE_POLICY_VERSION_MINIMUM 3.5` before `FetchContent_MakeAvailable` to keep the pinned tags buildable. Pin `nlohmann/json v3.12.0` (CMake-4-compatible release).

**Machine-specific workaround (discovered in Phase 1)**: this Mac's Command Line Tools install has a broken toolchain libc++ header directory (`/Library/Developer/CommandLineTools/usr/include/c++/v1` contains only 11 files — `<cstdlib>` etc. are missing), so any C++ compile of standard headers fails. The SDK copy of the headers is intact. Configure with:

```bash
cmake -S . -B build -DCMAKE_CXX_FLAGS="-nostdinc++ -isystem /Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/c++/v1"
```

This is a local-machine issue (fixable permanently by reinstalling CLT), not a project requirement — `CMakeLists.txt` stays portable.

---

## Phase 1: Walking skeleton — build system, CLI, config load

### Changes

#### 1. Build system
**File**: `CMakeLists.txt`
**Action**: create

```cmake
cmake_minimum_required(VERSION 3.16)
project(urlmon CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(CURL REQUIRED)

include(FetchContent)
# yaml-cpp 0.8.0 declares cmake_minimum_required(3.4); CMake 4 needs this floor.
set(CMAKE_POLICY_VERSION_MINIMUM 3.5)

set(YAML_CPP_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(YAML_CPP_BUILD_TOOLS OFF CACHE BOOL "" FORCE)
FetchContent_Declare(yaml-cpp
  GIT_REPOSITORY https://github.com/jbeder/yaml-cpp.git
  GIT_TAG 0.8.0)

set(JSON_BuildTests OFF CACHE INTERNAL "")
FetchContent_Declare(json
  GIT_REPOSITORY https://github.com/nlohmann/json.git
  GIT_TAG v3.12.0)

FetchContent_MakeAvailable(yaml-cpp json)

add_library(urlmon_core STATIC
  src/config.cpp)
target_include_directories(urlmon_core PUBLIC src)
target_link_libraries(urlmon_core PUBLIC
  CURL::libcurl yaml-cpp::yaml-cpp nlohmann_json::nlohmann_json)

add_executable(urlmon src/main.cpp)
target_link_libraries(urlmon PRIVATE urlmon_core)

enable_testing()
```

(`urlmon_core` exists so Phase 2+ unit tests can link the non-`main` translation units; `urlmon` stays the single executable target.)

#### 2. Config types and loader
**File**: `src/config.hpp`
**Action**: create

```cpp
#pragma once
#include <optional>
#include <string>
#include <vector>

struct UrlSpec {
  std::string url;
  int timeout_seconds = 10;
};

struct Config {
  int check_interval_seconds = 0;
  std::vector<UrlSpec> urls;
};

struct CliOptions {
  std::string config_path = "config.yaml";
  std::optional<std::string> state_file;
  bool verbose = false;
  bool stats_only = false;
  bool help = false;
  std::optional<std::string> error;  // set on unknown/malformed flag
};

std::optional<Config> load_config(const std::string& path, std::string& error);
CliOptions parse_args(int argc, char** argv);
std::string usage_text();
```

**File**: `src/config.cpp`
**Action**: create

- `load_config`: wrap `YAML::LoadFile` in try/catch (yaml-cpp throws on parse/missing file — convert to `error` string + `std::nullopt`). Validate:
  - `check_interval_seconds` present, integer, `>= 5`
  - `urls` present, non-empty sequence
  - each entry has non-empty `url`; optional `timeout_seconds` (integer `>= 1`, default 10)
  - On any violation: set a specific `error` message, return `std::nullopt`.
- `parse_args`: manual loop over `argv`. Flags: `--config <path>`, `--state-file <path>`, `--verbose`, `--stats`, `--help`. A flag missing its value argument or an unknown flag sets `error`.
- `usage_text`: multi-line usage string listing all flags with defaults.

#### 3. Entry point
**File**: `src/main.cpp`
**Action**: create

```cpp
int main(int argc, char** argv) {
  CliOptions opts = parse_args(argc, argv);
  if (opts.error) { std::cerr << *opts.error << "\n" << usage_text(); return 2; }
  if (opts.help)  { std::cout << usage_text(); return 0; }

  std::string err;
  auto config = load_config(opts.config_path, err);
  if (!config) { std::cerr << "config error: " << err << "\n"; return 1; }

  // Phase 1 only: print parsed config and exit.
  std::cout << "interval: " << config->check_interval_seconds << "s\n";
  for (const auto& u : config->urls)
    std::cout << "url: " << u.url << " (timeout " << u.timeout_seconds << "s)\n";
  return 0;
}
```

#### 4. Example config
**File**: `config/example.yaml`
**Action**: create

```yaml
check_interval_seconds: 15
urls:
  - url: https://httpbin.org/status/200
    timeout_seconds: 10
  - url: https://httpbin.org/status/503
```

#### 5. README stub
**File**: `README.md`
**Action**: create — project name, one-paragraph description, build prerequisites (CMake ≥ 3.16, C++17 compiler, libcurl dev headers), build commands, note that first configure fetches yaml-cpp/nlohmann-json. Full docs land in Phase 6.

### Verification

#### Automated
- [x] `cmake -S . -B build && cmake --build build` succeeds
- [x] `./build/urlmon --help` exits 0 and prints usage
- [x] `./build/urlmon --config config/example.yaml` exits 0 and prints interval + both URLs
- [x] `./build/urlmon --config missing.yaml` exits non-zero with a clear message
- [x] Malformed config (e.g. `check_interval_seconds: 2`) exits non-zero naming the violation

#### Manual
- [ ] Usage text reads sensibly and documents all five flags

---

## Phase 2: HTTP checker + classification (200-only)

### Changes

#### 1. Checker interface
**File**: `src/checker.hpp`
**Action**: create

```cpp
#pragma once
#include <string>
#include "config.hpp"

enum class Status { Unknown, Up, Down };

struct CheckResult {
  long http_status = 0;
  int curl_code = 0;              // CURLcode as int; 0 == CURLE_OK
  std::string curl_error_name;    // stable key, e.g. "operation_timedout"; empty on success
  double total_ms = 0;
};

Status classify(const CheckResult& r);       // Up iff curl_code == 0 && http_status == 200
const char* status_name(Status s);           // "unknown" / "up" / "down"
std::string curl_error_key(int curl_code);   // stable snake_case key for a CURLcode

class HttpClient {
 public:
  HttpClient();                // curl_global_init + curl_easy_init
  ~HttpClient();               // cleanup both
  HttpClient(const HttpClient&) = delete;
  HttpClient& operator=(const HttpClient&) = delete;
  CheckResult check(const UrlSpec& spec);
 private:
  void* handle_ = nullptr;     // CURL*; kept void* so the header needs no curl include
};
```

#### 2. Checker implementation
**File**: `src/checker.cpp`
**Action**: create

- `HttpClient::check`: `curl_easy_reset(handle_)` then set: `CURLOPT_URL`, `CURLOPT_FOLLOWLOCATION 1`, `CURLOPT_MAXREDIRS 5`, `CURLOPT_TIMEOUT spec.timeout_seconds`, `CURLOPT_NOSIGNAL 1`, `CURLOPT_WRITEFUNCTION` discarding the body, `CURLOPT_USERAGENT "urlmon/1.0"`. After `curl_easy_perform`: read `CURLINFO_RESPONSE_CODE` and `CURLINFO_TOTAL_TIME` (seconds → ms). On non-zero `CURLcode`, fill `curl_code` + `curl_error_name = curl_error_key(code)`.
- `curl_error_key`: switch over common codes → design's snake_case names (`couldnt_resolve_host`, `couldnt_connect`, `operation_timedout`, `ssl_connect_error`, `peer_failed_verification`, `too_many_redirects`, `send_error`, `recv_error`, `got_nothing`, `url_malformat`, `unsupported_protocol`); default `"curl_error_<n>"`.
- `classify` and `status_name` as specified above.

#### 3. One-shot wiring in main
**File**: `src/main.cpp`
**Action**: modify — replace the Phase-1 config printout: construct `HttpClient`, loop over `config->urls`, print one line per check:
`<url>  UP|DOWN  (HTTP <status>, <ms>ms)` or `(curl: <error_name>)` on curl failure.

#### 4. Unit test
**File**: `tests/test_classify.cpp`
**Action**: create — assert-based `main` (no framework), constructing `CheckResult` values directly (no network):
- `{200, 0}` → `Up`
- `{301, 0}`, `{404, 0}`, `{500, 0}`, `{503, 0}` → `Down`
- `{0, CURLE_OPERATION_TIMEDOUT}` → `Down`
- `{0, 0}` (status 0, no curl error) → `Down`
- `curl_error_key(28) == "operation_timedout"`, `curl_error_key(6) == "couldnt_resolve_host"`

#### 5. Build updates
**File**: `CMakeLists.txt`
**Action**: modify — add `src/checker.cpp` to `urlmon_core`; add:

```cmake
add_executable(test_classify tests/test_classify.cpp)
target_link_libraries(test_classify PRIVATE urlmon_core)
add_test(NAME test_classify COMMAND test_classify)
```

### Verification

#### Automated
- [x] Build succeeds; `ctest --test-dir build --output-on-failure` passes `test_classify`
- [x] `./build/urlmon --config config/example.yaml` prints `UP` for `/status/200` and `DOWN` for `/status/503`
      (httpbin.org itself was serving 503 during implementation; verified against
      `https://example.com` and `https://httpbingo.org/status/{200,503,404}` instead)

#### Manual
- [x] A config pointing at `/status/404` prints `DOWN` with `HTTP 404` (via httpbingo.org)
- [x] A config with an unreachable host (e.g. `https://no-such-host.invalid`) prints `DOWN` with a curl error name (`couldnt_resolve_host`)

---

## Phase 3: Monitor loop + transition notifications (in-memory state)

### Changes

#### 1. Notifier
**File**: `src/notifier.hpp` / `src/notifier.cpp`
**Action**: create

```cpp
#pragma once
#include <string>
#include "checker.hpp"

std::string iso8601_now();  // UTC, "%Y-%m-%dT%H:%M:%SZ" via gmtime_r + strftime
void log_info(const std::string& msg);   // "<ts> <msg>" to stdout, flushed
void log_error(const std::string& msg);  // "<ts> ERROR <msg>" to stderr
void emit_transition(const std::string& url, Status prev, Status now,
                     const CheckResult& r);
void log_check(const std::string& url, Status s, const CheckResult& r); // verbose mode
```

- `emit_transition` output format (fixed-width status column):
  `2026-07-14T10:05:00Z DOWN  https://example.com  (HTTP 503, 1234ms)` — curl-failure detail renders as `(curl: operation_timedout)`. Share a `result_detail(const CheckResult&)` helper with `log_check`.

#### 2. Monitor loop
**File**: `src/monitor.hpp` / `src/monitor.cpp`
**Action**: create

```cpp
#pragma once
#include <map>
#include "checker.hpp"
#include "config.hpp"

struct MonitorContext {
  Config config;
  std::map<std::string, Status> status;  // last known per URL
  bool verbose = false;
};

int run_monitor(MonitorContext& ctx, HttpClient& client);
```

- `run_monitor` loop body: for each `UrlSpec` — `check`, `classify`, `log_check` when verbose, `emit_transition` only when `prev != now && prev != Status::Unknown`, then `ctx.status[url] = now`. First-ever check of a URL (prev `Unknown`) sets the baseline silently.
- Interval wait: plain `std::this_thread::sleep_for(check_interval_seconds)` for this phase (replaced in Phase 6).

#### 3. Wiring
**Files**: `src/main.cpp`, `CMakeLists.txt`
**Action**: modify — `main` builds a `MonitorContext` and calls `run_monitor` instead of the one-shot pass; add `src/notifier.cpp`, `src/monitor.cpp` to `urlmon_core`.

### Verification

#### Automated
- [x] Build + `ctest` still pass
- [x] Two cycles against a stable `/status/200` URL produce no transition lines after baseline
- [x] With `--verbose`, every check logs a line

#### Manual
- [x] Swap a config entry between `/status/200` and `/status/503` across restarts of the endpoint (or edit config + restart): exactly one `DOWN` line on failure, one `UP` line on recovery
      (verified with a local toggleable HTTP server on 127.0.0.1:8642)

---

## Phase 4: Persistent state (JSON sidecar)

### Changes

#### 1. State store
**File**: `src/state.hpp`
**Action**: create

```cpp
#pragma once
#include <map>
#include <string>
#include "checker.hpp"
#include "config.hpp"

struct UrlState {
  Status status = Status::Unknown;
  std::string last_checked;  // ISO 8601, empty if never
};

struct StateStore {
  int version = 1;
  std::map<std::string, UrlState> urls;
};

StateStore load_state(const std::string& path);              // missing/invalid → empty store
bool save_state(const std::string& path, const StateStore&); // atomic: tmp + rename
void reconcile(StateStore& store, const Config& config);
std::string derive_state_path(const std::string& config_path); // strip ext, + ".state.json"
```

**File**: `src/state.cpp`
**Action**: create

- `load_state`: read file; on open failure or `nlohmann::json::parse` error return empty store (log a warning via `log_error` for a corrupt file, silent for missing). Map `"up"/"down"/"unknown"` strings ↔ `Status`.
- `save_state`: serialize (2-space indent), write to `path + ".tmp"`, `std::rename` onto `path`. Return false (and `log_error`) on I/O failure.
- `reconcile`: insert missing config URLs as default `UrlState`; erase store URLs absent from config.
- `derive_state_path("config.yaml")` → `"config.state.json"`; no-extension paths just append `.state.json`.

#### 2. Monitor integration
**Files**: `src/monitor.hpp`, `src/monitor.cpp`
**Action**: modify — `MonitorContext` replaces the bare status map with `StateStore state;` plus `std::string state_path;`. Loop reads `prev` from `state.urls[url].status`, writes back status + `last_checked = iso8601_now()`, and calls `save_state` once per cycle after all URLs are checked.

#### 3. Main wiring
**File**: `src/main.cpp`
**Action**: modify — resolve state path (`opts.state_file` else `derive_state_path(opts.config_path)`), `load_state`, `reconcile` against config, pass into context.

#### 4. Build
**File**: `CMakeLists.txt`
**Action**: modify — add `src/state.cpp` to `urlmon_core`.

### Verification

#### Automated
- [x] Build + `ctest` pass
- [x] First run creates `<config>.state.json` with both URLs and valid JSON
- [x] Restart while a URL is `down` re-emits **no** `DOWN` line (baseline restored from file)
- [x] Adding a URL to config → appears as `unknown`, checked silently; removing one → dropped from the file on next save

#### Manual
- [x] Kill the process mid-run repeatedly; state file always parses (atomic rename, never truncated)
      (8 kill -9 iterations against the local toggle server; JSON parsed every time)

---

## Phase 5: Response statistics

### Changes

#### 1. Stats module
**File**: `src/stats.hpp`
**Action**: create

```cpp
#pragma once
#include <map>
#include <string>
#include "checker.hpp"

struct UrlStats {
  long total_checks = 0, up_checks = 0, down_checks = 0;
  std::map<long, long> http_status;        // status code → count (only when curl_code == 0 and status != 0)
  std::map<std::string, long> curl_error;  // error name → count
};

void record(UrlStats& s, const CheckResult& r, Status st);
std::string format_stats(const std::string& url, const UrlStats& s);
```

**File**: `src/stats.cpp`
**Action**: create

- `record`: bump `total_checks` and `up_checks`/`down_checks`; on curl failure bump `curl_error[r.curl_error_name]`, otherwise bump `http_status[r.http_status]`.
- `format_stats` renders (uptime = up/total, one decimal; `(none)` for empty maps):

```
https://example.com   checks=120  up=118  down=2  uptime=98.3%
  HTTP  200: 118   503: 2
  curl  (none)
```

#### 2. State serialization
**Files**: `src/state.hpp`, `src/state.cpp`
**Action**: modify — `UrlState` gains `UrlStats stats;`. `load_state`/`save_state` round-trip the `stats` object per the design's JSON schema (`total_checks`, `up_checks`, `down_checks`, `http_status` object keyed by stringified code, `curl_error` object). Missing `stats` key on load → zeroed stats.

#### 3. Monitor + main
**Files**: `src/monitor.cpp`, `src/main.cpp`
**Action**: modify — monitor calls `record(state.urls[url].stats, result, now)` for every check (including baseline). `main`: when `opts.stats_only`, load state, print `format_stats` for each stored URL, exit 0 without checking anything.

#### 4. Unit test
**File**: `tests/test_stats.cpp`
**Action**: create — assert-based:
- Record 200/200/503/timeout sequence → totals 4/2/2, `http_status[200]==2`, `http_status[503]==1`, `curl_error["operation_timedout"]==1`
- Serialize a `StateStore` with stats via `save_state` to a temp path, `load_state` it back, assert field-for-field equality
- `format_stats` output contains `uptime=50.0%` for the sequence above

#### 5. Build
**File**: `CMakeLists.txt`
**Action**: modify — add `src/stats.cpp` to `urlmon_core`; add `test_stats` executable + `add_test` (same pattern as `test_classify`).

### Verification

#### Automated
- [ ] `ctest --test-dir build --output-on-failure` passes both tests
- [ ] After ≥2 cycles, `./build/urlmon --stats --config config/example.yaml` prints per-URL blocks whose counters match observed responses
- [ ] Counters continue accumulating across a restart (run, note totals, run again, totals grew)

#### Manual
- [ ] A URL that saw both 200 and 503 shows both keys with correct counts

---

## Phase 6: Graceful shutdown + packaging

### Changes

#### 1. Signal-aware interruptible wait
**Files**: `src/monitor.cpp`, `src/monitor.hpp`
**Action**: modify

- File-scope in `monitor.cpp`: `std::atomic<bool> g_shutdown{false};` and `extern "C" void handle_signal(int) { g_shutdown.store(true); }` — the handler only sets the atomic (async-signal-safe). **Deviation from structure.md**: no `condition_variable` notify from the handler (`notify_all` is not async-signal-safe); instead the interval wait loops over `sleep_for(200ms)` slices checking `g_shutdown`, giving ≤200 ms wake-up latency, which meets the "fraction of a second" requirement.
- `run_monitor`: install `SIGINT`/`SIGTERM` via `std::signal` at loop start; check `g_shutdown` before each URL within a cycle (finish the in-flight check, then break); on shutdown `save_state`, print `format_stats` summary for all URLs, return 0.
- `shutdown_requested()` accessor exposed in `monitor.hpp` if `main` needs it.

#### 2. Main exit path
**File**: `src/main.cpp`
**Action**: modify — `return run_monitor(ctx, client);` (exit code 0 on graceful shutdown).

#### 3. Documentation
**File**: `README.md`
**Action**: modify — full docs: dependencies (CMake ≥ 3.16, C++17 compiler, libcurl + TLS), build steps, config schema with example, **classification rule (200-only, redirects followed — final 200 counts as up; 3xx/4xx/5xx/curl errors/status 0 are down)**, all CLI flags, state-file behavior (sidecar path derivation, atomic writes, restart semantics), stats output, graceful-shutdown lifecycle, known limitations (no retries, flaky-network false positives, global interval only).

**File**: `config/example.yaml`
**Action**: modify — add explanatory comments (interval minimum, timeout default, 200-only rule).

### Verification

#### Automated
- [ ] Build + full `ctest` suite pass
- [ ] `SIGTERM` during the interval sleep: process exits 0 within ~1 s, prints stats summary, state file is current
- [ ] `SIGINT` mid-cycle: current check completes, then clean exit 0 with summary

#### Manual
- [ ] `Ctrl+C` interactively behaves the same as scripted `SIGINT`
- [ ] README instructions reproduce a working build from a clean checkout
