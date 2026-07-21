# Answers

1. **Notification channels**: Log state changes to stdout/stderr with structured timestamps; no external notification integrations in v1.

2. **Configuration source**: A single YAML config file listing URLs, check interval, and notification settings; minimal CLI flags for config path and verbosity.

3. **Process model**: Foreground long-running process with internal timer loop; user manages lifecycle via systemd/supervisor or terminal session.

4. **Down/recovery criteria**: **Up** only when HTTP status is exactly 200. **Down** on any other HTTP status (1xx, 3xx after redirect resolution, 4xx, 5xx), connection timeout, DNS failure, or TCP/SSL error. Configurable timeout per URL (default 10s). Accumulate per-response-type statistics (HTTP status codes and curl error categories) across checks.

5. **State persistence across restarts**: Persist last-known state per URL in a simple local file (JSON alongside the config); emit notifications only on state transitions.

6. **Build system and HTTP dependencies**: C++17, CMake, libcurl for HTTP(S) with system or bundled TLS; single executable target with no runtime beyond curl/OpenSSL.

7. **Scope boundaries for v1**: v1 covers sequential URL checks, state-change notifications, config-file-driven setup, and graceful shutdown. Out of scope: web UI, metrics storage/history, authentication, and concurrent check workers.
