#pragma once

#include <optional>
#include <string>
#include <vector>

struct UrlSpec {
  std::string url;
  int timeout_seconds = 10;
};

struct Config {
  int check_interval_seconds = 0;
  std::vector<UrlSpec> urls;
};

struct CliOptions {
  std::string config_path = "config.yaml";
  std::optional<std::string> state_file;
  bool verbose = false;
  bool stats_only = false;
  bool help = false;
  std::optional<std::string> error;
};

std::optional<Config> load_config(const std::string& path, std::string& error);
CliOptions parse_args(int argc, char** argv);
std::string usage_text();
