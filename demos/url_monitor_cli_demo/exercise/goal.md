# Goal

Build a **FastAPI service** that monitors URLs for uptime in the background, stores configuration and check results in **SQLite**, and exposes a **REST API** for managing monitors and querying status. This exercise extends the concepts from the CLI URL monitor demo into a persistent, multi-client web service.

## Background

The companion CLI demo (`../`) checks URLs from the command line with in-memory state and stdout notifications. This project takes the same domain — HTTP health checks, consecutive-failure detection, UP/DOWN transitions — and implements it as a long-running API service that multiple clients can use without restarting a process.

## Functional requirements

### URL monitoring

- Monitor one or more URLs concurrently in the **background** while the API serves requests.
- Perform HTTP GET health checks on a **per-URL schedule** (configurable interval and timeout).
- A single check **fails** when the HTTP status is ≥ 400 or the request times out / cannot connect.
- Mark a URL **DOWN** after N consecutive failures (configurable per URL; sensible default, e.g. 3).
- Mark a URL **UP** again on the first successful check after being DOWN.
- Record every check result and every status transition.

### Configuration storage (SQLite)

- Persist monitored URLs and their settings in SQLite: URL, enabled flag, check interval, timeout, failure threshold, optional display name.
- Support creating, reading, updating, and deleting monitor entries via the API.
- Disabling a monitor stops checks but retains history.

### Results storage (SQLite)

- Persist check results: timestamp, URL/monitor id, HTTP status (if any), response time, success/fail, error message.
- Persist status transitions: timestamp, monitor id, from-status, to-status, triggering check details.
- Support querying recent check history and current status per monitor.

### REST API (no authentication)

Provide a JSON REST API (no auth required for this exercise):

| Area | Endpoints (illustrative) |
|------|--------------------------|
| Monitors | List, create, get, update, delete monitored URLs |
| Status | Current status per monitor; summary of all monitors |
| History | Paginated check results and transition events |
| Service | Health/readiness endpoint for the API itself |

Use standard HTTP status codes. Validation errors return structured JSON error responses.

### Background execution

- Start the monitoring scheduler when the application starts; stop it cleanly on shutdown.
- Checks for different URLs may run **concurrently** (async I/O).
- API requests must not block the monitoring loop and vice versa.

## Non-functional requirements

- **Python 3.11+**, **FastAPI**, **SQLite** (via async driver or sync with clear boundaries — decide during design).
- Configuration via **Pydantic Settings** (database path, defaults, app host/port).
- **httpx** for outbound HTTP checks; follow project async I/O conventions.
- **OpenAPI** documentation generated automatically from route definitions.
- **pytest** test suite covering API endpoints, persistence, and checker logic.
- Graceful shutdown: finish or cancel in-flight checks without corrupting stored state.

## Out of scope (for this exercise)

- Authentication, authorization, API keys, or multi-tenancy
- Slack, email, webhooks, or push notifications
- Web UI or dashboard
- Distributed / multi-node monitoring
- Log file rotation, metrics, or Prometheus
- Per-URL custom headers or authenticated target URLs

## Success criteria

A student (or agent) can:

1. `POST` a new URL to monitor and see it appear in `GET` list responses.
2. Observe background checks writing results to SQLite without manual intervention.
3. `GET` current status showing UP/DOWN after enough consecutive failures against a failing endpoint.
4. `GET` check history showing timestamps and HTTP status codes.
5. `DELETE` or disable a monitor and confirm checks stop.
6. Run `pytest` and have all tests pass.
7. Open `/docs` and interact with the API via Swagger UI.

## Relationship to the CLI demo

Reuse the **domain concepts** from the CLI project (failure criteria, consecutive failures, transitions) but do **not** copy the CLI code verbatim. The service architecture, persistence layer, async concurrency model, and REST API are new work. The FastAPI coding rules in `../docs/rules/fastapi/` apply to this exercise.
