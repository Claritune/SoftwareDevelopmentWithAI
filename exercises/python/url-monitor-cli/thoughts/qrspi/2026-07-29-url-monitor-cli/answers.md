# Answers

1. **Runtime model**: Long-lived foreground process that loops every `--interval`
   seconds until interrupted (Ctrl-C). *(default)*

2. **URL source**: URLs supplied as positional CLI arguments, with global flags
   (`--interval`, `--timeout`, `--failure-threshold`) applying to all URLs. *(default)*

3. **Definition of "down"**: A site is DOWN after N consecutive failures
   (`--failure-threshold`, default 3). A failure is any timeout, connection error,
   or non-2xx HTTP status. *(default)*

4. **HTTP library and I/O model**: `httpx` in **async** mode. URLs within a cycle
   are checked **concurrently** using async I/O.

5. **Notification channels & output format**: stdout only, with an optional
   `--log-file` mirroring the same lines. Line format:
   `[2026-06-11T10:00:00Z] DOWN  https://example.com  (3 consecutive failures, last: HTTP 503)`. *(default)*

6. **Notification trigger policy**: Print only on state transitions (down→up,
   up→down); an optional `--verbose` flag enables per-check lines. *(default)*

7. **Testing & packaging**: `pyproject.toml` exposing a `url-monitor` console
   script; `pytest` tests mocking HTTP and time so no real network or sleeping is
   required. *(default)*
