# Curl Integration Test Report

**Run date:** 2026-06-15  
**Base URL:** http://127.0.0.1:8000  
**Script:** `tests/curl_integration.sh`  
**Result:** 78/78 assertions passed — ALL SCENARIOS PASSED

---

## Coverage boundary

The tests exercise the **HTTP API surface only** — request routing, persistence round-trips visible through the API, and error contract. They do **not** verify internal scheduler behaviour (see [Gap analysis](#gap-analysis)).

---

## Scenario Results

### Scenario 1 — Health & Readiness

**Purpose:** Confirm the process is up and the database connection is live before running anything else.

| Assertion | Endpoint | Expected | Result |
|-----------|----------|----------|--------|
| HTTP 200 | `GET /health` | 200 | PASS |
| `status` = `"ok"` | `GET /health` | `"ok"` | PASS |
| HTTP 200 | `GET /ready` | 200 | PASS |
| `status` = `"ready"` | `GET /ready` | `"ready"` | PASS |

**What is tested:** The process is reachable and the DB connection used by `/ready` is healthy.  
**What is not tested:** Whether the background scheduler task is running.

---

### Scenario 2 — Create Monitor (full fields)

**Purpose:** Verify that all fields in `MonitorCreate` are stored and returned correctly on creation.

| Assertion | Field | Expected | Result |
|-----------|-------|----------|--------|
| HTTP 201 | — | 201 | PASS |
| URL stored | `.url` | `https://httpbin.org/status/200` | PASS |
| display_name stored | `.display_name` | `"HTTPBin 200"` | PASS |
| enabled flag | `.enabled` | `true` | PASS |
| check_interval_seconds | `.check_interval_seconds` | `30` | PASS |
| timeout_seconds | `.timeout_seconds` | `5` | PASS |
| failure_threshold | `.failure_threshold` | `2` | PASS |
| Initial status | `.status` | `"UNKNOWN"` | PASS |
| ID assigned | `.id` | non-null | PASS |

**What is tested:** All writable fields are persisted and echoed back; new monitors start in UNKNOWN status.  
**What is not tested:** Whether the scheduler picks up this monitor on its next tick.

---

### Scenario 3 — Create Monitor (minimal, URL only)

**Purpose:** Verify that only `url` is required and defaults apply for omitted fields.

| Assertion | Field | Expected | Result |
|-----------|-------|----------|--------|
| HTTP 201 | — | 201 | PASS |
| URL stored | `.url` | `https://httpbin.org/status/201` | PASS |
| ID assigned | `.id` | non-null | PASS |

**What is tested:** Minimal creation works; server supplies default values for interval, timeout, threshold.  
**What is not tested:** That defaults match the configured `Settings` values.

---

### Scenario 4 — Duplicate URL Conflict (409)

**Purpose:** The unique constraint on `url` must be surfaced as a structured 409, not a 500.

| Assertion | Field | Expected | Result |
|-----------|-------|----------|--------|
| HTTP 409 | — | 409 | PASS |
| Error code | `.error` | `"CONFLICT"` | PASS |

**What is tested:** Duplicate URL returns the correct error code and status.

---

### Scenario 5 — Input Validation (422)

**Purpose:** Invalid or missing `url` must be rejected at the schema layer with 422.

| Assertion | Input | Expected | Result |
|-----------|-------|----------|--------|
| HTTP 422 — invalid URL | `"not-a-url"` | 422 | PASS |
| HTTP 422 — missing URL | `{}` | 422 | PASS |

**What is tested:** Pydantic validation rejects bad input before it reaches the database layer.

---

### Scenario 6 — List Monitors & Pagination

**Purpose:** Verify the list endpoint returns all monitors and that `limit`/`offset` are respected.

| Assertion | Case | Expected | Result |
|-----------|------|----------|--------|
| HTTP 200 | default list | 200 | PASS |
| `.total` present | default list | non-null | PASS |
| `.items` present | default list | non-null | PASS |
| HTTP 200 | `limit=1` | 200 | PASS |
| `.limit` echoed | `limit=1` | `1` | PASS |
| `.offset` echoed | `offset=0` | `0` | PASS |
| Items ≤ limit | `limit=1` | ≤ 1 item | PASS |
| HTTP 200 | `offset=99999` | 200 | PASS |
| Empty items | `offset=99999` | 0 items | PASS |

**What is tested:** Pagination envelope fields are correct; over-offset returns an empty page, not an error.

---

### Scenario 7 — Get Specific Monitor

**Purpose:** Retrieve a single monitor by ID and confirm identity.

| Assertion | Field | Expected | Result |
|-----------|-------|----------|--------|
| HTTP 200 | — | 200 | PASS |
| Correct ID | `.id` | created ID | PASS |
| Correct URL | `.url` | `https://httpbin.org/status/200` | PASS |

**What is tested:** GET by ID returns the correct resource.

---

### Scenario 8 — Not Found (404)

**Purpose:** Missing resource ID returns a structured 404, not a 500.

| Assertion | Field | Expected | Result |
|-----------|-------|----------|--------|
| HTTP 404 | — | 404 | PASS |
| Error code | `.error` | `"NOT_FOUND"` | PASS |

**What is tested:** Non-existent ID produces a correctly structured error response.

---

### Scenario 9 — Partial Update via PATCH

**Purpose:** Each updateable field can be changed independently; unset fields are not reset.

| Assertion | Sub-case | Field | Expected | Result |
|-----------|----------|-------|----------|--------|
| HTTP 200 | display_name | — | 200 | PASS |
| display_name updated | display_name | `.display_name` | `"HTTPBin Updated"` | PASS |
| url unchanged | display_name | `.url` | original URL | PASS |
| HTTP 200 | tags | — | 200 | PASS |
| 3 tags stored | tags | `.tags` length | 3 | PASS |
| HTTP 200 | intervals | — | 200 | PASS |
| interval updated | intervals | `.check_interval_seconds` | `120` | PASS |
| timeout updated | intervals | `.timeout_seconds` | `15` | PASS |

**What is tested:** PATCH is truly partial — other fields survive the update.  
**What is not tested:** Whether a changed `check_interval_seconds` is picked up by the scheduler on the next tick.

---

### Scenario 10 — Disable Monitor

**Purpose:** Setting `enabled=false` is persisted.

| Assertion | Field | Expected | Result |
|-----------|-------|----------|--------|
| HTTP 200 | — | 200 | PASS |
| Enabled flag | `.enabled` | `false` | PASS |

**What is tested:** `enabled` field is written.  
**What is not tested:** Whether the scheduler skips the monitor after it is disabled.

---

### Scenario 11 — Re-enable Monitor

**Purpose:** Setting `enabled=true` reverts a previous disable.

| Assertion | Field | Expected | Result |
|-----------|-------|----------|--------|
| HTTP 200 | — | 200 | PASS |
| Enabled flag | `.enabled` | `true` | PASS |

**What is tested:** `enabled` can be toggled back.

---

### Scenario 12 — PATCH Nonexistent Monitor (404)

**Purpose:** PATCH on a missing ID returns a structured 404.

| Assertion | Field | Expected | Result |
|-----------|-------|----------|--------|
| HTTP 404 | — | 404 | PASS |
| Error code | `.error` | `"NOT_FOUND"` | PASS |

---

### Scenario 13 — Check History

**Purpose:** The `/checks` sub-resource is paginated and returns 404 for a missing parent.

| Assertion | Case | Expected | Result |
|-----------|------|----------|--------|
| HTTP 200 | default | 200 | PASS |
| `.total` present | default | non-null | PASS |
| HTTP 200 | `limit=10` | 200 | PASS |
| `.limit` echoed | `limit=10` | `10` | PASS |
| HTTP 404 | unknown monitor | 404 | PASS |

**What is tested:** Pagination contract on the check history endpoint; 404 propagation for an invalid parent.  
**What is not tested:** That check records contain correct `http_status`, `response_time_ms`, and `success` values written by the checker.

---

### Scenario 14 — Status Transition History

**Purpose:** The `/transitions` sub-resource is paginated and returns 404 for a missing parent.

| Assertion | Case | Expected | Result |
|-----------|------|----------|--------|
| HTTP 200 | default | 200 | PASS |
| `.total` present | default | non-null | PASS |
| HTTP 200 | `limit=5` | 200 | PASS |
| `.limit` echoed | `limit=5` | `5` | PASS |
| HTTP 404 | unknown monitor | 404 | PASS |

**What is tested:** Pagination contract on the transition history endpoint.  
**What is not tested:** That transitions are written with the correct `from_status`/`to_status` values by the checker.

---

### Scenario 15 — Status Summary

**Purpose:** The aggregate summary endpoint reflects all monitors and has internally consistent counts.

| Assertion | Field | Expected | Result |
|-----------|-------|----------|--------|
| HTTP 200 | — | 200 | PASS |
| `.total` present | — | non-null | PASS |
| `.up` present | — | non-null | PASS |
| `.down` present | — | non-null | PASS |
| `.unknown` present | — | non-null | PASS |
| `.monitors` present | — | non-null | PASS |
| Count consistency | total == up+down+unknown | equal | PASS |

**What is tested:** Summary counts are self-consistent and all expected fields are present.

---

### Scenario 16 — Tags Round-Trip

**Purpose:** Tags survive a POST → GET round-trip and are returned as an ordered array.

| Assertion | Field | Expected | Result |
|-----------|-------|----------|--------|
| HTTP 201 | — | 201 | PASS |
| display_name set | `.display_name` | `"Tagged Monitor"` | PASS |
| 3 tags on create | `.tags` length | 3 | PASS |
| HTTP 200 on GET | — | 200 | PASS |
| Tags match (sorted) | `.tags` sorted | `backend,staging,v2` | PASS |

**What is tested:** Tags are persisted as a JSON array and survive deserialization intact.

---

### Scenario 17 — Delete Monitor

**Purpose:** DELETE removes the resource; a subsequent GET returns 404.

| Assertion | Case | Expected | Result |
|-----------|------|----------|--------|
| HTTP 204 | DELETE | 204 | PASS |
| HTTP 404 | GET after DELETE | 404 | PASS |

**What is tested:** Resource is gone from the API after deletion.  
**What is not tested:** Whether child `checks` and `transitions` rows are also removed (cascade delete).

---

### Scenario 18 — Delete Nonexistent Monitor

**Purpose:** DELETE on a missing ID returns 404, not 204 or 500.

| Assertion | Expected | Result |
|-----------|----------|--------|
| HTTP 404 | 404 | PASS |

---

### Scenario 19 — URL Update via PATCH

**Purpose:** `url` can be changed via PATCH, but setting it to an already-used URL returns 409.

| Assertion | Case | Expected | Result |
|-----------|------|----------|--------|
| HTTP 200 | change URL | 200 | PASS |
| URL updated | `.url` | new URL | PASS |
| HTTP 409 | conflict | 409 | PASS |

**What is tested:** URL uniqueness constraint is enforced on PATCH, not just POST.

---

### Scenario 20 — Cleanup

**Purpose:** Remove all monitors created by this test run so the database is left clean.

| Assertion | Monitor | Expected | Result |
|-----------|---------|----------|--------|
| HTTP 204 or 404 | id from S2 | 204/404 | PASS |
| HTTP 204 or 404 | id from S16 | 204/404 | PASS |

---

## Run statistics

| Metric | Value |
|--------|-------|
| Total assertions | 78 |
| Passed | 78 |
| Failed | 0 |
| Total curl calls | 34 |
| HTTP 200 responses | 18 |
| HTTP 201 responses | 3 |
| HTTP 204 responses | 3 |
| HTTP 404 responses | 6 |
| HTTP 409 responses | 2 |
| HTTP 422 responses | 2 |
| Slowest call | 226 ms (`POST /api/v1/monitors`) |
| Fastest call | 188 ms (`GET /api/v1/monitors?limit=1`) |

---

## Gap analysis

The scenarios above test the HTTP contract. The internal engine — scheduler, checker, and DB writes — is **not exercised** by any of these tests. The specific gaps are:

| Internal behaviour | Gap |
|--------------------|-----|
| Scheduler runs checks on due monitors | Not tested. Tests create monitors but do not wait for the scheduler tick to fire and confirm `last_checked_at` changes. |
| `consecutive_failures` increments correctly | Not tested. Requires a monitor pointed at a URL that returns 4xx/5xx, then polling until the counter rises. |
| Status transitions UNKNOWN → UP | Not tested. Requires waiting for the checker to fire at least once for an enabled monitor pointed at a working URL. |
| Status transitions UP → DOWN after `failure_threshold` failures | Not tested. Requires a controllable failing URL and waiting N ticks. |
| Disabled monitors are skipped by the scheduler | Not tested. After `enabled=false`, the scheduler should not fire a check; there is no assertion that `last_checked_at` stays frozen. |
| Cascade delete removes child rows | Not tested. After `DELETE /monitors/:id`, the `checks` and `transitions` rows should be gone; no query verifies this. |
| Check record content (http_status, response_time_ms, success) | Partially tested — `total` is checked, but the actual field values inside returned check records are not inspected. |
| Transition record content (from_status, to_status, check_id) | Same as above — count is present, field values are not asserted. |

These gaps would require scheduler-aware tests: create a monitor, wait up to one tick (`COORDINATOR_TICK_SECONDS`, default 5 s), then assert on the resulting state.
