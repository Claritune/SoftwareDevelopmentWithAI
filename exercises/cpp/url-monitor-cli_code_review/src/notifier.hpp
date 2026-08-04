#pragma once

#include <string>

#include "checker.hpp"

std::string iso8601_now();

void log_info(const std::string& msg);
void log_error(const std::string& msg);

// One line per state transition, fixed-width status column:
//   2026-07-14T10:05:00Z DOWN  https://example.com  (HTTP 503, 1234ms)
void emit_transition(const std::string& url, Status prev, Status now,
                     const CheckResult& r);

// One line per check regardless of transition (verbose mode).
void log_check(const std::string& url, Status s, const CheckResult& r);
