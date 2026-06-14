# Task

Build a FastAPI service that monitors URLs for uptime in the background, persists monitor configuration and check results in SQLite, and exposes a REST API for managing monitors and querying status. This extends the CLI URL monitor demo's domain concepts (HTTP health checks, consecutive-failure detection, UP/DOWN transitions) into a persistent, multi-client web service with async concurrent background checks.
