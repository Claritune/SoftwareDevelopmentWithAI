#include "logger.h"
#include <chrono>
#include <iomanip>
#include <iostream>
#include <sstream>

std::string format_timestamp() {
    auto now = std::chrono::system_clock::now();
    auto time = std::chrono::system_clock::to_time_t(now);
    std::ostringstream oss;
    oss << std::put_time(std::gmtime(&time), "%Y-%m-%dT%H:%M:%SZ");
    return oss.str();
}

Logger::Logger(const std::string& log_file_path) {
    if (!log_file_path.empty()) {
        file_.emplace(log_file_path, std::ios::app);
    }
}

void Logger::log(const std::string& message) {
    std::string timestamped = "[" + format_timestamp() + "] " + message;
    std::cerr << timestamped << std::endl;
    if (file_) {
        *file_ << timestamped << std::endl;
    }
}
