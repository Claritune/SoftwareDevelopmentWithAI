# urlmon

A single-binary CLI tool that monitors a list of URLs for uptime. It checks
each URL sequentially on a schedule, logs state transitions (`DOWN`/`UP`) to
stdout, persists last-known state and cumulative response statistics in a JSON
sidecar file, and shuts down gracefully on `Ctrl+C`.

## Classification rule (200-only)

A URL is **up** if and only if the final HTTP status is `200`. Redirects are
followed (up to 5), so a final `200` after redirects still counts as up.
**Everything else is down**: 3xx (if it's the final status), 4xx (including
401/403), 5xx, connection timeouts, DNS failures, TCP/SSL errors, and status 0.
Point urlmon at endpoints that ultimately return 200.

Note: a single failed check flips a URL to down — there is no retry or
consecutive-failure threshold in v1, so flaky networks can produce false
positives.

## Dependencies

- CMake 3.16 or newer
- A C++17 compiler
- libcurl development headers with TLS support (preinstalled on macOS; on
  Debian/Ubuntu: `apt install libcurl4-openssl-dev`)

`yaml-cpp 0.8.0` and `nlohmann/json v3.12.0` are fetched automatically during
the first CMake configure, so the first build downloads and compiles them —
expect an extra minute.

## Build

```bash
cmake -S . -B build
cmake --build build
ctest --test-dir build   # unit tests (classification + stats)
```

## Configuration

```yaml
check_interval_seconds: 60   # required, minimum 5
urls:                        # required, non-empty
  - url: https://example.com
    timeout_seconds: 10      # optional, default 10
  - url: https://api.example.com/health
```

See `config/example.yaml`. The process exits non-zero with a message if the
config file is missing or invalid.

## Usage

```bash
./build/urlmon --config config/example.yaml
```

| Flag | Meaning |
|---|---|
| `--config <path>` | YAML config file (default: `config.yaml`) |
| `--state-file <path>` | JSON state file (default: config path with its extension replaced by `.state.json`, e.g. `config.yaml` → `config.state.json`) |
| `--verbose` | Log every check result, not just transitions |
| `--stats` | Print accumulated per-URL statistics from the state file and exit |
| `--help` | Show usage |

### Output

The first check of a URL sets its baseline silently. After that, only state
transitions are logged (unless `--verbose`):

```
2026-07-14T10:05:00Z DOWN  https://example.com  (HTTP 503, 1234ms)
2026-07-14T10:10:00Z UP    https://example.com  (HTTP 200, 456ms)
```

### Statistics

Every check increments per-URL counters keyed by HTTP status code or curl
error name. Counters are persisted and survive restarts. `--stats` (and the
shutdown summary) render them:

```
https://example.com   checks=120  up=118  down=2  uptime=98.3%
  HTTP  200: 118   503: 2
  curl  (none)
```

## State file and lifecycle

- State is written atomically (temp file + rename) after every check cycle, so
  a crash never leaves a corrupt file.
- On restart, the last-known status is loaded — a URL that was already down
  does **not** re-emit a `DOWN` notification.
- URLs added to the config start as `unknown` (silent baseline); URLs removed
  from the config are dropped from the state file, discarding their stats.
- `SIGINT`/`SIGTERM` (e.g. `Ctrl+C`) stop the monitor gracefully: the in-flight
  check finishes, state is saved, a stats summary is printed, and the process
  exits 0. During the interval sleep, shutdown takes effect within ~200 ms.

## Limitations (v1)

- Sequential checks with a single global interval (no per-URL schedules).
- Stdout is the only notification channel.
- No retries, backoff, or flap suppression.
- No config hot-reload — restart to pick up changes.
