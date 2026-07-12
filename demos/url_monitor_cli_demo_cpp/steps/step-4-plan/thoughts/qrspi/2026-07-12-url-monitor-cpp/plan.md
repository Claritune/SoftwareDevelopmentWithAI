# Implementation Plan

## Overview
Build a C++ CLI URL monitor that checks sites on a schedule and prints DOWN/UP transition notifications. Two phases: (1) single check round with transition logic, (2) continuous polling with logging and graceful shutdown.

## Phase 1: Single Check Round with Transition Detection

### Changes

#### 1. CMakeLists.txt
**File**: `CMakeLists.txt`
**Action**: create

```cmake
cmake_minimum_required(VERSION 3.14)
project(url_monitor VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)

FetchContent_Declare(cpr
    GIT_REPOSITORY https://github.com/libcpr/cpr.git
    GIT_TAG 1.11.2)
FetchContent_MakeAvailable(cpr)

FetchContent_Declare(cli11
    GIT_REPOSITORY https://github.com/CLIUtils/CLI11.git
    GIT_TAG v2.4.2)
FetchContent_MakeAvailable(cli11)

FetchContent_Declare(Catch2
    GIT_REPOSITORY https://github.com/catchorg/Catch2.git
    GIT_TAG v3.7.1)
FetchContent_MakeAvailable(Catch2)

add_executable(url-monitor
    src/main.cpp
    src/checker.cpp
    src/monitor.cpp)
target_link_libraries(url-monitor PRIVATE cpr::cpr CLI11::CLI11)
target_include_directories(url-monitor PRIVATE src)

enable_testing()
add_executable(tests tests/test_monitor.cpp src/monitor.cpp)
target_link_libraries(tests PRIVATE Catch2::Catch2WithMain)
target_include_directories(tests PRIVATE src)
add_test(NAME unit_tests COMMAND tests)
```

#### 2. Config struct
**File**: `src/config.h`
**Action**: create

```cpp
#pragma once
#include <string>
#include <vector>

struct Config {
    std::vector<std::string> urls;
    int failure_threshold = 3;
    int interval_seconds = 30;
    int timeout_seconds = 10;
    std::string log_file;
};
```

#### 3. HTTP checker
**File**: `src/checker.h`
**Action**: create

```cpp
#pragma once
#include <string>

struct CheckResult {
    int status_code = 0;
    long elapsed_ms = 0;
    bool success = false;
    std::string error;
};

CheckResult check_url(const std::string& url, int timeout_seconds);
```

**File**: `src/checker.cpp`
**Action**: create

```cpp
#include "checker.h"
#include <cpr/cpr.h>

CheckResult check_url(const std::string& url, int timeout_seconds) {
    CheckResult result;
    auto response = cpr::Get(
        cpr::Url{url},
        cpr::Timeout{timeout_seconds * 1000},
        cpr::Redirect{10});

    result.elapsed_ms = static_cast<long>(response.elapsed * 1000);

    if (response.error.code != cpr::ErrorCode::OK) {
        result.success = false;
        result.error = response.error.message;
        return result;
    }

    result.status_code = response.status_code;
    result.success = (response.status_code < 400);
    if (!result.success) {
        result.error = "HTTP " + std::to_string(response.status_code);
    }
    return result;
}
```

#### 4. State machine (monitor)
**File**: `src/monitor.h`
**Action**: create

```cpp
#pragma once
#include "checker.h"
#include <optional>
#include <string>

struct UrlState {
    int consecutive_failures = 0;
    bool is_down = false;
};

struct Transition {
    enum Type { DOWN, UP };
    Type type;
    std::string url;
    std::string reason;
};

std::optional<Transition> update_state(
    UrlState& state,
    const std::string& url,
    const CheckResult& result,
    int failure_threshold);
```

**File**: `src/monitor.cpp`
**Action**: create

```cpp
#include "monitor.h"

std::optional<Transition> update_state(
    UrlState& state,
    const std::string& url,
    const CheckResult& result,
    int failure_threshold) {

    if (result.success) {
        state.consecutive_failures = 0;
        if (state.is_down) {
            state.is_down = false;
            std::string reason = "HTTP " + std::to_string(result.status_code)
                + ", " + std::to_string(result.elapsed_ms) + "ms";
            return Transition{Transition::UP, url, reason};
        }
        return std::nullopt;
    }

    state.consecutive_failures++;
    if (!state.is_down && state.consecutive_failures >= failure_threshold) {
        state.is_down = true;
        std::string reason = std::to_string(state.consecutive_failures)
            + " consecutive failures, last: " + result.error;
        return Transition{Transition::DOWN, url, reason};
    }
    return std::nullopt;
}
```

#### 5. Main entry point (single round)
**File**: `src/main.cpp`
**Action**: create

```cpp
#include "config.h"
#include "checker.h"
#include "monitor.h"
#include <CLI/CLI.hpp>
#include <iostream>
#include <map>

int main(int argc, char** argv) {
    Config config;

    CLI::App app{"URL Monitor — checks URLs for uptime"};
    app.add_option("urls", config.urls, "URLs to monitor")
        ->required()
        ->expected(-1);
    app.add_option("--failure-threshold", config.failure_threshold,
        "Consecutive failures before marking DOWN")
        ->default_val(3);
    app.add_option("--interval", config.interval_seconds,
        "Seconds between check rounds")
        ->default_val(30);
    app.add_option("--timeout", config.timeout_seconds,
        "HTTP request timeout in seconds")
        ->default_val(10);
    app.add_option("--log-file", config.log_file,
        "Append check logs to this file");

    CLI11_PARSE(app, argc, argv);

    std::map<std::string, UrlState> states;
    for (const auto& url : config.urls) {
        states[url] = UrlState{};
    }

    for (const auto& url : config.urls) {
        auto result = check_url(url, config.timeout_seconds);

        std::cerr << "[check] " << url
                  << " status=" << result.status_code
                  << " elapsed=" << result.elapsed_ms << "ms"
                  << " success=" << (result.success ? "true" : "false")
                  << std::endl;

        auto transition = update_state(
            states[url], url, result, config.failure_threshold);

        if (transition) {
            std::string label = (transition->type == Transition::DOWN)
                ? "DOWN" : "UP  ";
            std::cout << "[" << label << "] " << transition->url
                      << "  (" << transition->reason << ")" << std::endl;
        }
    }

    return 0;
}
```

#### 6. Unit tests
**File**: `tests/test_monitor.cpp`
**Action**: create

```cpp
#include <catch2/catch_test_macros.hpp>
#include "monitor.h"

TEST_CASE("State starts healthy") {
    UrlState state;
    CHECK(state.consecutive_failures == 0);
    CHECK(state.is_down == false);
}

TEST_CASE("Successful check produces no transition") {
    UrlState state;
    CheckResult ok{200, 50, true, ""};
    auto t = update_state(state, "http://example.com", ok, 3);
    CHECK_FALSE(t.has_value());
    CHECK(state.consecutive_failures == 0);
}

TEST_CASE("Failures below threshold produce no transition") {
    UrlState state;
    CheckResult fail{503, 100, false, "HTTP 503"};
    update_state(state, "http://example.com", fail, 3);
    auto t = update_state(state, "http://example.com", fail, 3);
    CHECK_FALSE(t.has_value());
    CHECK(state.consecutive_failures == 2);
    CHECK(state.is_down == false);
}

TEST_CASE("Reaching threshold triggers DOWN") {
    UrlState state;
    CheckResult fail{0, 0, false, "Connection timeout"};
    update_state(state, "http://example.com", fail, 3);
    update_state(state, "http://example.com", fail, 3);
    auto t = update_state(state, "http://example.com", fail, 3);
    REQUIRE(t.has_value());
    CHECK(t->type == Transition::DOWN);
    CHECK(t->url == "http://example.com");
    CHECK(state.is_down == true);
}

TEST_CASE("Success after DOWN triggers UP") {
    UrlState state;
    state.is_down = true;
    state.consecutive_failures = 3;
    CheckResult ok{200, 42, true, ""};
    auto t = update_state(state, "http://example.com", ok, 3);
    REQUIRE(t.has_value());
    CHECK(t->type == Transition::UP);
    CHECK(state.is_down == false);
    CHECK(state.consecutive_failures == 0);
}

TEST_CASE("Additional failures after DOWN do not re-trigger") {
    UrlState state;
    state.is_down = true;
    state.consecutive_failures = 3;
    CheckResult fail{500, 100, false, "HTTP 500"};
    auto t = update_state(state, "http://example.com", fail, 3);
    CHECK_FALSE(t.has_value());
    CHECK(state.consecutive_failures == 4);
}
```

### Verification
#### Automated
- [ ] `cmake -B build && cmake --build build` compiles without errors
- [ ] `ctest --test-dir build` — all 5 tests pass

#### Manual
- [ ] `./build/url-monitor --help` prints usage with all flags
- [ ] `./build/url-monitor https://httpbin.org/status/200` prints check log to stderr, no transition
- [ ] `./build/url-monitor https://httpbin.org/status/503` prints check log, no DOWN yet (threshold=3, only 1 failure)

---

## Phase 2: Continuous Monitoring with Logging

### Changes

#### 1. Logger utility
**File**: `src/logger.h`
**Action**: create

```cpp
#pragma once
#include <string>
#include <fstream>
#include <optional>

std::string format_timestamp();

class Logger {
public:
    explicit Logger(const std::string& log_file_path = "");
    void log(const std::string& message);
private:
    std::optional<std::ofstream> file_;
};
```

**File**: `src/logger.cpp`
**Action**: create

```cpp
#include "logger.h"
#include <chrono>
#include <iomanip>
#include <iostream>
#include <sstream>

std::string format_timestamp() {
    auto now = std::chrono::system_clock::now();
    auto time = std::chrono::system_clock::to_time_t(now);
    std::ostringstream oss;
    oss << std::put_time(std::gmtime(&time), "%Y-%m-%dT%H:%M:%SZ");
    return oss.str();
}

Logger::Logger(const std::string& log_file_path) {
    if (!log_file_path.empty()) {
        file_.emplace(log_file_path, std::ios::app);
    }
}

void Logger::log(const std::string& message) {
    std::string timestamped = "[" + format_timestamp() + "] " + message;
    std::cerr << timestamped << std::endl;
    if (file_) {
        *file_ << timestamped << std::endl;
    }
}
```

#### 2. Updated main with poll loop and signal handling
**File**: `src/main.cpp`
**Action**: replace entirely

```cpp
#include "config.h"
#include "checker.h"
#include "monitor.h"
#include "logger.h"
#include <CLI/CLI.hpp>
#include <atomic>
#include <csignal>
#include <iostream>
#include <map>
#include <thread>

static std::atomic<bool> g_running{true};

static void signal_handler(int) {
    g_running = false;
}

int main(int argc, char** argv) {
    Config config;

    CLI::App app{"URL Monitor — checks URLs for uptime"};
    app.add_option("urls", config.urls, "URLs to monitor")
        ->required()
        ->expected(-1);
    app.add_option("--failure-threshold", config.failure_threshold,
        "Consecutive failures before marking DOWN")
        ->default_val(3);
    app.add_option("--interval", config.interval_seconds,
        "Seconds between check rounds")
        ->default_val(30);
    app.add_option("--timeout", config.timeout_seconds,
        "HTTP request timeout in seconds")
        ->default_val(10);
    app.add_option("--log-file", config.log_file,
        "Append check logs to this file");

    CLI11_PARSE(app, argc, argv);

    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);

    Logger logger(config.log_file);
    std::map<std::string, UrlState> states;
    for (const auto& url : config.urls) {
        states[url] = UrlState{};
    }

    logger.log("Monitoring " + std::to_string(config.urls.size())
        + " URL(s), interval=" + std::to_string(config.interval_seconds) + "s");

    while (g_running) {
        for (const auto& url : config.urls) {
            if (!g_running) break;

            auto result = check_url(url, config.timeout_seconds);

            logger.log(url + " status=" + std::to_string(result.status_code)
                + " elapsed=" + std::to_string(result.elapsed_ms) + "ms"
                + " success=" + (result.success ? "true" : "false"));

            auto transition = update_state(
                states[url], url, result, config.failure_threshold);

            if (transition) {
                std::string label = (transition->type == Transition::DOWN)
                    ? "DOWN" : "UP  ";
                std::string ts = format_timestamp();
                std::cout << "[" << ts << "] " << label << "  "
                          << transition->url
                          << "  (" << transition->reason << ")" << std::endl;
            }
        }

        for (int i = 0; i < config.interval_seconds && g_running; ++i) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    }

    logger.log("Shutting down.");
    return 0;
}
```

#### 3. Updated CMakeLists.txt
**File**: `CMakeLists.txt`
**Action**: add `src/logger.cpp` to the source list

```cmake
add_executable(url-monitor
    src/main.cpp
    src/checker.cpp
    src/monitor.cpp
    src/logger.cpp)
```

#### 4. Additional tests
**File**: `tests/test_monitor.cpp`
**Action**: append

```cpp
TEST_CASE("Threshold of 1 triggers DOWN on first failure") {
    UrlState state;
    CheckResult fail{500, 100, false, "HTTP 500"};
    auto t = update_state(state, "http://example.com", fail, 1);
    REQUIRE(t.has_value());
    CHECK(t->type == Transition::DOWN);
}

TEST_CASE("Multiple UP/DOWN cycles work correctly") {
    UrlState state;
    CheckResult fail{0, 0, false, "timeout"};
    CheckResult ok{200, 30, true, ""};

    // Go down
    update_state(state, "http://x.com", fail, 2);
    auto t1 = update_state(state, "http://x.com", fail, 2);
    REQUIRE(t1.has_value());
    CHECK(t1->type == Transition::DOWN);

    // Come back up
    auto t2 = update_state(state, "http://x.com", ok, 2);
    REQUIRE(t2.has_value());
    CHECK(t2->type == Transition::UP);

    // Go down again
    update_state(state, "http://x.com", fail, 2);
    auto t3 = update_state(state, "http://x.com", fail, 2);
    REQUIRE(t3.has_value());
    CHECK(t3->type == Transition::DOWN);
}
```

### Verification
#### Automated
- [ ] `cmake -B build && cmake --build build` compiles without errors
- [ ] `ctest --test-dir build` — all 7 tests pass

#### Manual
- [ ] `./build/url-monitor https://httpbin.org/status/200 --interval 5` runs continuously, logs every 5s
- [ ] Ctrl+C prints "Shutting down." and exits cleanly
- [ ] `./build/url-monitor https://httpbin.org/status/503 --failure-threshold 2 --interval 2` shows DOWN after ~4s
- [ ] `--log-file test.log` creates file with check logs
