"""Main monitoring loop with signal handling and interruptible sleep."""

from __future__ import annotations

import signal
import time
from dataclasses import dataclass, field

from url_monitor.checker import CheckResult, Status, check, classify
from url_monitor.config import Config
from url_monitor.notifier import (
    emit_transition,
    iso8601_now,
    log_check,
    log_info,
)
from url_monitor.state import StateStore, save_state
from url_monitor.stats import format_stats, record


# Module-level shutdown flag
_shutdown_requested = False


def _signal_handler(signum: int, frame: object) -> None:
    """Signal handler for SIGINT/SIGTERM — sets shutdown flag."""
    global _shutdown_requested
    _shutdown_requested = True


def shutdown_requested() -> bool:
    """Check if shutdown has been requested."""
    return _shutdown_requested


def _interruptible_sleep(seconds: float) -> None:
    """Sleep in 200ms slices, checking shutdown flag between slices."""
    remaining = seconds
    while remaining > 0 and not _shutdown_requested:
        slice_time = min(0.2, remaining)
        time.sleep(slice_time)
        remaining -= slice_time


@dataclass
class MonitorContext:
    config: Config
    state: StateStore
    state_path: str
    verbose: bool = False


def run_monitor(ctx: MonitorContext) -> int:
    """Run the main monitoring loop until SIGINT/SIGTERM.

    Returns exit code (0 on graceful shutdown).
    """
    global _shutdown_requested
    _shutdown_requested = False

    # Install signal handlers
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    log_info("url-monitor starting")
    log_info(
        f"monitoring {len(ctx.config.urls)} URLs "
        f"every {ctx.config.check_interval_seconds}s"
    )

    while not _shutdown_requested:
        # Check each URL
        for spec in ctx.config.urls:
            if _shutdown_requested:
                break

            result = check(spec)
            new_status = classify(result)

            # Get or create URL state
            if spec.url not in ctx.state.urls:
                from url_monitor.state import UrlState

                ctx.state.urls[spec.url] = UrlState()

            url_state = ctx.state.urls[spec.url]
            prev_status = url_state.status

            # Record stats
            record(url_state.stats, result, new_status)

            # Emit transition (skip first check from Unknown)
            if prev_status != Status.Unknown and prev_status != new_status:
                emit_transition(spec.url, prev_status, new_status, result)

            # Verbose logging
            if ctx.verbose:
                log_check(spec.url, new_status, result)

            # Update state
            url_state.status = new_status
            url_state.last_checked = iso8601_now()

        # Save state after each cycle
        save_state(ctx.state_path, ctx.state)

        # Interruptible sleep
        if not _shutdown_requested:
            _interruptible_sleep(ctx.config.check_interval_seconds)

    # Shutdown
    log_info("shutting down")
    save_state(ctx.state_path, ctx.state)

    # Print stats summary
    print()
    for url, url_state in ctx.state.urls.items():
        print(format_stats(url, url_state.stats))
        print()

    return 0
