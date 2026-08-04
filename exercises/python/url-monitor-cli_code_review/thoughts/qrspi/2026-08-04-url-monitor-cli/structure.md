# Structure Outline

## Approach

Build the `url-monitor` Python CLI in three vertical slices, each runnable end-to-end. Start with CLI parsing and a single URL check, then add state tracking and transition logic, then the continuous monitoring loop with logging and graceful shutdown. Each slice is independently testable and verifiable.

---

## Slice 1: CLI + single URL check

Establish the package structure, CLI parsing, YAML config loading, HTTP checker, and a one-shot check pass that prints results and exits.

**Files**: `pyproject.toml`, `src/url_monitor/__init__.py`, `src/url_monitor/__main__.py`, `src/url_monitor/config.py`, `src/url_monitor/checker.py`, `config/example.yaml`, `tests/test_classify.py`

**Key changes**:
- `pyproject.toml` with `[project.scripts]` entry for `url-monitor`
- `config.py`: `UrlSpec`, `Config` dataclasses; `parse_args()` via argparse; `load_config()` with YAML validation (interval >= 5, urls non-empty, timeout >= 1)
- `checker.py`: `Status` enum, `CheckResult` dataclass, `classify()` (200-only rule), `check()` using `httpx.Client`
- `__main__.py`: parse args, load config, check each URL once, print results, exit
- `test_classify.py`: pytest tests for classification boundaries

**Verify**:
- `pip install -e ".[dev]"` succeeds
- `url-monitor --help` shows usage
- `url-monitor --config config/example.yaml` checks each URL once and prints results
- `pytest tests/test_classify.py -v` passes

---

## Slice 2: State tracking + transitions

Add JSON sidecar state persistence, state reconciliation, stats accumulation, transition emission, and `--stats` mode.

**Files**: `src/url_monitor/state.py`, `src/url_monitor/stats.py`, `src/url_monitor/notifier.py`, `tests/test_stats.py`

**Key changes**:
- `state.py`: `UrlState`, `StateStore` dataclasses; `load_state()`, `save_state()` (atomic), `reconcile()`
- `stats.py`: `UrlStats` dataclass; `record()`, `format_stats()`
- `notifier.py`: `iso8601_now()`, `log_info()`, `log_error()`, `emit_transition()`, `log_check()`
- `__main__.py`: add `--stats` path (load state, print stats, exit)
- `test_stats.py`: accumulation, formatting, state round-trip, legacy compatibility

**Verify**:
- `pytest tests/ -v` passes all tests
- After a one-shot run, state file exists with valid JSON
- `url-monitor --stats --config config/example.yaml` prints per-URL counters
- State round-trip preserves all fields

---

## Slice 3: Continuous monitoring + logging + shutdown

Add the main monitor loop, signal handling (SIGINT/SIGTERM), interruptible sleep, transition-only logging, verbose mode, and graceful shutdown with stats summary.

**Files**: `src/url_monitor/monitor.py`, `src/url_monitor/__main__.py` (wire loop)

**Key changes**:
- `monitor.py`: `MonitorContext` dataclass; `run_monitor()` loop; signal handler setting `_shutdown_requested`; `_interruptible_sleep()` with 200ms slices
- `__main__.py`: build context, call `run_monitor()` instead of one-shot
- Transition logic: skip on first check from Unknown; emit on real status change
- On shutdown: save state, print stats summary, exit 0

**Verify**:
- Monitor runs continuously, logging transitions only (unless `--verbose`)
- `Ctrl+C` exits within ~200ms, prints stats summary
- State file is current after shutdown
- Restart does not re-emit DOWN for already-down URLs

---

## Testing Checkpoints

- **After Slice 1**: Package installs; CLI + config work; classification tests pass; one-shot checks work against httpbin.
- **After Slice 2**: Stats tests pass; state persists and round-trips correctly; `--stats` mode works; legacy state files load.
- **After Slice 3**: Full monitor loop with signal handling; graceful shutdown; transitions correct across restarts; all tests pass.
