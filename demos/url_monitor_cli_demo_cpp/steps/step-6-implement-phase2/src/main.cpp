#include "config.h"
#include "checker.h"
#include "monitor.h"
#include "logger.h"
#include <CLI/CLI.hpp>
#include <atomic>
#include <csignal>
#include <iostream>
#include <map>
#include <thread>

static std::atomic<bool> g_running{true};

static void signal_handler(int) {
    g_running = false;
}

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

    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);

    Logger logger(config.log_file);
    std::map<std::string, UrlState> states;
    for (const auto& url : config.urls) {
        states[url] = UrlState{};
    }

    logger.log("Monitoring " + std::to_string(config.urls.size())
        + " URL(s), interval=" + std::to_string(config.interval_seconds) + "s");

    while (g_running) {
        for (const auto& url : config.urls) {
            if (!g_running) break;

            auto result = check_url(url, config.timeout_seconds);

            logger.log(url + " status=" + std::to_string(result.status_code)
                + " elapsed=" + std::to_string(result.elapsed_ms) + "ms"
                + " success=" + (result.success ? "true" : "false"));

            auto transition = update_state(
                states[url], url, result, config.failure_threshold);

            if (transition) {
                std::string label = (transition->type == Transition::DOWN)
                    ? "DOWN" : "UP  ";
                std::string ts = format_timestamp();
                std::cout << "[" << ts << "] " << label << "  "
                          << transition->url
                          << "  (" << transition->reason << ")" << std::endl;
            }
        }

        for (int i = 0; i < config.interval_seconds && g_running; ++i) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    }

    logger.log("Shutting down.");
    return 0;
}
