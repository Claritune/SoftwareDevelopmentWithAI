# Answers

1. **Notification channels**: Log state changes to stdout with ISO 8601 timestamps; no external notification integrations in v1.

2. **Concurrency model**: Sequential checks using synchronous `httpx.Client`. Matches the C++ solution's model.

3. **Scope boundaries for v1**: Sequential checks, state-change notifications, YAML config, JSON state persistence, graceful shutdown. Out of scope: web UI, async checks, retries, hot-reload, per-URL intervals.

4. **HTTP library**: `httpx` with synchronous `Client`. Follow redirects, configurable per-URL timeout.

5. **Config format**: YAML via `pyyaml`, matching the C++ solution.

6. **CLI parsing**: `argparse` from stdlib.

7. **State file atomicity**: `tempfile.mkstemp()` + `os.replace()` for atomic writes.

8. **Notification format**: Match the C++ format. `<timestamp> <STATUS>  <url>  (<detail>)`. Error details use `(error: <key>)` instead of `(curl: <key>)`.

9. **Stats output**: Same layout as C++, with `errors` label instead of `curl`.

10. **Test framework**: `pytest`, listed as a dev dependency in `pyproject.toml`.

11. **Test scope**: Pure-logic unit tests only — classification, stats accumulation, state round-trip. No mocked HTTP in v1.

12. **Test coverage target**: No formal target. Focus on classification edge cases and stats correctness.
