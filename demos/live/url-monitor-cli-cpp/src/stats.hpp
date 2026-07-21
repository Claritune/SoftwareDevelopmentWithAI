#pragma once

#include <map>
#include <string>

#include "checker.hpp"

struct UrlStats {
  long total_checks = 0;
  long up_checks = 0;
  long down_checks = 0;
  std::map<long, long> http_status;        // status code → count (completed requests)
  std::map<std::string, long> curl_error;  // curl error name → count

  bool operator==(const UrlStats& o) const {
    return total_checks == o.total_checks && up_checks == o.up_checks &&
           down_checks == o.down_checks && http_status == o.http_status &&
           curl_error == o.curl_error;
  }
};

void record(UrlStats& s, const CheckResult& r, Status st);

// Renders one block per URL:
//   https://example.com   checks=120  up=118  down=2  uptime=98.3%
//     HTTP  200: 118   503: 2
//     curl  (none)
std::string format_stats(const std::string& url, const UrlStats& s);
