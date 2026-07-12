#include "monitor.h"

std::optional<Transition> update_state(
    UrlState& state,
    const std::string& url,
    const CheckResult& result,
    int failure_threshold) {

    if (result.success) {
        state.consecutive_failures = 0;
        if (state.is_down) {
            state.is_down = false;
            std::string reason = "HTTP " + std::to_string(result.status_code)
                + ", " + std::to_string(result.elapsed_ms) + "ms";
            return Transition{Transition::UP, url, reason};
        }
        return std::nullopt;
    }

    state.consecutive_failures++;
    if (!state.is_down && state.consecutive_failures >= failure_threshold) {
        state.is_down = true;
        std::string reason = std::to_string(state.consecutive_failures)
            + " consecutive failures, last: " + result.error;
        return Transition{Transition::DOWN, url, reason};
    }
    return std::nullopt;
}
