# Answers

1. **Runtime model**: One-shot command only — no long-lived daemon.

2. **URL list and configuration**: URLs and settings provided via CLI arguments.

3. **Notification channels**: Stdout only for now.

4. **Persistence**: In-memory during the run plus log output — no database.

5. **"Down" criteria**: A site is considered down after consecutive failures (error HTTP status or connection timeout). The required failure count is configurable via a CLI flag with a sensible default.

6. **Concurrency model**: Sequential checks — no concurrency at this stage.

7. **Stack alignment**: Pure Python CLI.
