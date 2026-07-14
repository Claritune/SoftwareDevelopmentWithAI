#include "state.hpp"

#include <nlohmann/json.hpp>

#include <cstdio>
#include <fstream>

#include "notifier.hpp"

using nlohmann::json;

namespace {

Status status_from_string(const std::string& s) {
  if (s == "up") return Status::Up;
  if (s == "down") return Status::Down;
  return Status::Unknown;
}

}  // namespace

StateStore load_state(const std::string& path) {
  StateStore store;

  std::ifstream in(path);
  if (!in) {
    return store;  // first run: no state file yet
  }

  json root;
  try {
    root = json::parse(in);
  } catch (const json::parse_error& e) {
    log_error("state file " + path + " is not valid JSON, starting fresh: " + e.what());
    return store;
  }

  store.version = root.value("version", 1);
  if (root.contains("urls") && root["urls"].is_object()) {
    for (const auto& [url, entry] : root["urls"].items()) {
      UrlState st;
      st.status = status_from_string(entry.value("status", "unknown"));
      st.last_checked = entry.value("last_checked", "");
      store.urls[url] = std::move(st);
    }
  }
  return store;
}

bool save_state(const std::string& path, const StateStore& store) {
  json urls = json::object();
  for (const auto& [url, st] : store.urls) {
    urls[url] = {
        {"status", status_name(st.status)},
        {"last_checked", st.last_checked},
    };
  }
  json root = {{"version", store.version}, {"urls", urls}};

  const std::string tmp_path = path + ".tmp";
  {
    std::ofstream out(tmp_path, std::ios::trunc);
    if (!out) {
      log_error("cannot write state file: " + tmp_path);
      return false;
    }
    out << root.dump(2) << "\n";
    if (!out) {
      log_error("failed writing state file: " + tmp_path);
      return false;
    }
  }

  if (std::rename(tmp_path.c_str(), path.c_str()) != 0) {
    log_error("cannot rename " + tmp_path + " to " + path);
    return false;
  }
  return true;
}

void reconcile(StateStore& store, const Config& config) {
  std::map<std::string, UrlState> reconciled;
  for (const UrlSpec& spec : config.urls) {
    auto it = store.urls.find(spec.url);
    reconciled[spec.url] = (it != store.urls.end()) ? it->second : UrlState{};
  }
  store.urls = std::move(reconciled);
}

std::string derive_state_path(const std::string& config_path) {
  const std::size_t slash = config_path.find_last_of('/');
  const std::size_t dot = config_path.find_last_of('.');
  if (dot == std::string::npos || (slash != std::string::npos && dot < slash)) {
    return config_path + ".state.json";
  }
  return config_path.substr(0, dot) + ".state.json";
}
