# url-monitor

A Python CLI tool that monitors a list of URLs for uptime. It checks each URL
sequentially on a schedule, logs state transitions (`DOWN`/`UP`) to stdout,
persists last-known state and cumulative response statistics in a JSON sidecar
file, and shuts down gracefully on `Ctrl+C`.

This is the Python solution to the url-monitor-cli exercise, mirroring the
architecture of the C++ `urlmon` solution.

## Classification rule (200-only)

A URL is **up** if and only if the HTTP status is `200` and no error occurred.
Redirects are followed, so a final `200` after redirects counts as up.
**Everything else is down**: 3xx (final status), 4xx, 5xx, connection timeouts,
DNS failures, and any `httpx` exception.

A single failed check flips a URL to down -- there is no retry or
consecutive-failure threshold in v1.

## Install

```bash
pip install -e ".[dev]"
```

## Run

```bash
url-monitor --config config/example.yaml
```

| Flag | Meaning |
|---|---|
| `--config <path>` | YAML config file (default: `config.yaml`) |
| `--state-file <path>` | JSON state file (default: derived from config path, e.g. `config.yaml` -> `config.state.json`) |
| `--verbose` | Log every check result, not just transitions |
| `--stats` | Print accumulated per-URL statistics from the state file and exit |
| `--help` | Show usage |

## Test

```bash
pytest tests/ -v
```

## Output

The first check of a URL sets its baseline silently. After that, only state
transitions are logged (unless `--verbose`):

```
2026-08-04T10:05:00Z DOWN  https://example.com  (HTTP 503, 1234ms)
2026-08-04T10:10:00Z UP    https://example.com  (HTTP 200, 456ms)
```

## Statistics

Every check increments per-URL counters. Counters persist across restarts.
`--stats` (and the shutdown summary) render them:

```
https://example.com   checks=120  up=118  down=2  uptime=98.3%
  HTTP  200: 118   503: 2
  errors  (none)
```

## Architecture

| Module | Responsibility |
|---|---|
| `config.py` | CLI argument parsing (argparse), YAML config loading/validation |
| `checker.py` | HTTP checking via httpx, status classification (200-only) |
| `monitor.py` | Main check loop, signal handling, interruptible sleep |
| `notifier.py` | Stdout logging, transition emission, ISO 8601 timestamps |
| `state.py` | JSON sidecar load/save (atomic), state reconciliation |
| `stats.py` | Per-URL counter accumulation, stats formatting |

## Limitations (v1)

- Sequential checks with a single global interval (no per-URL schedules).
- Stdout is the only notification channel.
- No retries, backoff, or flap suppression.
- No config hot-reload -- restart to pick up changes.
