# Clarifying Questions

## Project Type
greenfield

## Goal Summary
Build a C++ CLI tool that monitors URLs for uptime. It checks URLs on a schedule, tracks consecutive failures, and prints DOWN/UP transition notifications to stdout. Runs as a foreground process until interrupted.

## Existing Constraints
None — empty project with only `goal.md`.

## Questions

1. **Runtime model**: Should the tool run a continuous foreground poll loop (runs until Ctrl+C), or perform a single check round and exit?
   - *Why it matters*: A poll loop requires signal handling and a sleep/timer mechanism. A single-round tool is simpler but less useful for monitoring.
   - *Default if unanswered*: Continuous foreground loop with configurable interval.

2. **HTTP library**: Should we use libcurl (C API, available on macOS by default) or a C++ wrapper like cpr/cpp-httplib (friendlier API, pulled via FetchContent)?
   - *Why it matters*: libcurl is already installed but has a verbose C-style API. cpr wraps libcurl with modern C++ idioms but adds a build dependency. cpp-httplib is header-only but has fewer features.
   - *Default if unanswered*: cpr via FetchContent (wraps libcurl, modern C++ API).

3. **CLI argument parsing**: Should we use a library like CLI11 (header-only, popular) or parse argv manually?
   - *Why it matters*: CLI11 gives us `--help`, type validation, and subcommands for free. Manual parsing is boilerplate-heavy and error-prone for multiple flags.
   - *Default if unanswered*: CLI11 via FetchContent.

4. **Failure criteria**: What constitutes a "failed" check — HTTP status >= 400, any non-2xx status, or only connection/timeout errors?
   - *Why it matters*: A 301 redirect could be normal or a sign of misconfiguration. The threshold definition affects false-positive rates.
   - *Default if unanswered*: HTTP status >= 400 OR connection/timeout error.

5. **Notification channel**: Should DOWN/UP transitions go to stdout only, or also support logging to a file?
   - *Why it matters*: File logging requires a logging library or manual file I/O. stdout-only is simpler and composable with shell redirection.
   - *Default if unanswered*: Transitions to stdout, routine check details to stderr. Optional `--log-file` flag for file logging.

6. **Concurrency**: Should URL checks run sequentially or in parallel (e.g., std::async, thread pool)?
   - *Why it matters*: Sequential is simpler but slow with many URLs. Parallel requires thread safety for shared state (the UP/DOWN tracker).
   - *Default if unanswered*: Sequential checks — simplicity over speed for v1.

7. **Test framework**: Should we use Catch2, Google Test, or doctest for unit tests?
   - *Why it matters*: All three work well with CMake FetchContent. Catch2 has the nicest assertion syntax. Google Test is the industry standard. doctest is fastest to compile.
   - *Default if unanswered*: Catch2 via FetchContent.
