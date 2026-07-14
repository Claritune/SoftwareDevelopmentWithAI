#include "stats.hpp"

#include <cstdio>
#include <sstream>

void record(UrlStats& s, const CheckResult& r, Status st) {
  ++s.total_checks;
  if (st == Status::Up) {
    ++s.up_checks;
  } else {
    ++s.down_checks;
  }

  if (r.curl_code != 0) {
    ++s.curl_error[r.curl_error_name];
  } else {
    ++s.http_status[r.http_status];
  }
}

std::string format_stats(const std::string& url, const UrlStats& s) {
  std::ostringstream out;

  double uptime = s.total_checks > 0
                      ? 100.0 * static_cast<double>(s.up_checks) /
                            static_cast<double>(s.total_checks)
                      : 0.0;
  char uptime_buf[16];
  std::snprintf(uptime_buf, sizeof(uptime_buf), "%.1f", uptime);

  out << url << "   checks=" << s.total_checks << "  up=" << s.up_checks
      << "  down=" << s.down_checks << "  uptime=" << uptime_buf << "%\n";

  out << "  HTTP  ";
  if (s.http_status.empty()) {
    out << "(none)";
  } else {
    bool first = true;
    for (const auto& [code, count] : s.http_status) {
      if (!first) out << "   ";
      out << code << ": " << count;
      first = false;
    }
  }
  out << "\n";

  out << "  curl  ";
  if (s.curl_error.empty()) {
    out << "(none)";
  } else {
    bool first = true;
    for (const auto& [name, count] : s.curl_error) {
      if (!first) out << "   ";
      out << name << ": " << count;
      first = false;
    }
  }
  out << "\n";

  return out.str();
}
