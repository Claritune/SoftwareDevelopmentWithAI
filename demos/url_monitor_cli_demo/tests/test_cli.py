from datetime import datetime, timezone
from unittest.mock import patch

from click.testing import CliRunner

from url_monitor.checker import CheckResult
from url_monitor.cli import main


def _ok_result(url: str) -> CheckResult:
    return CheckResult(
        url=url,
        success=True,
        status_code=200,
        response_time_ms=42.0,
        error=None,
        timestamp=datetime(2026, 6, 11, 10, 0, 0, tzinfo=timezone.utc),
    )


def test_cli_missing_urls_exits_nonzero():
    runner = CliRunner()
    result = runner.invoke(main, [])
    assert result.exit_code != 0


def test_cli_success_with_mocked_check():
    runner = CliRunner()
    with patch("url_monitor.cli.check", return_value=_ok_result("https://example.com")):
        result = runner.invoke(main, ["https://example.com"])
    assert result.exit_code == 0
    assert "OK" in result.output
    assert "https://example.com" in result.output


def test_cli_invalid_failure_threshold():
    runner = CliRunner()
    result = runner.invoke(main, ["https://example.com", "--failure-threshold", "0"])
    assert result.exit_code == 1
    assert "Configuration error" in result.output
