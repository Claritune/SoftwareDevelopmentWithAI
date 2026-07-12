#pragma once
#include "checker.h"
#include <optional>
#include <string>

struct UrlState {
    int consecutive_failures = 0;
    bool is_down = false;
};

struct Transition {
    enum Type { DOWN, UP };
    Type type;
    std::string url;
    std::string reason;
};

std::optional<Transition> update_state(
    UrlState& state,
    const std::string& url,
    const CheckResult& result,
    int failure_threshold);
