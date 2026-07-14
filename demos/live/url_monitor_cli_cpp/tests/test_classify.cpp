// Unit tests for the 200-only classification rule. Pure logic, no network:
// CheckResult values are constructed directly.

#include <cassert>
#include <iostream>

#include "checker.hpp"

namespace {

CheckResult make(long http_status, int curl_code) {
  CheckResult r;
  r.http_status = http_status;
  r.curl_code = curl_code;
  if (curl_code != 0) {
    r.curl_error_name = curl_error_key(curl_code);
  }
  return r;
}

}  // namespace

int main() {
  // Up: only a completed request with final status 200.
  assert(classify(make(200, 0)) == Status::Up);

  // Down: every non-200 HTTP status.
  assert(classify(make(301, 0)) == Status::Down);
  assert(classify(make(404, 0)) == Status::Down);
  assert(classify(make(500, 0)) == Status::Down);
  assert(classify(make(503, 0)) == Status::Down);

  // Down: curl-level failure (28 == CURLE_OPERATION_TIMEDOUT).
  assert(classify(make(0, 28)) == Status::Down);

  // Down: status 0 with no curl error (nothing observed).
  assert(classify(make(0, 0)) == Status::Down);

  // Even status 200 alongside a curl error is Down.
  assert(classify(make(200, 28)) == Status::Down);

  // Stable curl error keys.
  assert(curl_error_key(28) == "operation_timedout");
  assert(curl_error_key(6) == "couldnt_resolve_host");
  assert(curl_error_key(7) == "couldnt_connect");
  assert(curl_error_key(9999) == "curl_error_9999");

  // Status names used in logs and state file.
  assert(std::string(status_name(Status::Up)) == "up");
  assert(std::string(status_name(Status::Down)) == "down");
  assert(std::string(status_name(Status::Unknown)) == "unknown");

  std::cout << "test_classify: all assertions passed\n";
  return 0;
}
