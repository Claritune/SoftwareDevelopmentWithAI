#pragma once

#include <map>
#include <string>

#include "checker.hpp"
#include "config.hpp"

struct MonitorContext {
  Config config;
  std::map<std::string, Status> status;  // last known status per URL
  bool verbose = false;
};

// Runs the check loop until interrupted. Returns the process exit code.
int run_monitor(MonitorContext& ctx, HttpClient& client);
