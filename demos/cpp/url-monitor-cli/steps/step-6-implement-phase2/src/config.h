#pragma once
#include <string>
#include <vector>

struct Config {
    std::vector<std::string> urls;
    int failure_threshold = 3;
    int interval_seconds = 30;
    int timeout_seconds = 10;
    std::string log_file;
};
