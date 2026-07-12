#include <catch2/catch_test_macros.hpp>
#include "monitor.h"

TEST_CASE("State starts healthy") {
    UrlState state;
    CHECK(state.consecutive_failures == 0);
    CHECK(state.is_down == false);
}

TEST_CASE("Successful check produces no transition") {
    UrlState state;
    CheckResult ok{200, 50, true, ""};
    auto t = update_state(state, "http://example.com", ok, 3);
    CHECK_FALSE(t.has_value());
    CHECK(state.consecutive_failures == 0);
}

TEST_CASE("Failures below threshold produce no transition") {
    UrlState state;
    CheckResult fail{503, 100, false, "HTTP 503"};
    update_state(state, "http://example.com", fail, 3);
    auto t = update_state(state, "http://example.com", fail, 3);
    CHECK_FALSE(t.has_value());
    CHECK(state.consecutive_failures == 2);
    CHECK(state.is_down == false);
}

TEST_CASE("Reaching threshold triggers DOWN") {
    UrlState state;
    CheckResult fail{0, 0, false, "Connection timeout"};
    update_state(state, "http://example.com", fail, 3);
    update_state(state, "http://example.com", fail, 3);
    auto t = update_state(state, "http://example.com", fail, 3);
    REQUIRE(t.has_value());
    CHECK(t->type == Transition::DOWN);
    CHECK(t->url == "http://example.com");
    CHECK(state.is_down == true);
}

TEST_CASE("Success after DOWN triggers UP") {
    UrlState state;
    state.is_down = true;
    state.consecutive_failures = 3;
    CheckResult ok{200, 42, true, ""};
    auto t = update_state(state, "http://example.com", ok, 3);
    REQUIRE(t.has_value());
    CHECK(t->type == Transition::UP);
    CHECK(state.is_down == false);
    CHECK(state.consecutive_failures == 0);
}

TEST_CASE("Additional failures after DOWN do not re-trigger") {
    UrlState state;
    state.is_down = true;
    state.consecutive_failures = 3;
    CheckResult fail{500, 100, false, "HTTP 500"};
    auto t = update_state(state, "http://example.com", fail, 3);
    CHECK_FALSE(t.has_value());
    CHECK(state.consecutive_failures == 4);
}
