#include "config.h"
#include "checker.h"
#include "monitor.h"
#include <CLI/CLI.hpp>
#include <iostream>
#include <map>

int main(int argc, char** argv) {
    Config config;

    CLI::App app{"URL Monitor — checks URLs for uptime"};
    app.add_option("urls", config.urls, "URLs to monitor")
        ->required()
        ->expected(-1);
    app.add_option("--failure-threshold", config.failure_threshold,
        "Consecutive failures before marking DOWN")
        ->default_val(3);
    app.add_option("--interval", config.interval_seconds,
        "Seconds between check rounds")
        ->default_val(30);
    app.add_option("--timeout", config.timeout_seconds,
        "HTTP request timeout in seconds")
        ->default_val(10);
    app.add_option("--log-file", config.log_file,
        "Append check logs to this file");

    CLI11_PARSE(app, argc, argv);

    std::map<std::string, UrlState> states;
    for (const auto& url : config.urls) {
        states[url] = UrlState{};
    }

    for (const auto& url : config.urls) {
        auto result = check_url(url, config.timeout_seconds);

        std::cerr << "[check] " << url
                  << " status=" << result.status_code
                  << " elapsed=" << result.elapsed_ms << "ms"
                  << " success=" << (result.success ? "true" : "false")
                  << std::endl;

        auto transition = update_state(
            states[url], url, result, config.failure_threshold);

        if (transition) {
            std::string label = (transition->type == Transition::DOWN)
                ? "DOWN" : "UP  ";
            std::cout << "[" << label << "] " << transition->url
                      << "  (" << transition->reason << ")" << std::endl;
        }
    }

    return 0;
}
