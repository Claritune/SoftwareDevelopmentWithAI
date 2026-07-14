#pragma once

#include <string>

#include "checker.hpp"
#include "config.hpp"
#include "state.hpp"

struct MonitorContext {
  Config config;
  StateStore state;        // last known status per URL, persisted each cycle
  std::string state_path;  // JSON sidecar location
  bool verbose = false;
};

// Runs the check loop until interrupted. Returns the process exit code.
int run_monitor(MonitorContext& ctx, HttpClient& client);
