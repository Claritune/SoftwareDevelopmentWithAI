# Code Review: urlmon

**Date:** 2026-07-14  
**Scope:** Functionality, error/edge cases, code quality, OOP practices (decoupling, encapsulation)

---

## Overall Assessment

This is a **well-scoped v1**: clear module boundaries, predictable behavior, and tests on the pure logic. The design favors plain functions and data structs over class hierarchies, which fits a sequential CLI monitor.

---

## What Works Well

**Classification and monitoring loop** are straightforward and match the spec (200-only, redirects followed, transitions only after baseline):

```cpp
// checker.cpp
Status classify(const CheckResult& r) {
  return (r.curl_code == 0 && r.http_status == 200) ? Status::Up : Status::Down;
}
```

```cpp
// monitor.cpp
// First check sets the baseline silently; only real changes notify.
if (st.status != Status::Unknown && st.status != now) {
  emit_transition(spec.url, st.status, now, result);
}
st.status = now;
st.last_checked = iso8601_now();
```

**Graceful shutdown** is handled sensibly: async-signal-safe flag, interruptible sleep (~200 ms granularity), in-flight check completes, state saved twice (after cycle + on exit).

**State persistence** uses temp-file + rename, handles missing file silently, warns on corrupt JSON, and `reconcile` correctly drops removed URLs and adds new ones as `Unknown`.

**Tests** cover the important pure logic: classification boundaries, stats accumulation, and state round-trip. Both pass (`ctest --test-dir build`).

---

## Error Cases and Edge Cases

### High Impact

| Issue | Location | Risk |
|-------|----------|------|
| **`save_state` failures are ignored** | `monitor.cpp` | Disk full, permission denied, or rename failure → silent data loss; monitoring continues |
| **`HttpClient` doesn't handle init failure** | `checker.cpp` | `curl_easy_init()` can return `nullptr`; subsequent `curl_easy_reset` would crash |
| **`std::stol` in state load can throw** | `state.cpp:27` | Malformed `http_status` keys (e.g. `"abc"`) bypass the JSON parse catch and can terminate the process |
| **`count.get<long>()` can throw** | `state.cpp:27-32` | Wrong JSON types in stats (string instead of number) → uncaught exception |

The return value of `save_state` is never checked in the monitor loop or on shutdown:

```cpp
// monitor.cpp
save_state(ctx.state_path, ctx.state);
```

No null check on `handle_` after init:

```cpp
// checker.cpp
HttpClient::HttpClient() {
  curl_global_init(CURL_GLOBAL_DEFAULT);
  handle_ = curl_easy_init();
}
```

### Medium Impact

**Duplicate URLs in config** — not validated. The same URL listed twice is checked twice per cycle, but both writes go to the same map entry, so stats double-count and work is duplicated.

**`--stats` shows stale URLs** — it reads the state file only, without reconciling against config. URLs removed from config but still in the state file appear until the monitor runs again.

**State `version` is inert** — read and written, never validated or migrated. A future schema change has no hook today.

**Corrupt stats are all-or-nothing** — one bad entry could abort load; wrapping `stats_from_json` in try/catch (or validating types) would match the resilience of the top-level JSON parse.

### Lower Impact / Behavioral Notes

- **No URL scheme validation** in config — bad URLs fail at curl time (`url_malformat`). Acceptable for v1.
- **Flapping** — one failed check immediately marks DOWN (documented in README). Not a bug, but operationally noisy.
- **Shutdown comment is slightly misleading** — the `break` runs *before* the next check starts, not mid-check; behavior is still correct.
- **`gmtime_r` is POSIX-only** — fine on macOS/Linux; not portable to Windows without `#ifdef` or C++20 `chrono` formatting. Conflicts slightly with "no compiler-specific extensions" in project conventions.

---

## Functionality Gaps vs. README Promises

| README claim | Code reality |
|--------------|--------------|
| Atomic state write | Implemented correctly via `.tmp` + `rename` |
| Restart doesn't re-emit DOWN | Correct (`Unknown` baseline + transition guard) |
| `--stats` from state file | Works; may include URLs no longer in config |
| Process exits non-zero on bad config | Yes (`return 1`) |
| Graceful shutdown saves state | Attempts save, but failure is not reported |

One subtle HTTP detail: **`CURLOPT_TIMEOUT` covers the whole transfer** including redirects. A chain of slow redirects can consume the full budget before the final status is reached. Reasonable default; worth knowing for ops.

---

## Code Quality: Overengineering and Unnecessary Complexity

**Verdict: appropriately minimal.** No unnecessary abstractions for v1.

### Good Restraint

- Free functions + plain structs instead of interfaces/factories
- `std::optional` for config load instead of a custom `Result<T,E>` (conventions mention `Result`, but `optional` + `error` string is simpler here)
- Manual `curl_error_key` switch — stable, JSON-friendly keys vs. raw `curl_easy_strerror` strings
- `void*` for `CURL*` in the header — small decoupling cost, keeps libcurl out of public headers

### Minor Unnecessary Bits

- `UrlStats::operator==` in the header exists only for tests — could live in the test file, but it's harmless
- `notifier` module name vs. role — it also owns `iso8601_now`, generic logging, and verbose check lines; naming is slightly broader than "notifications"
- `shutdown_requested()` is exported from `monitor.hpp` but only used internally — dead public API unless planned for tests/extension

### Not Overengineered (Correctly Absent per Scope)

- Thread pool, retry policy, observer pattern, plugin notification channels

---

## OOP Practices: Decoupling and Encapsulation

### Module Coupling (Good)

```
main → config, monitor, state, checker, stats
monitor → checker, config, state, notifier, stats
state → checker, stats, notifier (log_error only)
stats → checker
checker → config
notifier → checker
```

Dependencies mostly flow one way. **`MonitorContext` is an intentional aggregate** — not a class with behavior, which is fine for a procedural orchestrator:

```cpp
struct MonitorContext {
  Config config;
  StateStore state;
  std::string state_path;
  bool verbose = false;
};
```

### Encapsulation Observations

| Component | Assessment |
|-----------|------------|
| **`HttpClient`** | Good RAII, deleted copy, curl hidden via `void*`. Weak spot: no guard if init fails; `curl_global_init/cleanup` per instance is fragile if multiple instances ever exist |
| **`StateStore` / `UrlState`** | Fully public structs — acceptable at this scale; no invariant enforcement (e.g. `up_checks + down_checks == total_checks`) |
| **`Config` / `CliOptions`** | Public fields; parsing separated in `config.cpp` — clean |
| **Global shutdown flag** | `g_shutdown` in anonymous namespace — violates "no global mutable state" in conventions, but is pragmatic for signal handling; `MonitorContext` can't receive SIGINT otherwise without indirection |

### Decoupling Gaps

1. **`state.cpp` → `notifier.hpp`** — persistence layer depends on logging. A callback or returning errors to the caller would decouple I/O from presentation (minor for v1).

2. **`checker.hpp` bundles** enum, result type, classification, error-key mapping, and HTTP client — reasonable for ~100 lines, but it's the most mixed-responsibility header.

3. **No injectable check function** — `run_monitor` takes `HttpClient&`, which enables testing the loop with a fake client in theory, but there's no test for it. Acceptable given scope ("no network in unit tests").

4. **Output ordering** — `std::map` keys sort URLs alphabetically in shutdown stats and `--stats`, not config order. Decoupled from user intent, minor UX issue.

---

## Test Coverage Gaps (Not Bugs, but Blind Spots)

Automated tests do **not** cover:

- `parse_args` / `load_config` validation paths
- `reconcile` (URL add/remove)
- `derive_state_path` edge cases
- `save_state` I/O failure paths
- Monitor loop / shutdown / transition emission logic

That aligns with the testing rule (pure logic only), but it leaves integration behavior manual.

---

## Summary Ratings

| Area | Rating | Notes |
|------|--------|-------|
| **Functionality** | Strong | Delivers v1 spec cleanly |
| **Error handling** | Mixed | Config good; runtime I/O and curl init weak |
| **Edge cases** | Mixed | Duplicate URLs, corrupt stats sub-objects, save failures |
| **Overengineering** | Low | Right-sized for scope |
| **Decoupling** | Good | Clear modules; minor logging coupling |
| **Encapsulation** | Pragmatic | Public structs; fine for CLI, not for a library |

---

## Highest-Value Fixes (If Iterating)

1. Check `save_state` return value; log error (and optionally exit non-zero on shutdown save failure).
2. Guard `HttpClient` against failed `curl_easy_init()`.
3. Wrap `stats_from_json` parsing in try/catch (or use `.get<long>()` with type checks) so corrupt stats don't crash.
4. Reject duplicate URLs in `load_config`.
5. Optionally reconcile state in `--stats` mode if you want config-aligned output.

None of these require architectural rework — the codebase is in good shape for a focused v1 monitor.
