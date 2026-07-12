#include "checker.h"
#include <cpr/cpr.h>

CheckResult check_url(const std::string& url, int timeout_seconds) {
    CheckResult result;
    auto response = cpr::Get(
        cpr::Url{url},
        cpr::Timeout{timeout_seconds * 1000},
        cpr::Redirect(10L));

    result.elapsed_ms = static_cast<long>(response.elapsed * 1000);

    if (response.error.code != cpr::ErrorCode::OK) {
        result.success = false;
        result.error = response.error.message;
        return result;
    }

    result.status_code = response.status_code;
    result.success = (response.status_code < 400);
    if (!result.success) {
        result.error = "HTTP " + std::to_string(response.status_code);
    }
    return result;
}
