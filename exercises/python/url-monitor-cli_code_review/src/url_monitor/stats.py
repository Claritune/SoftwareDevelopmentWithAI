"""Per-URL counter accumulation and stats formatting."""

from __future__ import annotations

from dataclasses import dataclass, field

from url_monitor.checker import CheckResult, Status


@dataclass
class UrlStats:
    total_checks: int = 0
    up_checks: int = 0
    down_checks: int = 0
    http_status: dict[int, int] = field(default_factory=dict)
    errors: dict[str, int] = field(default_factory=dict)


def record(stats: UrlStats, result: CheckResult, status: Status) -> None:
    """Record a check result into the URL stats."""
    stats.total_checks += 1
    if status == Status.Up:
        stats.up_checks += 1
    else:
        stats.down_checks += 1

    if result.error is not None:
        stats.errors[result.error] = stats.errors.get(result.error, 0) + 1
    elif result.http_status != 0:
        stats.http_status[result.http_status] = (
            stats.http_status.get(result.http_status, 0) + 1
        )


def format_stats(url: str, stats: UrlStats) -> str:
    """Format per-URL stats into a human-readable block."""
    if stats.total_checks == 0:
        uptime_pct = 0.0
    else:
        uptime_pct = (stats.up_checks / stats.total_checks) * 100

    header = (
        f"{url}   checks={stats.total_checks}  "
        f"up={stats.up_checks}  down={stats.down_checks}  "
        f"uptime={uptime_pct:.1f}%"
    )

    # HTTP status line
    if stats.http_status:
        http_parts = "   ".join(
            f"{code}: {count}" for code, count in sorted(stats.http_status.items())
        )
        http_line = f"  HTTP  {http_parts}"
    else:
        http_line = "  HTTP  (none)"

    # Errors line
    if stats.errors:
        error_parts = "   ".join(
            f"{name}: {count}" for name, count in sorted(stats.errors.items())
        )
        error_line = f"  errors  {error_parts}"
    else:
        error_line = "  errors  (none)"

    return f"{header}\n{http_line}\n{error_line}"
