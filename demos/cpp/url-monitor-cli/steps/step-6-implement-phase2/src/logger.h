#pragma once
#include <fstream>
#include <optional>
#include <string>

std::string format_timestamp();

class Logger {
public:
    explicit Logger(const std::string& log_file_path = "");
    void log(const std::string& message);
private:
    std::optional<std::ofstream> file_;
};
