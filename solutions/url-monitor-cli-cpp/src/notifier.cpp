#include "notifier.hpp"

#include <ctime>
#include <iostream>
#include <sstream>

namespace {

std::string result_detail(const CheckResult& r) {
  std::ostringstream out;
  if (r.curl_code != 0) {
    out << "(curl: " << r.curl_error_name << ")";
  } else {
    out << "(HTTP " << r.http_status << ", " << static_cast<long>(r.total_ms) << "ms)";
  }
  return out.str();
}

// Uppercase, padded to the width of "DOWN " so URLs line up.
const char* status_column(Status s) {
  switch (s) {
    case Status::Up:
      return "UP  ";
    case Status::Down:
      return "DOWN";
    default:
      return "??? ";
  }
}

}  // namespace

std::string iso8601_now() {
  std::time_t now = std::time(nullptr);
  std::tm tm_utc{};
  gmtime_r(&now, &tm_utc);
  char buf[32];
  std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &tm_utc);
  return buf;
}

void log_info(const std::string& msg) {
  std::cout << iso8601_now() << " " << msg << std::endl;
}

void log_error(const std::string& msg) {
  std::cerr << iso8601_now() << " ERROR " << msg << std::endl;
}

void emit_transition(const std::string& url, Status /*prev*/, Status now,
                     const CheckResult& r) {
  std::cout << iso8601_now() << " " << status_column(now) << "  " << url << "  "
            << result_detail(r) << std::endl;
}

void log_check(const std::string& url, Status s, const CheckResult& r) {
  std::cout << iso8601_now() << " CHECK " << status_column(s) << " " << url << "  "
            << result_detail(r) << std::endl;
}
