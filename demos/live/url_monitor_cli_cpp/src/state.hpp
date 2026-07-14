#pragma once

#include <map>
#include <string>

#include "checker.hpp"
#include "config.hpp"

struct UrlState {
  Status status = Status::Unknown;
  std::string last_checked;  // ISO 8601 UTC, empty if never checked
};

struct StateStore {
  int version = 1;
  std::map<std::string, UrlState> urls;
};

// Missing file → empty store (silent). Unparseable file → empty store (warning).
StateStore load_state(const std::string& path);

// Atomic: writes to "<path>.tmp" then renames over path. False on I/O failure.
bool save_state(const std::string& path, const StateStore& store);

// New config URLs are added as Unknown; URLs no longer in config are dropped.
void reconcile(StateStore& store, const Config& config);

// "config.yaml" → "config.state.json"; extensionless paths get ".state.json".
std::string derive_state_path(const std::string& config_path);
