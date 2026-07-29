#pragma once

#include <string>

#include "config.hpp"

enum class Status { Unknown, Up, Down };

struct CheckResult {
  long http_status = 0;
  int curl_code = 0;            // CURLcode as int; 0 == CURLE_OK
  std::string curl_error_name;  // stable key, e.g. "operation_timedout"; empty on success
  double total_ms = 0;
};

// Up iff the request completed (curl_code == 0) with final HTTP status 200.
// Everything else — any other status, status 0, or a curl error — is Down.
Status classify(const CheckResult& r);

const char* status_name(Status s);
std::string curl_error_key(int curl_code);

class HttpClient {
 public:
  HttpClient();
  ~HttpClient();
  HttpClient(const HttpClient&) = delete;
  HttpClient& operator=(const HttpClient&) = delete;

  CheckResult check(const UrlSpec& spec);

 private:
  void* handle_ = nullptr;  // CURL*; void* keeps curl out of this header
};
