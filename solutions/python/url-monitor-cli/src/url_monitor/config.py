"""CLI argument parsing and YAML config loading/validation."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field

import yaml


@dataclass
class UrlSpec:
    url: str
    timeout_seconds: int = 10


@dataclass
class Config:
    check_interval_seconds: int
    urls: list[UrlSpec]


@dataclass
class CliOptions:
    config_path: str = "config.yaml"
    state_file: str | None = None
    verbose: bool = False
    stats_only: bool = False


def parse_args(argv: list[str] | None = None) -> CliOptions:
    """Parse CLI arguments and return CliOptions."""
    parser = argparse.ArgumentParser(
        prog="url-monitor",
        description="Monitor URLs for uptime and log state transitions.",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to YAML config file (default: config.yaml)",
    )
    parser.add_argument(
        "--state-file",
        default=None,
        help="Path to JSON state file (default: derived from config path)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log every check result, not just transitions",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print accumulated stats from state file and exit",
    )

    args = parser.parse_args(argv)
    return CliOptions(
        config_path=args.config,
        state_file=args.state_file,
        verbose=args.verbose,
        stats_only=args.stats,
    )


def derive_state_path(config_path: str) -> str:
    """Derive state file path from config path.

    config.yaml -> config.state.json
    config.yml  -> config.state.json
    config      -> config.state.json
    """
    root, _ = os.path.splitext(config_path)
    return root + ".state.json"


def load_config(path: str) -> Config:
    """Load and validate YAML config file.

    Raises:
        SystemExit: on config validation errors (exit code 1)
    """
    try:
        with open(path) as f:
            raw = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"config error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as exc:
        print(f"config error: invalid YAML: {exc}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(raw, dict):
        print("config error: expected a YAML mapping at top level", file=sys.stderr)
        sys.exit(1)

    # Validate check_interval_seconds
    interval = raw.get("check_interval_seconds")
    if interval is None:
        print("config error: missing 'check_interval_seconds'", file=sys.stderr)
        sys.exit(1)
    if not isinstance(interval, int) or interval < 5:
        print(
            "config error: 'check_interval_seconds' must be an integer >= 5",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate urls
    urls_raw = raw.get("urls")
    if not urls_raw or not isinstance(urls_raw, list):
        print("config error: 'urls' must be a non-empty list", file=sys.stderr)
        sys.exit(1)

    urls: list[UrlSpec] = []
    seen: set[str] = set()
    for i, entry in enumerate(urls_raw):
        if not isinstance(entry, dict) or "url" not in entry:
            print(
                f"config error: urls[{i}] must have a 'url' field", file=sys.stderr
            )
            sys.exit(1)

        url = entry["url"]
        if not isinstance(url, str) or not url.strip():
            print(f"config error: urls[{i}].url must be a non-empty string", file=sys.stderr)
            sys.exit(1)

        if not url.startswith("http://") and not url.startswith("https://"):
            print(
                f"config error: urls[{i}].url must start with http:// or https://",
                file=sys.stderr,
            )
            sys.exit(1)

        timeout = entry.get("timeout_seconds", 10)
        if not isinstance(timeout, int) or timeout < 1:
            print(
                f"config error: urls[{i}].timeout_seconds must be an integer >= 1",
                file=sys.stderr,
            )
            sys.exit(1)

        if url in seen:
            print(f"config error: duplicate url: {url}", file=sys.stderr)
            sys.exit(1)
        seen.add(url)

        urls.append(UrlSpec(url=url, timeout_seconds=timeout))

    return Config(check_interval_seconds=interval, urls=urls)
