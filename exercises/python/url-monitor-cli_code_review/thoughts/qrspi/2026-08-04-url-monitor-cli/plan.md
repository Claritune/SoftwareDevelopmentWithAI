# Implementation Plan

## Overview

Build `url-monitor`, a Python 3.11+ CLI tool that monitors a YAML-configured list of URLs on a schedule, classifies each as up (HTTP 200 only) or down (everything else), logs state transitions to stdout, persists last-known state plus cumulative response statistics in a JSON sidecar, and shuts down gracefully on SIGINT/SIGTERM.

Install and test commands:

```bash
pip install -e ".[dev]"
pytest tests/ -v
url-monitor --config config/example.yaml
```

---

## Phase 1: Package skeleton + CLI + config loader

### Changes

#### 1. Package configuration
**File**: `pyproject.toml`
**Action**: create

Modern `[project]` table with `name="url-monitor"`, `version="1.0.0"`, `requires-python=">=3.11"`, dependencies `httpx` and `pyyaml`, dev dependency `pytest`, and `[project.scripts]` entry mapping `url-monitor` to `url_monitor.__main__:main`.

#### 2. Config types and loader
**File**: `src/url_monitor/config.py`
**Action**: create

- `UrlSpec(url: str, timeout_seconds: int = 10)` dataclass
- `Config(check_interval_seconds: int, urls: list[UrlSpec])` dataclass
- `CliOptions(config_path, state_file, verbose, stats_only)` dataclass
- `parse_args(argv)` — argparse-based; flags: `--config`, `--state-file`, `--verbose`, `--stats`, `--help`
- `load_config(path)` — `yaml.safe_load`, validate interval >= 5, urls non-empty, each url has non-empty string, timeout >= 1
- `derive_state_path(config_path)` — strip extension, append `.state.json`

#### 3. Entry point stub
**File**: `src/url_monitor/__main__.py`
**Action**: create

Parse args, load config, print parsed URLs and interval, exit.

### Verification
- [x] `pip install -e ".[dev]"` succeeds
- [x] `url-monitor --help` exits 0 with usage
- [x] `url-monitor --config config/example.yaml` prints interval and URLs
- [x] `url-monitor --config missing.yaml` exits 1 with error message
- [x] Config with `check_interval_seconds: 2` exits 1

---

## Phase 2: HTTP checker + classification

### Changes

#### 1. Checker module
**File**: `src/url_monitor/checker.py`
**Action**: create

- `Status` enum: `Unknown`, `Up`, `Down`
- `CheckResult(http_status: int, error: str | None, total_ms: float)` dataclass
- `classify(result)` — `Up` iff `error is None and http_status == 200`
- `status_name(status)` — lowercase string
- `check(spec)` — `httpx.Client` GET with redirect following, timeout from spec. Map `httpx` exceptions to stable error keys via `_error_key()`.

#### 2. Unit tests
**File**: `tests/test_classify.py`
**Action**: create

- HTTP 200 no error -> Up
- HTTP 301, 404, 500, 503 no error -> Down
- Error (timeout, connection_refused) -> Down
- HTTP 0 no error -> Down
- HTTP 200 with error -> Down
- `status_name()` returns correct strings

#### 3. Wire one-shot checks
**File**: `src/url_monitor/__main__.py`
**Action**: modify — replace config printout with one-shot check loop.

### Verification
- [x] `pytest tests/test_classify.py -v` passes
- [x] One-shot run prints UP for `https://example.com` and DOWN for `/status/503`

---

## Phase 3: State persistence + stats

### Changes

#### 1. Stats module
**File**: `src/url_monitor/stats.py`
**Action**: create

- `UrlStats` dataclass with counters and dicts
- `record(stats, result, status)` — bump counters
- `format_stats(url, stats)` — human-readable block

#### 2. State module
**File**: `src/url_monitor/state.py`
**Action**: create

- `UrlState(status, last_checked, stats)` dataclass
- `StateStore(version, urls)` dataclass
- `load_state(path)` — JSON parse, missing/corrupt = empty
- `save_state(path, store)` — atomic via `tempfile.mkstemp` + `os.replace`
- `reconcile(store, config)` — add new URLs, drop removed

#### 3. Stats tests
**File**: `tests/test_stats.py`
**Action**: create

- Accumulation sequence
- Format output assertions
- State round-trip (save + load + verify equality)
- Legacy state without stats key

#### 4. Wire --stats mode
**File**: `src/url_monitor/__main__.py`
**Action**: modify — add `--stats` path: load state, print format_stats per URL, exit.

### Verification
- [x] `pytest tests/ -v` passes all tests
- [x] State file created after one-shot run
- [x] `--stats` prints counters
- [x] Round-trip preserves all fields

---

## Phase 4: Monitor loop + notification + shutdown

### Changes

#### 1. Notifier module
**File**: `src/url_monitor/notifier.py`
**Action**: create

- `iso8601_now()` — UTC timestamp string
- `log_info(msg)`, `log_error(msg)` — timestamped stdout/stderr
- `emit_transition(url, prev, now, result)` — fixed-width status line
- `log_check(url, status, result)` — verbose mode line

#### 2. Monitor module
**File**: `src/url_monitor/monitor.py`
**Action**: create

- `MonitorContext(config, state, state_path, verbose)` dataclass
- `run_monitor(ctx)` — main loop with signal handling
- `_signal_handler(signum, frame)` — sets `_shutdown_requested`
- `_interruptible_sleep(seconds)` — 200ms slice loop
- Transition logic: skip Unknown baseline, emit on real change
- On shutdown: save state, print stats summary, return 0

#### 3. Wire the loop
**File**: `src/url_monitor/__main__.py`
**Action**: modify — build `MonitorContext`, call `run_monitor()`.

### Verification
- [x] Monitor runs continuously, checks at configured interval
- [x] Only transitions logged (unless `--verbose`)
- [x] `Ctrl+C` exits gracefully within ~200ms
- [x] Stats summary printed on shutdown
- [x] State file saved on shutdown
- [x] Restart does not re-emit DOWN

---

## Phase 5: Documentation + review

### Changes

#### 1. README
**File**: `README.md`
**Action**: create — install, run, test commands; architecture overview; classification rule; CLI flags.

#### 2. Code review
**File**: `CODE_REVIEW.md`
**Action**: create — thorough review covering functionality, error handling, code quality.

### Verification
- [x] All tests pass: `pytest tests/ -v`
- [x] Full monitor loop works end-to-end
- [x] README instructions reproduce a working install from clean
