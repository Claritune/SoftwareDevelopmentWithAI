#include "checker.hpp"

#include <curl/curl.h>

namespace {

size_t discard_body(char*, size_t size, size_t nmemb, void*) {
  return size * nmemb;
}

}  // namespace

Status classify(const CheckResult& r) {
  return (r.curl_code == 0 && r.http_status == 200) ? Status::Up : Status::Down;
}

const char* status_name(Status s) {
  switch (s) {
    case Status::Up:
      return "up";
    case Status::Down:
      return "down";
    default:
      return "unknown";
  }
}

std::string curl_error_key(int curl_code) {
  switch (curl_code) {
    case CURLE_UNSUPPORTED_PROTOCOL:
      return "unsupported_protocol";
    case CURLE_URL_MALFORMAT:
      return "url_malformat";
    case CURLE_COULDNT_RESOLVE_HOST:
      return "couldnt_resolve_host";
    case CURLE_COULDNT_CONNECT:
      return "couldnt_connect";
    case CURLE_OPERATION_TIMEDOUT:
      return "operation_timedout";
    case CURLE_SSL_CONNECT_ERROR:
      return "ssl_connect_error";
    case CURLE_PEER_FAILED_VERIFICATION:
      return "peer_failed_verification";
    case CURLE_TOO_MANY_REDIRECTS:
      return "too_many_redirects";
    case CURLE_SEND_ERROR:
      return "send_error";
    case CURLE_RECV_ERROR:
      return "recv_error";
    case CURLE_GOT_NOTHING:
      return "got_nothing";
    default:
      return "curl_error_" + std::to_string(curl_code);
  }
}

HttpClient::HttpClient() {
  curl_global_init(CURL_GLOBAL_DEFAULT);
  handle_ = curl_easy_init();
}

HttpClient::~HttpClient() {
  if (handle_ != nullptr) {
    curl_easy_cleanup(static_cast<CURL*>(handle_));
  }
  curl_global_cleanup();
}

CheckResult HttpClient::check(const UrlSpec& spec) {
  CheckResult result;
  CURL* curl = static_cast<CURL*>(handle_);

  curl_easy_reset(curl);
  curl_easy_setopt(curl, CURLOPT_URL, spec.url.c_str());
  curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
  curl_easy_setopt(curl, CURLOPT_MAXREDIRS, 5L);
  curl_easy_setopt(curl, CURLOPT_TIMEOUT, static_cast<long>(spec.timeout_seconds));
  curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);
  curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, discard_body);
  curl_easy_setopt(curl, CURLOPT_USERAGENT, "urlmon/1.0");

  CURLcode code = curl_easy_perform(curl);

  double total_seconds = 0;
  curl_easy_getinfo(curl, CURLINFO_TOTAL_TIME, &total_seconds);
  result.total_ms = total_seconds * 1000.0;

  if (code != CURLE_OK) {
    result.curl_code = static_cast<int>(code);
    result.curl_error_name = curl_error_key(result.curl_code);
    return result;
  }

  curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &result.http_status);
  return result;
}
