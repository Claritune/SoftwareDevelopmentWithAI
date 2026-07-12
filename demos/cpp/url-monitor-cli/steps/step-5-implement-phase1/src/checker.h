#pragma once
#include <string>

struct CheckResult {
    int status_code = 0;
    long elapsed_ms = 0;
    bool success = false;
    std::string error;
};

CheckResult check_url(const std::string& url, int timeout_seconds);
