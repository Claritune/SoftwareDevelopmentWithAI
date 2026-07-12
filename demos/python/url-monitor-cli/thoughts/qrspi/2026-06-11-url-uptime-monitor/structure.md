# Structure Outline

## Approach

Build the CLI in three vertical slices: first make URL checking invocable from the command line, then add transition detection with stdout notifications, then wrap in the continuous poll loop with logging and graceful shutdown. Each phase produces a runnable, testable increment — not layer-by-layer scaffolding.

## Phase 1: Check URLs from the CLI

Delivers an installable package that parses CLI arguments into validated config, performs a single sequential check round against all URLs, and prints structured results to stderr.

**Files**: `pyproject.toml`, `src/url_monitor/__init__.py`, `src/url_monitor/__main__.py`, `src/url_monitor/config.py`, `src/url_monitor/cli.py`, `src/url_monitor/checker.py`, `tests/test_checker.py`, `tests/test_cli.py`

**Key changes**:
- `MonitorConfig(BaseSettings)` — `urls: list[str]`, `failure_threshold: int = 3`, `interval: int = 30`, `timeout: int = 10`, `log_file: str | None = None`
- `from_cli(urls: tuple[str, ...], **flags) -> MonitorConfig` — new; merges click args into Settings without `os.getenv()`
- `CheckResult { url: str, success: bool, status_code: int | None, response_time_ms: float | None, error: str | None, timestamp: datetime }` — new dataclass
- `check(url: str, timeout: int, client: httpx.Client | None = None) -> CheckResult` — new; GET with sync httpx, fail on status >= 400 or connection error
- `is_failure(result: CheckResult) -> bool` — new; encapsulates failure criteria
- `cli.main()` — click command; runs one round, prints each `CheckResult` to stderr, exits 0

**Verify**: `pytest tests/` passes; `python -m url_monitor https://httpbin.org/status/200` prints a success line to stderr and exits 0; `python -m url_monitor` (no URLs) exits 1 with usage error.

---

## Phase 2: Detect transitions and notify on stdout

Adds per-URL state tracking and prints human-readable DOWN/UP messages to stdout when status transitions occur. Wires a `run_round` orchestrator that Phase 3 will loop — testable with multiple rounds via pytest mocks without an infinite loop.

**Files**: `src/url_monitor/state.py`, `src/url_monitor/notifier.py`, `src/url_monitor/monitor.py` (partial), `tests/test_state.py`, `tests/test_notifier.py`, `tests/test_monitor.py`

**Key changes**:
- `UrlStatus(str, Enum)` — `UNKNOWN`, `UP`, `DOWN`
- `UrlState { status: UrlStatus, consecutive_failures: int }` — new dataclass
- `Transition { url: str, from_status: UrlStatus, to_status: UrlStatus, result: CheckResult }` — new dataclass
- `StateTracker.update(url: str, result: CheckResult, threshold: int) -> Transition | None` — new; implements state machine from design
- `format_notification(transition: Transition) -> str` — new; `[timestamp] DOWN|UP url (detail)`
- `notify(transition: Transition) -> None` — new; prints to stdout
- `run_round(config: MonitorConfig, tracker: StateTracker, client: httpx.Client) -> list[Transition]` — new; checks all URLs sequentially, returns transitions
- `cli.main()` — modified; runs 3 rounds with 0s sleep (internal test path) OR accepts `--rounds N` dev flag to exercise transitions without infinite loop

**Verify**: `pytest tests/test_state.py` covers all transition paths (UNKNOWN→DOWN, UP→DOWN, DOWN→UP, UNKNOWN→UP silent); integration test with mocked `check()` returning 3 consecutive failures produces one DOWN line on stdout; recovery after DOWN produces UP line.

---

## Phase 3: Continuous monitoring with logging and graceful shutdown

Completes the product: infinite poll loop until SIGINT/SIGTERM, structured logging of every check to file or stderr, clean shutdown, and production CLI (remove `--rounds` dev flag if added).

**Files**: `src/url_monitor/logger.py`, `src/url_monitor/monitor.py` (complete), `src/url_monitor/cli.py`, `tests/test_logger.py`, `tests/test_monitor.py` (extend)

**Key changes**:
- `format_check_log(result: CheckResult) -> str` — new; structured line for routine checks
- `CheckLogger(log_file: str | None)` — new; append to file or write to stderr
- `run_forever(config: MonitorConfig) -> None` — new; poll loop: `run_round` → log each result → notify transitions → `sleep(interval)` → repeat until shutdown flag set
- `ShutdownHandler` — new; sets flag on SIGINT/SIGTERM, prints shutdown message
- `cli.main()` — modified; calls `run_forever`, help text notes "Runs until Ctrl+C"

**Verify**: `pytest tests/` passes; manual: `python -m url_monitor https://httpbin.org/status/200 --interval 5` logs checks every 5s, Ctrl+C prints shutdown and exits 0; `python -m url_monitor https://httpbin.org/status/503 --interval 5` prints DOWN to stdout after 3 failures; `--log-file monitor.log` creates append-only log with all check entries.

---

## Testing Checkpoints

| After phase | What is true |
|-------------|--------------|
| **Phase 1** | Package installs; CLI parses args via Pydantic; single-round HTTP checks work; failure criteria (>= 400, timeout) correct |
| **Phase 2** | State machine tracks consecutive failures; DOWN/UP printed to stdout on transitions only; `run_round` orchestrates check → state → notify |
| **Phase 3** | Full poll loop runs until interrupted; every check logged; signals handled cleanly; all pytest green |

## Note on vertical slicing

Phases 1–2 deliberately avoid the infinite loop so each slice can be verified in CI without hanging tests. Phase 2 uses `run_round` + mocked HTTP responses for transition E2E tests. Phase 3 promotes `run_round` into `run_forever` — if Phase 3 fails, Phases 1–2 remain independently useful as a single-round checker with transition detection.
