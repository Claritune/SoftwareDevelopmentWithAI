# Answers

1. **Runtime model**: Continuous foreground loop — runs until Ctrl+C. Configurable interval via `--interval` flag (default 30 seconds).

2. **HTTP library**: cpr via FetchContent. Modern C++ API, wraps libcurl, well-maintained.

3. **CLI argument parsing**: CLI11 via FetchContent. Gives us `--help`, type validation, and clean flag definitions.

4. **Failure criteria**: HTTP status >= 400 OR connection/timeout error. Redirects (3xx) count as success.

5. **Notification channel**: DOWN/UP transitions to stdout. Routine check logs to stderr. Support `--log-file` flag to append logs to a file.

6. **Concurrency**: Sequential checks for v1. Keep it simple.

7. **Test framework**: Catch2 via FetchContent.
