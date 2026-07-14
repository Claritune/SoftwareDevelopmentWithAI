# Clarifying Questions

## Project Type
greenfield

## Goal Summary
Build a CLI tool that monitors a list of URLs for uptime, checks them on a schedule, and sends notifications when a site goes down or comes back up.

## Existing Constraints
- Project directory name implies C++ implementation (`url_monitor_cli_cpp`), but no language or build rules are documented yet.
- Cursor hooks block destructive file operations (`.cursor/hooks/block-delete.sh`, `.cursor/hooks/block-rm.sh`) — affects agent workflow, not application behavior.

## Questions

1. **Notification channels**: How should the tool notify users when a URL goes down or recovers?
   - *Why it matters*: Each channel (stdout/log, email, Slack/Discord webhook, desktop push) requires different dependencies, configuration, and error handling. Supporting multiple channels from day one significantly expands scope.
   - *Default if unanswered*: Log state changes to stdout/stderr with structured timestamps; no external notification integrations in v1.

2. **Configuration source**: Where does the URL list, check interval, and notification settings come from?
   - *Why it matters*: A config file (YAML/TOML/JSON) vs. CLI flags vs. environment variables changes the CLI surface, parsing dependencies, and how users deploy the tool.
   - *Default if unanswered*: A single config file (YAML) listing URLs, check interval, and notification settings; minimal CLI flags for config path and verbosity.

3. **Process model**: Should the tool run as a foreground daemon, background service, or one-shot check invoked by cron/systemd?
   - *Why it matters*: A self-scheduling long-running process needs signal handling, graceful shutdown, and optional PID-file/daemonization. A cron-friendly one-shot mode is simpler but shifts scheduling to the OS.
   - *Default if unanswered*: Foreground long-running process with internal timer loop; user manages lifecycle via systemd/supervisor or terminal session.

4. **Down/recovery criteria**: What conditions count as "down" vs. "up"?
   - *Why it matters*: Treating only connection failures as down vs. also flagging 4xx/5xx responses, slow responses, or SSL errors changes the HTTP client logic, retry strategy, and false-positive rate.
   - *Default if unanswered*: Down on connection timeout, DNS failure, or TCP/SSL error; also down on HTTP status ≥ 500. 4xx responses treated as "up" (reachable). Configurable timeout per URL (default 10s).

5. **State persistence across restarts**: Should the tool remember prior URL states so it doesn't re-notify on startup?
   - *Why it matters*: Without persisted state, a restart after a known outage triggers a duplicate "down" notification, and recovery detection requires at least one successful check cycle. Persistence adds a small on-disk store and migration concerns.
   - *Default if unanswered*: Persist last-known state per URL in a simple local file (e.g., JSON alongside the config); emit notifications only on state transitions.

6. **Build system and HTTP dependencies**: What C++ standard, build tool, and HTTP library should the project use?
   - *Why it matters*: Choices like C++17 + CMake + libcurl vs. C++20 + FetchContent + cpp-httplib affect portability, TLS support, packaging, and CI setup. This is foundational for all network I/O.
   - *Default if unanswered*: C++17, CMake, libcurl for HTTP(S) with system or bundled TLS; single executable target with no runtime beyond curl/OpenSSL.

7. **Scope boundaries for v1**: What is explicitly out of scope for the first version?
   - *Why it matters*: Features like a web dashboard, multi-user auth, historical uptime metrics, parallel check pools, or IPv6-only targets each add substantial design surface. A clear v1 boundary prevents scope creep.
   - *Default if unanswered*: v1 covers sequential URL checks, state-change notifications, config-file-driven setup, and graceful shutdown. Out of scope: web UI, metrics storage/history, authentication, and concurrent check workers.
