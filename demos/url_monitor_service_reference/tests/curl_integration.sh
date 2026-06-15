#!/usr/bin/env bash
# Curl-based integration tests for the URL Monitor Service.
# Requires a running server at BASE_URL (default: http://127.0.0.1:8000).
# Usage:
#   ./tests/curl_integration.sh            # run all scenarios
#   BASE_URL=http://localhost:9000 ./tests/curl_integration.sh
#
# Output: terminal (coloured) + tests/curl_integration.log
# Exit code: 0 = all pass, 1 = one or more failures

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
LOG_FILE="$(dirname "$0")/curl_integration.log"
PASS=0
FAIL=0
SKIPPED=0
declare -a FAILED_SCENARIOS=()
declare -a LOG_LINES=()

# ── colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

log()    { local ts; ts=$(date '+%H:%M:%S'); local line="[$ts] $*"; echo -e "$line"; LOG_LINES+=("$line"); }
info()   { log "${CYAN}INFO${RESET}  $*"; }
pass()   { log "${GREEN}PASS${RESET}  $*"; }
fail()   { log "${RED}FAIL${RESET}  $*"; }
header() { log ""; log "${BOLD}${YELLOW}══ $* ══${RESET}"; }

# Pretty-print JSON if jq is available, otherwise raw
pretty() { command -v jq &>/dev/null && echo "$1" | jq . 2>/dev/null || echo "$1"; }

# ── assertion helpers ─────────────────────────────────────────────────────────
CURRENT_SCENARIO=""

begin_scenario() {
    CURRENT_SCENARIO="$1"
    info "Scenario: ${BOLD}$1${RESET}"
}

assert_status() {
    local label="$1" expected="$2" actual="$3" body="$4"
    if [[ "$actual" == "$expected" ]]; then
        pass "$label → HTTP $actual (expected $expected)"
        (( PASS++ )) || true
    else
        fail "$label → HTTP $actual (expected $expected)"
        fail "  Body: $(pretty "$body")"
        (( FAIL++ )) || true
        FAILED_SCENARIOS+=("$CURRENT_SCENARIO :: $label")
    fi
}

assert_field() {
    local label="$1" field="$2" expected="$3" body="$4"
    local actual
    actual=$(echo "$body" | jq -r "$field" 2>/dev/null || echo "__jq_error__")
    if [[ "$actual" == "$expected" ]]; then
        pass "$label → $field = $actual"
        (( PASS++ )) || true
    else
        fail "$label → $field expected '$expected', got '$actual'"
        (( FAIL++ )) || true
        FAILED_SCENARIOS+=("$CURRENT_SCENARIO :: $label ($field)")
    fi
}

assert_field_not_null() {
    local label="$1" field="$2" body="$3"
    local actual
    actual=$(echo "$body" | jq -r "$field" 2>/dev/null || echo "null")
    if [[ "$actual" != "null" && "$actual" != "__jq_error__" && -n "$actual" ]]; then
        pass "$label → $field is present ($actual)"
        (( PASS++ )) || true
    else
        fail "$label → $field is null or missing"
        (( FAIL++ )) || true
        FAILED_SCENARIOS+=("$CURRENT_SCENARIO :: $label ($field null)")
    fi
}

assert_number_gte() {
    local label="$1" field="$2" min="$3" body="$4"
    local actual
    actual=$(echo "$body" | jq -r "($field // -1)" 2>/dev/null || echo "-1")
    if (( actual >= min )); then
        pass "$label → $field = $actual (≥ $min)"
        (( PASS++ )) || true
    else
        fail "$label → $field = $actual (expected ≥ $min)"
        (( FAIL++ )) || true
        FAILED_SCENARIOS+=("$CURRENT_SCENARIO :: $label ($field expected ≥ $min, got $actual)")
    fi
}

# Polls GET $path every POLL_INTERVAL seconds.
# $condition is a jq boolean expression evaluated against the response body.
# Logs a status snapshot on every attempt.
# Returns 0 when condition is first satisfied; returns 1 on timeout.
# Must be called inside an `if` block — the return-1 path is caught by `set -e`.
TICK_SECONDS="${COORDINATOR_TICK_SECONDS:-5}"
POLL_INTERVAL=2

wait_for() {
    local label="$1" path="$2" condition="$3"
    local timeout_s="${4:-$(( TICK_SECONDS * 4 ))}"
    local elapsed=0
    info "Polling: ${BOLD}$label${RESET} every ${POLL_INTERVAL}s, timeout ${timeout_s}s"
    while [[ $elapsed -lt $timeout_s ]]; do
        sleep "$POLL_INTERVAL" || true
        (( elapsed += POLL_INTERVAL )) || true
        call GET "$path"
        local val snippet
        val=$(echo "$BODY" | jq -r "if ($condition) then \"true\" else \"false\" end" 2>/dev/null || echo "false")
        snippet=$(echo "$BODY" | jq -c \
            '{status:.status, failures:.consecutive_failures, last_checked:.last_checked_at}' \
            2>/dev/null || echo "${BODY:0:80}")
        log "  ${CYAN}[poll ${elapsed}s]${RESET} satisfied=$val  $snippet"
        LOG_LINES+=("METRIC method=POLL path=$path status=$STATUS elapsed_ms=${elapsed}000 scenario=$CURRENT_SCENARIO condition_met=$val")
        if [[ "$val" == "true" ]]; then
            info "Condition satisfied after ${elapsed}s"
            return 0
        fi
    done
    log "  ${RED}[poll timeout at ${timeout_s}s — condition never satisfied]${RESET}"
    return 1
}

# macOS-compatible millisecond timer
_ms_now() { python3 -c "import time; print(int(time.time() * 1000))"; }

# ── curl wrapper ──────────────────────────────────────────────────────────────
# Sets globals: $STATUS and $BODY
STATUS=""
BODY=""
call() {
    local method="$1" path="$2"; shift 2
    local url="${BASE_URL}${path}"
    local start_ms end_ms elapsed_ms
    start_ms=$(_ms_now)
    local response
    response=$(curl -s -w "\n__STATUS__%{http_code}" -X "$method" "$url" \
        -H "Content-Type: application/json" \
        "$@" 2>&1)
    end_ms=$(_ms_now)
    elapsed_ms=$(( end_ms - start_ms ))
    STATUS=$(echo "$response" | grep '__STATUS__' | sed 's/__STATUS__//')
    BODY=$(echo "$response" | sed '/__STATUS__/d')
    log "  ${CYAN}→ $method $url${RESET} [${elapsed_ms}ms] HTTP $STATUS"
    # Record for log analysis
    LOG_LINES+=("METRIC method=$method path=$path status=$STATUS elapsed_ms=$elapsed_ms scenario=$CURRENT_SCENARIO")
}

# ── pre-flight ────────────────────────────────────────────────────────────────
echo "" > "$LOG_FILE"   # reset log file

header "Pre-flight: check server reachability"
if ! curl -sf "${BASE_URL}/health" -o /dev/null; then
    fail "Server not reachable at $BASE_URL — start it before running this script."
    exit 1
fi
info "Server is reachable at $BASE_URL"

# ── SCENARIO 1: Health & Readiness ───────────────────────────────────────────
header "SCENARIO 1 — Health & Readiness"

begin_scenario "GET /health"
call GET /health
assert_status "health endpoint" "200" "$STATUS" "$BODY"
assert_field   "health status field" ".status" "ok" "$BODY"

begin_scenario "GET /ready"
call GET /ready
assert_status "readiness endpoint" "200" "$STATUS" "$BODY"
assert_field   "ready status field" ".status" "ready" "$BODY"

# ── SCENARIO 2: Create monitor — full fields ──────────────────────────────────
header "SCENARIO 2 — Create Monitor (full fields)"

begin_scenario "POST /api/v1/monitors — full"
call POST /api/v1/monitors -d '{
    "url": "https://httpbin.org/status/200",
    "display_name": "HTTPBin 200",
    "tags": ["prod", "smoke"],
    "check_interval_seconds": 30,
    "timeout_seconds": 5,
    "failure_threshold": 2,
    "enabled": true
}'
assert_status      "create full monitor"      "201" "$STATUS" "$BODY"
assert_field       "url stored"               ".url" "https://httpbin.org/status/200" "$BODY"
assert_field       "display_name stored"      ".display_name" "HTTPBin 200" "$BODY"
assert_field       "enabled is true"          ".enabled" "true" "$BODY"
assert_field       "check_interval stored"    ".check_interval_seconds" "30" "$BODY"
assert_field       "timeout stored"           ".timeout_seconds" "5" "$BODY"
assert_field       "failure_threshold stored" ".failure_threshold" "2" "$BODY"
assert_field       "initial status UNKNOWN"   ".status" "UNKNOWN" "$BODY"
assert_field_not_null "id assigned"           ".id" "$BODY"
MONITOR_ID_FULL=$(echo "$BODY" | jq -r '.id')
info "Created monitor id=$MONITOR_ID_FULL"

# ── SCENARIO 3: Create monitor — minimal (URL only) ───────────────────────────
header "SCENARIO 3 — Create Monitor (minimal, URL only)"

begin_scenario "POST /api/v1/monitors — minimal"
call POST /api/v1/monitors -d '{"url": "https://httpbin.org/status/201"}'
assert_status      "create minimal monitor"   "201" "$STATUS" "$BODY"
assert_field       "url stored"               ".url" "https://httpbin.org/status/201" "$BODY"
assert_field_not_null "id assigned"           ".id" "$BODY"
MONITOR_ID_MIN=$(echo "$BODY" | jq -r '.id')
info "Created minimal monitor id=$MONITOR_ID_MIN"

# ── SCENARIO 4: Duplicate URL → 409 ──────────────────────────────────────────
header "SCENARIO 4 — Duplicate URL Conflict (409)"

begin_scenario "POST /api/v1/monitors — duplicate URL"
call POST /api/v1/monitors -d '{"url": "https://httpbin.org/status/200"}'
assert_status "duplicate URL conflict" "409" "$STATUS" "$BODY"
assert_field  "error code CONFLICT"   ".error" "CONFLICT" "$BODY"

# ── SCENARIO 5: Invalid URL → 422 ────────────────────────────────────────────
header "SCENARIO 5 — Invalid URL Validation (422)"

begin_scenario "POST /api/v1/monitors — invalid URL"
call POST /api/v1/monitors -d '{"url": "not-a-url"}'
assert_status "invalid URL rejected" "422" "$STATUS" "$BODY"

begin_scenario "POST /api/v1/monitors — missing URL"
call POST /api/v1/monitors -d '{}'
assert_status "missing URL rejected" "422" "$STATUS" "$BODY"

# ── SCENARIO 6: List monitors with pagination ─────────────────────────────────
header "SCENARIO 6 — List Monitors & Pagination"

begin_scenario "GET /api/v1/monitors — default"
call GET /api/v1/monitors
assert_status      "list monitors"      "200" "$STATUS" "$BODY"
assert_field_not_null "total field"     ".total" "$BODY"
assert_field_not_null "items array"     ".items" "$BODY"

begin_scenario "GET /api/v1/monitors — limit=1"
call GET "/api/v1/monitors?limit=1&offset=0"
assert_status "paginated list"            "200" "$STATUS" "$BODY"
assert_field  "limit echoed back"         ".limit" "1" "$BODY"
assert_field  "offset echoed back"        ".offset" "0" "$BODY"
ITEM_COUNT=$(echo "$BODY" | jq '.items | length')
if [[ "$ITEM_COUNT" -le 1 ]]; then
    pass "pagination limit=1 → $ITEM_COUNT item(s) returned"
    (( PASS++ )) || true
else
    fail "pagination limit=1 → got $ITEM_COUNT items (expected ≤1)"
    (( FAIL++ )) || true
    FAILED_SCENARIOS+=("$CURRENT_SCENARIO :: items > limit")
fi

begin_scenario "GET /api/v1/monitors — high offset (empty page)"
call GET "/api/v1/monitors?limit=10&offset=99999"
assert_status "high-offset list"   "200" "$STATUS" "$BODY"
EMPTY_COUNT=$(echo "$BODY" | jq '.items | length')
if [[ "$EMPTY_COUNT" -eq 0 ]]; then
    pass "high offset returns empty items array"
    (( PASS++ )) || true
else
    fail "high offset returned $EMPTY_COUNT items (expected 0)"
    (( FAIL++ )) || true
    FAILED_SCENARIOS+=("$CURRENT_SCENARIO :: non-empty high offset")
fi

# ── SCENARIO 7: Get specific monitor ─────────────────────────────────────────
header "SCENARIO 7 — Get Specific Monitor"

begin_scenario "GET /api/v1/monitors/:id — exists"
call GET "/api/v1/monitors/$MONITOR_ID_FULL"
assert_status "get by id"   "200" "$STATUS" "$BODY"
assert_field  "correct id"  ".id" "$MONITOR_ID_FULL" "$BODY"
assert_field  "correct url" ".url" "https://httpbin.org/status/200" "$BODY"

# ── SCENARIO 8: Get nonexistent monitor → 404 ────────────────────────────────
header "SCENARIO 8 — Not Found (404)"

begin_scenario "GET /api/v1/monitors/:id — not found"
call GET "/api/v1/monitors/999999"
assert_status "not found"         "404" "$STATUS" "$BODY"
assert_field  "error code"        ".error" "NOT_FOUND" "$BODY"

# ── SCENARIO 9: Update monitor (PATCH) ───────────────────────────────────────
header "SCENARIO 9 — Update Monitor (PATCH)"

begin_scenario "PATCH /api/v1/monitors/:id — display_name"
call PATCH "/api/v1/monitors/$MONITOR_ID_FULL" -d '{"display_name": "HTTPBin Updated"}'
assert_status "patch accepted"         "200" "$STATUS" "$BODY"
assert_field  "display_name updated"   ".display_name" "HTTPBin Updated" "$BODY"
assert_field  "url unchanged"          ".url" "https://httpbin.org/status/200" "$BODY"

begin_scenario "PATCH /api/v1/monitors/:id — tags"
call PATCH "/api/v1/monitors/$MONITOR_ID_FULL" -d '{"tags": ["prod", "smoke", "updated"]}'
assert_status "patch tags accepted" "200" "$STATUS" "$BODY"
TAG_COUNT=$(echo "$BODY" | jq '.tags | length')
if [[ "$TAG_COUNT" -eq 3 ]]; then
    pass "tags updated → 3 tags"
    (( PASS++ )) || true
else
    fail "tags updated → expected 3, got $TAG_COUNT"
    (( FAIL++ )) || true
    FAILED_SCENARIOS+=("$CURRENT_SCENARIO :: tag count mismatch")
fi

begin_scenario "PATCH /api/v1/monitors/:id — intervals"
call PATCH "/api/v1/monitors/$MONITOR_ID_FULL" -d '{"check_interval_seconds": 120, "timeout_seconds": 15}'
assert_status "patch intervals"              "200" "$STATUS" "$BODY"
assert_field  "interval updated"             ".check_interval_seconds" "120" "$BODY"
assert_field  "timeout updated"              ".timeout_seconds" "15" "$BODY"

# ── SCENARIO 10: Disable monitor ─────────────────────────────────────────────
header "SCENARIO 10 — Disable Monitor"

begin_scenario "PATCH /api/v1/monitors/:id — disable"
call PATCH "/api/v1/monitors/$MONITOR_ID_FULL" -d '{"enabled": false}'
assert_status "disable accepted"  "200" "$STATUS" "$BODY"
assert_field  "enabled is false"  ".enabled" "false" "$BODY"

# ── SCENARIO 11: Re-enable monitor ───────────────────────────────────────────
header "SCENARIO 11 — Re-enable Monitor"

begin_scenario "PATCH /api/v1/monitors/:id — re-enable"
call PATCH "/api/v1/monitors/$MONITOR_ID_FULL" -d '{"enabled": true}'
assert_status "re-enable accepted" "200" "$STATUS" "$BODY"
assert_field  "enabled is true"    ".enabled" "true" "$BODY"

# ── SCENARIO 12: PATCH nonexistent → 404 ─────────────────────────────────────
header "SCENARIO 12 — PATCH Nonexistent Monitor (404)"

begin_scenario "PATCH /api/v1/monitors/:id — not found"
call PATCH "/api/v1/monitors/999999" -d '{"display_name": "ghost"}'
assert_status "patch not found"  "404" "$STATUS" "$BODY"
assert_field  "error code"       ".error" "NOT_FOUND" "$BODY"

# ── SCENARIO 13: Check history ───────────────────────────────────────────────
header "SCENARIO 13 — Check History"

begin_scenario "GET /api/v1/monitors/:id/checks — default"
call GET "/api/v1/monitors/$MONITOR_ID_FULL/checks"
assert_status      "checks list"        "200" "$STATUS" "$BODY"
assert_field_not_null "total"           ".total" "$BODY"

begin_scenario "GET /api/v1/monitors/:id/checks — limit & offset"
call GET "/api/v1/monitors/$MONITOR_ID_FULL/checks?limit=10&offset=0"
assert_status "checks paginated" "200" "$STATUS" "$BODY"
assert_field  "limit echoed"     ".limit" "10" "$BODY"

begin_scenario "GET /api/v1/monitors/:id/checks — nonexistent monitor"
call GET "/api/v1/monitors/999999/checks"
assert_status "checks for missing monitor" "404" "$STATUS" "$BODY"

# ── SCENARIO 14: Transition history ──────────────────────────────────────────
header "SCENARIO 14 — Status Transition History"

begin_scenario "GET /api/v1/monitors/:id/transitions — default"
call GET "/api/v1/monitors/$MONITOR_ID_FULL/transitions"
assert_status      "transitions list" "200" "$STATUS" "$BODY"
assert_field_not_null "total"         ".total" "$BODY"

begin_scenario "GET /api/v1/monitors/:id/transitions — limit & offset"
call GET "/api/v1/monitors/$MONITOR_ID_FULL/transitions?limit=5&offset=0"
assert_status "transitions paginated" "200" "$STATUS" "$BODY"
assert_field  "limit echoed"          ".limit" "5" "$BODY"

begin_scenario "GET /api/v1/monitors/:id/transitions — nonexistent monitor"
call GET "/api/v1/monitors/999999/transitions"
assert_status "transitions for missing monitor" "404" "$STATUS" "$BODY"

# ── SCENARIO 15: Status summary ──────────────────────────────────────────────
header "SCENARIO 15 — Status Summary"

begin_scenario "GET /api/v1/status/summary"
call GET /api/v1/status/summary
assert_status      "status summary"       "200" "$STATUS" "$BODY"
assert_field_not_null "total count"       ".total" "$BODY"
assert_field_not_null "up count"          ".up" "$BODY"
assert_field_not_null "down count"        ".down" "$BODY"
assert_field_not_null "unknown count"     ".unknown" "$BODY"
assert_field_not_null "monitors array"    ".monitors" "$BODY"
# Verify total = up + down + unknown
TOTAL=$(echo "$BODY" | jq '.total')
SUM=$(echo "$BODY" | jq '.up + .down + .unknown')
if [[ "$TOTAL" == "$SUM" ]]; then
    pass "summary counts consistent (total=$TOTAL = up+down+unknown=$SUM)"
    (( PASS++ )) || true
else
    fail "summary counts inconsistent (total=$TOTAL ≠ up+down+unknown=$SUM)"
    (( FAIL++ )) || true
    FAILED_SCENARIOS+=("$CURRENT_SCENARIO :: count mismatch")
fi

# ── SCENARIO 16: Create monitors with tags, then verify in list ───────────────
header "SCENARIO 16 — Monitors with Tags"

begin_scenario "POST /api/v1/monitors — with tags array"
call POST /api/v1/monitors -d '{
    "url": "https://httpbin.org/status/204",
    "display_name": "Tagged Monitor",
    "tags": ["staging", "backend", "v2"]
}'
assert_status "create with tags" "201" "$STATUS" "$BODY"
assert_field  "display_name set" ".display_name" "Tagged Monitor" "$BODY"
TAG_COUNT=$(echo "$BODY" | jq '.tags | length')
if [[ "$TAG_COUNT" -eq 3 ]]; then
    pass "3 tags stored correctly"
    (( PASS++ )) || true
else
    fail "expected 3 tags, got $TAG_COUNT"
    (( FAIL++ )) || true
    FAILED_SCENARIOS+=("$CURRENT_SCENARIO :: tag count")
fi
MONITOR_ID_TAGGED=$(echo "$BODY" | jq -r '.id')

begin_scenario "GET tagged monitor — verify tags persisted"
call GET "/api/v1/monitors/$MONITOR_ID_TAGGED"
assert_status "get tagged monitor" "200" "$STATUS" "$BODY"
RETRIEVED_TAGS=$(echo "$BODY" | jq -r '.tags | sort | join(",")')
if [[ "$RETRIEVED_TAGS" == "backend,staging,v2" ]]; then
    pass "tags round-tripped correctly: $RETRIEVED_TAGS"
    (( PASS++ )) || true
else
    fail "tags mismatch: got '$RETRIEVED_TAGS', expected 'backend,staging,v2'"
    (( FAIL++ )) || true
    FAILED_SCENARIOS+=("$CURRENT_SCENARIO :: tag values")
fi

# ── SCENARIO 17: Delete monitor ───────────────────────────────────────────────
header "SCENARIO 17 — Delete Monitor"

begin_scenario "DELETE /api/v1/monitors/:id — exists"
call DELETE "/api/v1/monitors/$MONITOR_ID_MIN"
assert_status "delete returns 204" "204" "$STATUS" "$BODY"

begin_scenario "GET /api/v1/monitors/:id — after delete (404)"
call GET "/api/v1/monitors/$MONITOR_ID_MIN"
assert_status "deleted monitor not found" "404" "$STATUS" "$BODY"

# ── SCENARIO 18: Delete nonexistent → 404 ────────────────────────────────────
header "SCENARIO 18 — Delete Nonexistent Monitor"

begin_scenario "DELETE /api/v1/monitors/:id — not found"
call DELETE "/api/v1/monitors/999999"
assert_status "delete not found" "404" "$STATUS" "$BODY"

# ── SCENARIO 19: URL change via PATCH ────────────────────────────────────────
header "SCENARIO 19 — URL Update via PATCH"

begin_scenario "PATCH /api/v1/monitors/:id — change URL"
call PATCH "/api/v1/monitors/$MONITOR_ID_FULL" -d '{"url": "https://httpbin.org/status/301"}'
assert_status "url change accepted" "200" "$STATUS" "$BODY"
assert_field  "url updated"         ".url" "https://httpbin.org/status/301" "$BODY"

begin_scenario "PATCH /api/v1/monitors/:id — URL conflict with existing"
call PATCH "/api/v1/monitors/$MONITOR_ID_FULL" -d '{"url": "https://httpbin.org/status/204"}'
assert_status "url conflict on patch" "409" "$STATUS" "$BODY"

# ── SCENARIO 20: Clean up ─────────────────────────────────────────────────────
header "SCENARIO 20 — Cleanup"

begin_scenario "DELETE remaining monitors"
for id in "$MONITOR_ID_FULL" "$MONITOR_ID_TAGGED"; do
    call DELETE "/api/v1/monitors/$id"
    if [[ "$STATUS" == "204" || "$STATUS" == "404" ]]; then
        pass "cleaned up monitor $id (HTTP $STATUS)"
        (( PASS++ )) || true
    else
        fail "cleanup monitor $id returned HTTP $STATUS"
        (( FAIL++ )) || true
        FAILED_SCENARIOS+=("$CURRENT_SCENARIO :: cleanup id=$id")
    fi
done

# ── SCENARIO 21: Scheduler fires — UNKNOWN → UP ───────────────────────────────
header "SCENARIO 21 — Scheduler: check execution (UNKNOWN → UP)"

begin_scenario "Scheduler UNKNOWN→UP — monitor state"
call POST /api/v1/monitors -d '{
    "url": "https://httpbin.org/get",
    "display_name": "Scheduler UP Test",
    "check_interval_seconds": 1,
    "timeout_seconds": 5,
    "failure_threshold": 3
}'
assert_status "create monitor for scheduler UP test" "201" "$STATUS" "$BODY"
MONITOR_ID_S21=$(echo "$BODY" | jq -r '.id')
info "Monitor id=$MONITOR_ID_S21 — waiting for scheduler to fire and set status=UP"

if wait_for "status becomes UP" "/api/v1/monitors/$MONITOR_ID_S21" '.status == "UP"' 20; then
    pass "scheduler transitioned monitor to UP within timeout"
    (( PASS++ )) || true
else
    fail "monitor never reached UP — scheduler may not be running"
    (( FAIL++ )) || true
    FAILED_SCENARIOS+=("$CURRENT_SCENARIO :: status never reached UP (scheduler may be down)")
fi

call GET "/api/v1/monitors/$MONITOR_ID_S21"
assert_status         "get monitor after scheduler check"  "200" "$STATUS" "$BODY"
assert_field          "status is UP"                       ".status" "UP" "$BODY"
assert_field          "consecutive_failures reset to 0"    ".consecutive_failures" "0" "$BODY"
assert_field_not_null "last_checked_at is populated"       ".last_checked_at" "$BODY"

begin_scenario "Scheduler UNKNOWN→UP — check record content"
call GET "/api/v1/monitors/$MONITOR_ID_S21/checks?limit=1&offset=0"
assert_status         "checks endpoint returns 200"    "200" "$STATUS" "$BODY"
assert_number_gte     "at least 1 check written to DB" ".total" 1 "$BODY"
FIRST_CHECK=$(echo "$BODY" | jq -c '.items[0]')
info "First check record: $(echo "$FIRST_CHECK" | jq .)"
assert_field          "check.success is true"          ".success" "true" "$FIRST_CHECK"
assert_field          "check.http_status is 200"       ".http_status" "200" "$FIRST_CHECK"
assert_number_gte     "check.response_time_ms ≥ 0"     ".response_time_ms" 0 "$FIRST_CHECK"
assert_field_not_null "check.checked_at is set"        ".checked_at" "$FIRST_CHECK"
assert_field_not_null "check.monitor_id is set"        ".monitor_id" "$FIRST_CHECK"

begin_scenario "Scheduler UNKNOWN→UP — transition record content"
call GET "/api/v1/monitors/$MONITOR_ID_S21/transitions?limit=1&offset=0"
assert_status         "transitions endpoint returns 200"    "200" "$STATUS" "$BODY"
assert_number_gte     "at least 1 transition written to DB" ".total" 1 "$BODY"
FIRST_TRANS=$(echo "$BODY" | jq -c '.items[0]')
info "First transition record: $(echo "$FIRST_TRANS" | jq .)"
assert_field          "transition.from_status is UNKNOWN"   ".from_status" "UNKNOWN" "$FIRST_TRANS"
assert_field          "transition.to_status is UP"          ".to_status" "UP" "$FIRST_TRANS"
assert_field_not_null "transition.check_id is set"          ".check_id" "$FIRST_TRANS"
assert_field_not_null "transition.transitioned_at is set"   ".transitioned_at" "$FIRST_TRANS"

call DELETE "/api/v1/monitors/$MONITOR_ID_S21"
assert_status "cleanup S21 monitor" "204" "$STATUS" "$BODY"

# ── SCENARIO 22: Disabled monitor is not checked ─────────────────────────────
header "SCENARIO 22 — Scheduler: disabled monitor is not checked"

begin_scenario "Disabled monitor skipped by scheduler"
call POST /api/v1/monitors -d '{
    "url": "https://httpbin.org/ip",
    "display_name": "Disabled Monitor Test",
    "check_interval_seconds": 1,
    "enabled": false
}'
assert_status "create disabled monitor" "201" "$STATUS" "$BODY"
MONITOR_ID_S22=$(echo "$BODY" | jq -r '.id')
DISABLED_WAIT=$(( TICK_SECONDS * 2 + 2 ))
info "Monitor id=$MONITOR_ID_S22 (enabled=false) — waiting ${DISABLED_WAIT}s (${TICK_SECONDS}s tick × 2 + buffer)"
sleep "$DISABLED_WAIT" || true

call GET "/api/v1/monitors/$MONITOR_ID_S22"
assert_status "get disabled monitor" "200" "$STATUS" "$BODY"
info "Disabled monitor state after ${DISABLED_WAIT}s: $(echo "$BODY" | jq -c '{status,last_checked_at,consecutive_failures}')"
assert_field  "status still UNKNOWN"     ".status" "UNKNOWN" "$BODY"
# last_checked_at should remain null because the scheduler never touched it
LAST_CHECKED=$(echo "$BODY" | jq -r '.last_checked_at')
if [[ "$LAST_CHECKED" == "null" ]]; then
    pass "last_checked_at is null — scheduler correctly skipped disabled monitor"
    (( PASS++ )) || true
else
    fail "last_checked_at is '$LAST_CHECKED' — scheduler incorrectly checked a disabled monitor"
    (( FAIL++ )) || true
    FAILED_SCENARIOS+=("$CURRENT_SCENARIO :: disabled monitor was checked (last_checked_at=$LAST_CHECKED)")
fi

call GET "/api/v1/monitors/$MONITOR_ID_S22/checks"
assert_status     "checks endpoint accessible" "200" "$STATUS" "$BODY"
assert_field      "zero check records written" ".total" "0" "$BODY"

call DELETE "/api/v1/monitors/$MONITOR_ID_S22"
assert_status "cleanup S22 monitor" "204" "$STATUS" "$BODY"

# ── SCENARIO 23: consecutive_failures increments on check failure ──────────────
header "SCENARIO 23 — Scheduler: consecutive_failures increments on failure"

begin_scenario "Failure counting increments"
call POST /api/v1/monitors -d '{
    "url": "https://httpbin.org/status/500",
    "display_name": "Failure Counting Test",
    "check_interval_seconds": 1,
    "timeout_seconds": 5,
    "failure_threshold": 10
}'
assert_status "create always-failing monitor" "201" "$STATUS" "$BODY"
MONITOR_ID_S23=$(echo "$BODY" | jq -r '.id')
info "Monitor id=$MONITOR_ID_S23 (url=.../500, threshold=10) — waiting for failure count to rise"

if wait_for "consecutive_failures ≥ 1" "/api/v1/monitors/$MONITOR_ID_S23" \
    '.consecutive_failures >= 1' 20; then
    pass "consecutive_failures incremented — scheduler is recording failures"
    (( PASS++ )) || true
else
    fail "consecutive_failures never rose above 0 within timeout"
    (( FAIL++ )) || true
    FAILED_SCENARIOS+=("$CURRENT_SCENARIO :: consecutive_failures never incremented")
fi

call GET "/api/v1/monitors/$MONITOR_ID_S23"
assert_status     "get failing monitor"            "200" "$STATUS" "$BODY"
assert_number_gte "consecutive_failures ≥ 1"       ".consecutive_failures" 1 "$BODY"
assert_field_not_null "last_checked_at set"         ".last_checked_at" "$BODY"

begin_scenario "Failure counting — check record content"
call GET "/api/v1/monitors/$MONITOR_ID_S23/checks?limit=1&offset=0"
assert_status     "checks endpoint returns 200"     "200" "$STATUS" "$BODY"
assert_number_gte "at least 1 check written"        ".total" 1 "$BODY"
FAIL_CHECK=$(echo "$BODY" | jq -c '.items[0]')
info "First failure check record: $(echo "$FAIL_CHECK" | jq .)"
assert_field      "check.success is false"          ".success" "false" "$FAIL_CHECK"
assert_field      "check.http_status is 500"        ".http_status" "500" "$FAIL_CHECK"
assert_number_gte "check.response_time_ms ≥ 0"      ".response_time_ms" 0 "$FAIL_CHECK"
# error_message should be populated for a 5xx response
ERROR_MSG=$(echo "$FAIL_CHECK" | jq -r '.error_message')
if [[ "$ERROR_MSG" != "null" && -n "$ERROR_MSG" ]]; then
    pass "check.error_message is set ('$ERROR_MSG')"
    (( PASS++ )) || true
else
    fail "check.error_message is null — expected a message for a 500 response"
    (( FAIL++ )) || true
    FAILED_SCENARIOS+=("$CURRENT_SCENARIO :: check.error_message null for 500")
fi

call DELETE "/api/v1/monitors/$MONITOR_ID_S23"
assert_status "cleanup S23 monitor" "204" "$STATUS" "$BODY"

# ── SCENARIO 24: UNKNOWN → DOWN after failure_threshold ───────────────────────
header "SCENARIO 24 — Scheduler: UNKNOWN → DOWN after failure_threshold"

begin_scenario "Scheduler UNKNOWN→DOWN — status transition"
call POST /api/v1/monitors -d '{
    "url": "https://httpbin.org/status/503",
    "display_name": "DOWN Transition Test",
    "check_interval_seconds": 1,
    "timeout_seconds": 5,
    "failure_threshold": 2
}'
assert_status "create monitor for DOWN transition" "201" "$STATUS" "$BODY"
MONITOR_ID_S24=$(echo "$BODY" | jq -r '.id')
DOWN_TIMEOUT=$(( TICK_SECONDS * 2 * 2 + 5 ))
info "Monitor id=$MONITOR_ID_S24 (threshold=2) — waiting up to ${DOWN_TIMEOUT}s for status=DOWN"

if wait_for "status becomes DOWN" "/api/v1/monitors/$MONITOR_ID_S24" \
    '.status == "DOWN"' "$DOWN_TIMEOUT"; then
    pass "monitor transitioned to DOWN after threshold failures"
    (( PASS++ )) || true
else
    fail "monitor never reached DOWN within ${DOWN_TIMEOUT}s"
    (( FAIL++ )) || true
    FAILED_SCENARIOS+=("$CURRENT_SCENARIO :: status never reached DOWN")
fi

call GET "/api/v1/monitors/$MONITOR_ID_S24"
assert_status     "get downed monitor"               "200" "$STATUS" "$BODY"
assert_field      "status is DOWN"                   ".status" "DOWN" "$BODY"
assert_number_gte "consecutive_failures ≥ threshold" ".consecutive_failures" 2 "$BODY"
assert_field_not_null "last_checked_at set"          ".last_checked_at" "$BODY"

begin_scenario "Scheduler UNKNOWN→DOWN — transition record content"
call GET "/api/v1/monitors/$MONITOR_ID_S24/transitions?limit=1&offset=0"
assert_status     "transitions endpoint returns 200"      "200" "$STATUS" "$BODY"
assert_number_gte "at least 1 DOWN transition recorded"   ".total" 1 "$BODY"
DOWN_TRANS=$(echo "$BODY" | jq -c '.items[0]')
info "DOWN transition record: $(echo "$DOWN_TRANS" | jq .)"
assert_field      "transition.to_status is DOWN"          ".to_status" "DOWN" "$DOWN_TRANS"
assert_field_not_null "transition.from_status is set"     ".from_status" "$DOWN_TRANS"
assert_field_not_null "transition.check_id is set"        ".check_id" "$DOWN_TRANS"

begin_scenario "Scheduler UNKNOWN→DOWN — check records show failures"
call GET "/api/v1/monitors/$MONITOR_ID_S24/checks?limit=5&offset=0"
assert_status     "checks endpoint returns 200"      "200" "$STATUS" "$BODY"
assert_number_gte "at least 2 checks recorded"       ".total" 2 "$BODY"
# Every check should be a failure
ALL_SUCCESS=$(echo "$BODY" | jq '[.items[].success] | all')
if [[ "$ALL_SUCCESS" == "false" ]]; then
    pass "all recorded checks have success=false"
    (( PASS++ )) || true
else
    fail "some check records incorrectly show success=true for a 503 URL"
    (( FAIL++ )) || true
    FAILED_SCENARIOS+=("$CURRENT_SCENARIO :: unexpected success check for 503 URL")
fi

call DELETE "/api/v1/monitors/$MONITOR_ID_S24"
assert_status "cleanup S24 monitor" "204" "$STATUS" "$BODY"

# ── SCENARIO 25: Cascade delete removes child records ─────────────────────────
header "SCENARIO 25 — Cascade delete removes check and transition records"

begin_scenario "Cascade delete — setup and wait for checks"
call POST /api/v1/monitors -d '{
    "url": "https://httpbin.org/headers",
    "display_name": "Cascade Delete Test",
    "check_interval_seconds": 1,
    "timeout_seconds": 5,
    "failure_threshold": 3
}'
assert_status "create monitor for cascade test" "201" "$STATUS" "$BODY"
MONITOR_ID_S25=$(echo "$BODY" | jq -r '.id')
info "Monitor id=$MONITOR_ID_S25 — waiting for at least 1 check to be written"

if wait_for "at least 1 check recorded" "/api/v1/monitors/$MONITOR_ID_S25/checks" \
    '.total >= 1' 20; then
    pass "scheduler has written at least 1 check for monitor $MONITOR_ID_S25"
    (( PASS++ )) || true
else
    fail "no check was written within timeout — cannot verify cascade"
    (( FAIL++ )) || true
    FAILED_SCENARIOS+=("$CURRENT_SCENARIO :: no checks written before cascade test")
fi

# Record counts before deletion
call GET "/api/v1/monitors/$MONITOR_ID_S25/checks"
PRE_CHECK_TOTAL=$(echo "$BODY" | jq -r '.total')
call GET "/api/v1/monitors/$MONITOR_ID_S25/transitions"
PRE_TRANS_TOTAL=$(echo "$BODY" | jq -r '.total')
info "Before DELETE: checks=$PRE_CHECK_TOTAL, transitions=$PRE_TRANS_TOTAL"

begin_scenario "Cascade delete — DELETE returns 204"
call DELETE "/api/v1/monitors/$MONITOR_ID_S25"
assert_status "delete returns 204" "204" "$STATUS" "$BODY"

begin_scenario "Cascade delete — parent resource gone (404)"
call GET "/api/v1/monitors/$MONITOR_ID_S25"
assert_status "monitor no longer exists" "404" "$STATUS" "$BODY"

begin_scenario "Cascade delete — child checks gone (404)"
call GET "/api/v1/monitors/$MONITOR_ID_S25/checks"
assert_status "checks endpoint returns 404 for deleted parent" "404" "$STATUS" "$BODY"

begin_scenario "Cascade delete — child transitions gone (404)"
call GET "/api/v1/monitors/$MONITOR_ID_S25/transitions"
assert_status "transitions endpoint returns 404 for deleted parent" "404" "$STATUS" "$BODY"
info "Pre-delete counts (checks=$PRE_CHECK_TOTAL, transitions=$PRE_TRANS_TOTAL) are now inaccessible via API — cascade confirmed"

# ── LOG ANALYSIS ──────────────────────────────────────────────────────────────
header "Log Analysis"

TOTAL_ASSERTIONS=$(( PASS + FAIL ))
info "Total assertions : $TOTAL_ASSERTIONS"
info "Passed           : ${GREEN}$PASS${RESET}"
info "Failed           : ${RED}$FAIL${RESET}"

if [[ ${#FAILED_SCENARIOS[@]} -gt 0 ]]; then
    log ""
    log "${RED}${BOLD}Failed assertions:${RESET}"
    for s in "${FAILED_SCENARIOS[@]}"; do
        log "  ${RED}✗${RESET} $s"
    done
fi

# HTTP status code distribution from metric lines
log ""
log "${BOLD}HTTP status code distribution:${RESET}"
declare -A STATUS_COUNTS
for line in "${LOG_LINES[@]}"; do
    if [[ "$line" == *"METRIC"* ]]; then
        code=$(echo "$line" | grep -o 'status=[0-9]*' | cut -d= -f2)
        [[ -z "$code" ]] && continue
        STATUS_COUNTS["$code"]=$(( ${STATUS_COUNTS["$code"]:-0} + 1 ))
    fi
done
for code in $(echo "${!STATUS_COUNTS[@]}" | tr ' ' '\n' | sort); do
    log "  HTTP $code : ${STATUS_COUNTS[$code]} call(s)"
done

# Per-scenario timing from metric lines
log ""
log "${BOLD}Slowest calls (top 5):${RESET}"
TIMING_LINES=()
for line in "${LOG_LINES[@]}"; do
    if [[ "$line" == *"METRIC"* ]]; then
        TIMING_LINES+=("$line")
    fi
done
printf '%s\n' "${TIMING_LINES[@]}" \
    | grep -o 'elapsed_ms=[0-9]*' | cut -d= -f2 \
    | sort -rn | head -5 \
    | while read -r ms; do
        # Find the full line for this ms value (first match)
        for line in "${TIMING_LINES[@]}"; do
            if echo "$line" | grep -q "elapsed_ms=${ms}"; then
                method=$(echo "$line" | grep -o 'method=[^ ]*' | cut -d= -f2)
                path=$(echo "$line" | grep -o 'path=[^ ]*' | cut -d= -f2)
                scenario=$(echo "$line" | grep -o 'scenario=.*' | cut -d= -f2)
                log "  ${ms}ms  $method $path  [$scenario]"
                break
            fi
        done
    done

# Write log to file
printf '%s\n' "${LOG_LINES[@]}" > "$LOG_FILE"
info "Full log written to: $LOG_FILE"

# ── Exit code ─────────────────────────────────────────────────────────────────
log ""
if [[ $FAIL -eq 0 ]]; then
    log "${GREEN}${BOLD}ALL SCENARIOS PASSED ✓${RESET}"
    exit 0
else
    log "${RED}${BOLD}$FAIL ASSERTION(S) FAILED ✗${RESET}"
    exit 1
fi
