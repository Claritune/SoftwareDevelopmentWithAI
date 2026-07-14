// Unit tests for stats accumulation and state-file round-trip. Pure logic:
// CheckResult values are constructed directly, serialization uses a temp file.

#include <cassert>
#include <cstdio>
#include <iostream>
#include <string>

#include "state.hpp"
#include "stats.hpp"

namespace {

CheckResult http(long status) {
  CheckResult r;
  r.http_status = status;
  return r;
}

CheckResult curl_fail(int code) {
  CheckResult r;
  r.curl_code = code;
  r.curl_error_name = curl_error_key(code);
  return r;
}

void apply(UrlStats& s, const CheckResult& r) { record(s, r, classify(r)); }

}  // namespace

int main() {
  // Accumulation: 200, 200, 503, timeout.
  UrlStats s;
  apply(s, http(200));
  apply(s, http(200));
  apply(s, http(503));
  apply(s, curl_fail(28));  // CURLE_OPERATION_TIMEDOUT

  assert(s.total_checks == 4);
  assert(s.up_checks == 2);
  assert(s.down_checks == 2);
  assert(s.http_status.at(200) == 2);
  assert(s.http_status.at(503) == 1);
  assert(s.http_status.size() == 2);
  assert(s.curl_error.at("operation_timedout") == 1);
  assert(s.curl_error.size() == 1);

  // Formatting: uptime 2/4 = 50.0%.
  const std::string block = format_stats("https://example.com", s);
  assert(block.find("checks=4") != std::string::npos);
  assert(block.find("uptime=50.0%") != std::string::npos);
  assert(block.find("200: 2") != std::string::npos);
  assert(block.find("503: 1") != std::string::npos);
  assert(block.find("operation_timedout: 1") != std::string::npos);

  // Serialization round-trip through save_state/load_state.
  StateStore store;
  UrlState st;
  st.status = Status::Down;
  st.last_checked = "2026-07-14T10:00:00Z";
  st.stats = s;
  store.urls["https://example.com"] = st;

  const std::string path = "test_stats_roundtrip.state.json";
  assert(save_state(path, store));
  StateStore loaded = load_state(path);
  std::remove(path.c_str());

  assert(loaded.version == store.version);
  assert(loaded.urls.size() == 1);
  const UrlState& lst = loaded.urls.at("https://example.com");
  assert(lst.status == Status::Down);
  assert(lst.last_checked == "2026-07-14T10:00:00Z");
  assert(lst.stats == s);

  // Legacy state entry without a "stats" key loads with zeroed stats.
  StateStore empty_stats;
  empty_stats.urls["https://old.example.com"] = UrlState{};
  assert(save_state(path, empty_stats));
  StateStore reloaded = load_state(path);
  std::remove(path.c_str());
  assert(reloaded.urls.at("https://old.example.com").stats.total_checks == 0);

  std::cout << "test_stats: all assertions passed\n";
  return 0;
}
