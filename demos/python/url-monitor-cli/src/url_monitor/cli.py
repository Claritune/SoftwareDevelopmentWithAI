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
