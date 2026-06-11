# Implementation Plan

## Overview

Build a pure Python CLI that monitors URLs in a foreground poll loop, logs every check to stderr or a log file, and prints DOWN/UP transition messages to stdout. Implemented in three vertical phases: CLI + checker, state + notifications, then continuous loop with graceful shutdown.

Working directory for all commands: `demo_url_monitor/` (repository root).

---

## Phase 1: Check URLs from the CLI

### Changes

#### 1. Project manifest
**File**: `pyproject.toml`
**Action**: create

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "url-monitor"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
    "httpx>=0.27",
    "pydantic-settings>=2.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
url-monitor = "url_monitor.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/url_monitor"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

#### 2. Package entry
**File**: `src/url_monitor/__init__.py`
**Action**: create (empty)

**File**: `src/url_monitor/__main__.py`
**Action**: create

```python
from url_monitor.cli import main

main()
```

#### 3. Configuration
**File**: `src/url_monitor/config.py`
**Action**: create

```python
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MonitorConfig(BaseSettings):
    model_config = SettingsConfigDict()  # no env_file — CLI-only for v1

    urls: list[str] = Field(min_length=1)
    failure_threshold: int = Field(default=3, ge=1)
    interval: int = Field(default=30, ge=1)
    timeout: int = Field(default=10, ge=1)
    log_file: str | None = None

    @field_validator("urls")
    @classmethod
    def urls_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one URL is required")
        return v


def from_cli(
    urls: tuple[str, ...],
    failure_threshold: int,
    interval: int,
    timeout: int,
    log_file: str | None,
) -> MonitorConfig:
    return MonitorConfig(
        urls=list(urls),
        failure_threshold=failure_threshold,
        interval=interval,
        timeout=timeout,
        log_file=log_file,
    )
```

#### 4. HTTP checker
**File**: `src/url_monitor/checker.py`
**Action**: create

```python
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx


@dataclass(frozen=True)
class CheckResult:
    url: str
    success: bool
    status_code: int | None
    response_time_ms: float | None
    error: str | None
    timestamp: datetime


def is_failure(result: CheckResult) -> bool:
    return not result.success


def check(url: str, timeout: int, client: httpx.Client | None = None) -> CheckResult:
    owns_client = client is None
    if owns_client:
        client = httpx.Client(follow_redirects=True)

    start = datetime.now(timezone.utc)
    try:
        response = client.get(url, timeout=timeout)
        elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        success = response.status_code < 400
        return CheckResult(
            url=url,
            success=success,
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
            error=None,
            timestamp=start,
        )
    except httpx.RequestError as exc:
        return CheckResult(
            url=url,
            success=False,
            status_code=None,
            response_time_ms=None,
            error=str(exc),
            timestamp=start,
        )
    finally:
        if owns_client:
            client.close()
```

#### 5. CLI (single round)
**File**: `src/url_monitor/cli.py`
**Action**: create

```python
import sys

import click

from url_monitor.checker import check
from url_monitor.config import from_cli


def _format_result(result) -> str:
    if result.success:
        return (
            f"{result.timestamp.isoformat()} OK   {result.url} "
            f"HTTP {result.status_code} ({result.response_time_ms:.0f}ms)"
        )
    if result.status_code is not None:
        return (
            f"{result.timestamp.isoformat()} FAIL {result.url} "
            f"HTTP {result.status_code}"
        )
    return f"{result.timestamp.isoformat()} FAIL {result.url} {result.error}"


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("urls", nargs=-1, required=True)
@click.option("--failure-threshold", default=3, show_default=True, type=int)
@click.option("--interval", default=30, show_default=True, type=int)
@click.option("--timeout", default=10, show_default=True, type=int)
@click.option("--log-file", default=None, type=click.Path())
def main(urls, failure_threshold, interval, timeout, log_file):
    """Monitor URLs for uptime. Phase 1: single check round."""
    try:
        config = from_cli(urls, failure_threshold, interval, timeout, log_file)
    except Exception as exc:
        click.echo(f"Configuration error: {exc}", err=True)
        sys.exit(1)

    for url in config.urls:
        result = check(url, config.timeout)
        click.echo(_format_result(result), err=True)
```

#### 6. Tests — checker
**File**: `tests/test_checker.py`
**Action**: create

Test cases using `httpx.MockTransport`:
- 200 response → `success=True`, status_code=200
- 404 response → `success=False`, status_code=404
- 503 response → `success=False`
- Connection error (invalid host) → `success=False`, `error` set, `status_code=None`
- Redirect 302 → 200 (follow_redirects=True) → `success=True`

#### 7. Tests — CLI
**File**: `tests/test_cli.py`
**Action**: create

Use `click.testing.CliRunner`:
- `main([])` → exit code 2 (click missing required args) or invoke with no urls → exit 1
- `main(["https://example.com"])` with mocked `check` → exit 0, stderr contains "OK" or "FAIL"
- `--failure-threshold 0` → exit 1 (Pydantic validation error)

### Verification

#### Automated
- [x] `pip install -e ".[dev]"` succeeds
- [x] `pytest tests/ -v` passes (all Phase 1 tests green)

#### Manual
- [ ] `python -m url_monitor https://httpbin.org/status/200` prints one OK line to stderr, exits 0
- [ ] `python -m url_monitor https://httpbin.org/status/503` prints one FAIL line to stderr, exits 0
- [ ] `python -m url_monitor` exits non-zero with usage/config error
- [ ] `url-monitor --help` shows all flags and defaults

---

## Phase 2: Detect transitions and notify on stdout

### Changes

#### 1. State machine
**File**: `src/url_monitor/state.py`
**Action**: create

```python
from dataclasses import dataclass, field
from enum import Enum

from url_monitor.checker import CheckResult, is_failure


class UrlStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    UP = "UP"
    DOWN = "DOWN"


@dataclass
class UrlState:
    status: UrlStatus = UrlStatus.UNKNOWN
    consecutive_failures: int = 0


@dataclass(frozen=True)
class Transition:
    url: str
    from_status: UrlStatus
    to_status: UrlStatus
    result: CheckResult


class StateTracker:
    def __init__(self) -> None:
        self._states: dict[str, UrlState] = {}

    def get(self, url: str) -> UrlState:
        if url not in self._states:
            self._states[url] = UrlState()
        return self._states[url]

    def update(self, url: str, result: CheckResult, threshold: int) -> Transition | None:
        state = self.get(url)
        failed = is_failure(result)

        if failed:
            state.consecutive_failures += 1
            if state.consecutive_failures >= threshold:
                if state.status != UrlStatus.DOWN:
                    transition = Transition(url, state.status, UrlStatus.DOWN, result)
                    state.status = UrlStatus.DOWN
                    return transition
            return None

        # success path
        state.consecutive_failures = 0
        if state.status == UrlStatus.DOWN:
            transition = Transition(url, UrlStatus.DOWN, UrlStatus.UP, result)
            state.status = UrlStatus.UP
            return transition
        state.status = UrlStatus.UP
        return None  # UNKNOWN→UP silent
```

#### 2. Notifier
**File**: `src/url_monitor/notifier.py`
**Action**: create

```python
import sys

from url_monitor.state import Transition, UrlStatus


def format_notification(transition: Transition, threshold: int) -> str:
    ts = transition.result.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    direction = transition.to_status.value

    if transition.to_status == UrlStatus.DOWN:
        if transition.result.status_code is not None:
            detail = f"{threshold} consecutive failures, last: HTTP {transition.result.status_code}"
        else:
            detail = f"{threshold} consecutive failures, last: {transition.result.error}"
    else:
        detail = f"HTTP {transition.result.status_code}, {transition.result.response_time_ms:.0f}ms"

    return f"[{ts}] {direction:<4} {transition.url}  ({detail})"


def notify(transition: Transition, threshold: int) -> None:
    sys.stdout.write(format_notification(transition, threshold) + "\n")
    sys.stdout.flush()
```

#### 3. Round orchestrator
**File**: `src/url_monitor/monitor.py`
**Action**: create (partial — `run_round` only)

```python
import httpx

from url_monitor.checker import check
from url_monitor.config import MonitorConfig
from url_monitor.notifier import notify
from url_monitor.state import StateTracker, Transition


def run_round(
    config: MonitorConfig,
    tracker: StateTracker,
    client: httpx.Client,
) -> list[Transition]:
    transitions: list[Transition] = []
    for url in config.urls:
        result = check(url, config.timeout, client=client)
        transition = tracker.update(url, result, config.failure_threshold)
        if transition:
            notify(transition, config.failure_threshold)
            transitions.append(transition)
    return transitions
```

#### 4. CLI update
**File**: `src/url_monitor/cli.py`
**Action**: modify

- Import `StateTracker`, `run_round`, `check`, `httpx`
- Add `--rounds N` option (default 1 for Phase 2; used for transition testing)
- Replace single-round loop with:

```python
tracker = StateTracker()
with httpx.Client(follow_redirects=True) as client:
    for _ in range(rounds):
        for url in config.urls:
            result = check(url, config.timeout, client=client)
            click.echo(_format_result(result), err=True)
            transition = tracker.update(url, result, config.failure_threshold)
            if transition:
                notify(transition, config.failure_threshold)
```

Note: Phase 2 keeps stderr result printing from Phase 1 for debugging; Phase 3 moves routine output to `CheckLogger`.

#### 5. Tests — state
**File**: `tests/test_state.py`
**Action**: create

Build `CheckResult` fixtures (success/fail). Assert:
- 3 consecutive failures from UNKNOWN → one DOWN transition
- 3 consecutive failures from UP → one DOWN transition
- 1 success after DOWN → one UP transition
- 1 success from UNKNOWN → no transition, status becomes UP
- 2 failures then 1 success → no transition, consecutive_failures resets

#### 6. Tests — notifier
**File**: `tests/test_notifier.py`
**Action**: create

- `format_notification` for DOWN with HTTP status
- `format_notification` for DOWN with connection error
- `format_notification` for UP

#### 7. Tests — monitor integration
**File**: `tests/test_monitor.py`
**Action**: create

Use `unittest.mock.patch("url_monitor.monitor.check")` or inject mock transport:
- Sequence of 3 failures → `run_round` returns 1 transition; capture stdout → contains "DOWN"
- Sequence: 3 failures then 1 success across two `run_round` calls → second round stdout contains "UP"

### Verification

#### Automated
- [ ] `pytest tests/ -v` passes (all Phase 1 + Phase 2 tests green)

#### Manual
- [ ] `python -m url_monitor https://httpbin.org/status/503 --rounds 3` prints DOWN to stdout after 3rd round
- [ ] `python -m url_monitor https://httpbin.org/status/200 --rounds 1` prints no DOWN/UP lines to stdout (only stderr check lines)

---

## Phase 3: Continuous monitoring with logging and graceful shutdown

### Changes

#### 1. Check logger
**File**: `src/url_monitor/logger.py`
**Action**: create

```python
import sys
from pathlib import Path

from url_monitor.checker import CheckResult


def format_check_log(result: CheckResult) -> str:
    if result.success:
        return (
            f"{result.timestamp.isoformat()} OK   {result.url} "
            f"HTTP {result.status_code} ({result.response_time_ms:.0f}ms)"
        )
    if result.status_code is not None:
        return f"{result.timestamp.isoformat()} FAIL {result.url} HTTP {result.status_code}"
    return f"{result.timestamp.isoformat()} FAIL {result.url} {result.error}"


class CheckLogger:
    def __init__(self, log_file: str | None) -> None:
        self._log_file = Path(log_file) if log_file else None

    def log(self, result: CheckResult) -> None:
        line = format_check_log(result) + "\n"
        if self._log_file:
            with self._log_file.open("a") as f:
                f.write(line)
        else:
            sys.stderr.write(line)
            sys.stderr.flush()
```

#### 2. Monitor loop + shutdown
**File**: `src/url_monitor/monitor.py`
**Action**: modify

Add:

```python
import signal
import sys
import time

from url_monitor.checker import check
from url_monitor.logger import CheckLogger
from url_monitor.notifier import notify


class ShutdownHandler:
    def __init__(self) -> None:
        self.requested = False

    def install(self) -> None:
        signal.signal(signal.SIGINT, self._handle)
        signal.signal(signal.SIGTERM, self._handle)

    def _handle(self, signum, frame) -> None:
        self.requested = True


def run_forever(config: MonitorConfig) -> None:
    handler = ShutdownHandler()
    handler.install()
    tracker = StateTracker()
    logger = CheckLogger(config.log_file)

    sys.stderr.write(
        f"Monitoring {len(config.urls)} URL(s). Runs until Ctrl+C.\n"
    )

    with httpx.Client(follow_redirects=True) as client:
        while not handler.requested:
            for url in config.urls:
                if handler.requested:
                    break
                result = check(url, config.timeout, client=client)
                logger.log(result)
                transition = tracker.update(url, result, config.failure_threshold)
                if transition:
                    notify(transition, config.failure_threshold)

            if handler.requested:
                break
            time.sleep(config.interval)

    sys.stderr.write("Shutdown requested. Exiting.\n")
```

Refactor `run_round` to reuse the inner loop body if desired, or keep both — `run_forever` is the production path.

#### 3. CLI — production mode
**File**: `src/url_monitor/cli.py`
**Action**: modify

- Remove `--rounds` option
- Remove `_format_result` stderr printing from the check loop (logger handles it)
- Replace body with:

```python
@click.command(...)
@click.argument("urls", nargs=-1, required=True)
@click.option("--failure-threshold", ...)
@click.option("--interval", ..., help="Seconds between check rounds. Runs until Ctrl+C.")
@click.option("--timeout", ...)
@click.option("--log-file", ...)
def main(urls, failure_threshold, interval, timeout, log_file):
    """Monitor URLs for uptime. Runs until Ctrl+C."""
    try:
        config = from_cli(urls, failure_threshold, interval, timeout, log_file)
    except Exception as exc:
        click.echo(f"Configuration error: {exc}", err=True)
        sys.exit(1)

    run_forever(config)
```

- Move `_format_result` to `logger.py` (already replaced by `format_check_log`) and delete duplicate from `cli.py`

#### 4. Tests — logger
**File**: `tests/test_logger.py`
**Action**: create

- `format_check_log` for OK and FAIL cases
- `CheckLogger(log_file=tmp_path)` appends lines to file
- `CheckLogger(log_file=None)` writes to stderr (capture with capsys)

#### 5. Tests — monitor loop
**File**: `tests/test_monitor.py`
**Action**: modify

Add tests for `ShutdownHandler` and `run_forever`:
- Patch `time.sleep` to raise `KeyboardInterrupt` or set `handler.requested = True` after 2 iterations
- Patch `check` to return canned results
- Assert loop runs expected number of checks then exits
- Do NOT let tests run infinite loops — always patch sleep or pre-set shutdown flag

Remove or update any `--rounds`-dependent CLI tests from Phase 2.

#### 6. Tests — CLI update
**File**: `tests/test_cli.py`
**Action**: modify

- Patch `run_forever` to no-op; assert CLI invokes it with parsed config
- Remove `--rounds` test cases

### Verification

#### Automated
- [ ] `pytest tests/ -v` passes (full suite green, no hanging tests)

#### Manual
- [ ] `python -m url_monitor https://httpbin.org/status/200 --interval 5` logs checks every ~5s to stderr; Ctrl+C prints "Shutdown requested", exits 0
- [ ] `python -m url_monitor https://httpbin.org/status/503 --interval 5` prints DOWN to stdout after 3 consecutive failures; stderr shows FAIL log lines
- [ ] `python -m url_monitor https://httpbin.org/status/200 --log-file /tmp/monitor.log --interval 5` appends OK lines to log file; stdout has no routine check output
- [ ] `url-monitor --help` mentions "Runs until Ctrl+C"

---

## Testing Checkpoints (resume guide)

| Phase complete | Safe to resume from |
|----------------|---------------------|
| Phase 1 | Phase 2 — checker and config are stable |
| Phase 2 | Phase 3 — state machine and notifier are stable; wire logger + loop |
| Phase 3 | Done — run full manual smoke test |

## Deviations from structure.md

None. Phase order, files, and signatures match the structure outline. `--rounds` is added in Phase 2 as specified and removed in Phase 3 as specified.
