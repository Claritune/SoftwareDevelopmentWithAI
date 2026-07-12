# URL Monitor (C++)

A C++ CLI tool that monitors URLs for uptime, detects when sites go down or come back up, and prints notifications to stdout.

This repository is a **QRSPI demo**: it started as an empty directory and was built using a structured AI-assisted workflow — not by jumping straight to code.

## What it does

Given one or more URLs, the tool:

1. Performs HTTP health checks on a schedule
2. Tracks consecutive failures per URL
3. Announces **DOWN** and **UP** transitions to stdout
4. Logs every check to stderr and an optional log file
5. Runs in a foreground poll loop until you press Ctrl+C

A site is considered **down** after N consecutive failures (HTTP status >= 400 or connection timeout). N defaults to 3 and is configurable via `--failure-threshold`.

### Example

```bash
./build/url-monitor https://example.com https://api.example.com/health \
  --failure-threshold 3 \
  --interval 30 \
  --timeout 10 \
  --log-file monitor.log
```

Stdout on transitions:

```
[2026-07-12T15:57:32Z] DOWN  https://example.com  (3 consecutive failures, last: HTTP 503)
[2026-07-12T15:58:02Z] UP    https://example.com  (HTTP 200, 142ms)
```

## Quick start

**Requirements:** CMake 3.14+, C++17 compiler (Apple Clang, GCC, MSVC), system curl

```bash
# Build (dependencies are fetched automatically via CMake FetchContent)
cd steps/step-6-implement-phase2
cmake -B build
cmake --build build

# Run tests
./build/tests

# Monitor a URL
./build/url-monitor https://httpbin.org/status/200 --interval 10

# Stop with Ctrl+C
```

### CLI options

| Flag | Default | Description |
|------|---------|-------------|
| `URLS` | *(required)* | One or more URLs to monitor |
| `--failure-threshold` | `3` | Consecutive failures before marking DOWN |
| `--interval` | `30` | Seconds between check rounds |
| `--timeout` | `10` | HTTP request timeout in seconds |
| `--log-file` | *(none)* | Append timestamped check logs to this file |

## Demo structure

This demo shows incremental QRSPI steps as subfolders. Each step builds on the previous one:

```
steps/
├── step-0-goal/              # One-line product goal
├── step-1-questions/         # Clarifying questions and user decisions
├── step-2-design/            # Architecture and scope decisions
├── step-3-structure/         # Vertical implementation slices
├── step-4-plan/              # Tactical step-by-step plan
├── step-5-implement-phase1/  # Single check round + state machine + tests
└── step-6-implement-phase2/  # Poll loop + logger + signal handling (final)
```

The final working project is in `steps/step-6-implement-phase2/`.

### Source layout (step-6)

```
src/
├── config.h       # Config struct (URLs, thresholds, intervals)
├── checker.h/cpp  # HTTP health check via cpr (libcurl wrapper)
├── monitor.h/cpp  # State machine: consecutive failures → DOWN/UP transitions
├── logger.h/cpp   # Timestamped logging to stderr + optional file
└── main.cpp       # CLI parsing (CLI11), poll loop, signal handling
tests/
└── test_monitor.cpp  # 8 test cases, 25 assertions (Catch2)
```

### Libraries (auto-downloaded via FetchContent)

| Library | Purpose |
|---------|---------|
| [cpr](https://github.com/libcpr/cpr) 1.11.2 | HTTP requests (C++ wrapper around libcurl) |
| [CLI11](https://github.com/CLIUtils/CLI11) 2.4.2 | Command-line argument parsing |
| [Catch2](https://github.com/catchorg/Catch2) 3.7.1 | Unit testing |

## Development methodology: QRSPI

This project was built with **QRSPI** — a phased workflow for AI-assisted development that forces alignment *before* code is written. Each phase produces a reviewable artifact; the agent does not silently make architectural decisions.

| Phase | Artifact | Purpose |
|-------|----------|---------|
| **Q** — Question | `questions.md`, `answers.md` | Surface ambiguities and get explicit user decisions |
| **R** — Research | *(skipped — greenfield)* | Document existing codebase patterns |
| **S** — Structure | `structure.md` | Break work into vertical, testable slices |
| **P** — Plan | `plan.md` | Tactical implementation details with verification steps |
| **I** — Implement | code + tests | Execute one phase at a time, verify, commit |

Design decisions are captured in `design.md` between Question and Structure.

### Why QRSPI for a greenfield project?

A naive prompt like *"build me a URL monitor in C++"* causes an agent to silently choose libraries, intervals, output formats, and architecture. QRSPI turns those into **questions you answer explicitly**.

For this project, key decisions captured in `answers.md` include:

- **C++17** with CMake + FetchContent (no manual dependency installs)
- **One-shot foreground loop** (not a background daemon) — runs until Ctrl+C
- **URLs via CLI arguments** (not a config file)
- **Stdout-only notifications** for transitions; routine checks go to stderr/log
- **In-memory state** (no database)
- **Sequential checks** (no thread pool concurrency)

QRSPI artifacts are in each step's `thoughts/qrspi/2026-07-12-url-monitor-cpp/` directory.

## License

Part of the SoftwareDevelopmentWithAI demos collection.
