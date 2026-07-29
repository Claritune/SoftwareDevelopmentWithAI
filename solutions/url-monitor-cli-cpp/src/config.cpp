#include "config.hpp"

#include <yaml-cpp/yaml.h>

#include <sstream>

std::optional<Config> load_config(const std::string& path, std::string& error) {
  YAML::Node root;
  try {
    root = YAML::LoadFile(path);
  } catch (const YAML::BadFile&) {
    error = "cannot open config file: " + path;
    return std::nullopt;
  } catch (const YAML::Exception& e) {
    error = "YAML parse error in " + path + ": " + e.what();
    return std::nullopt;
  }

  Config config;

  const YAML::Node interval = root["check_interval_seconds"];
  if (!interval || !interval.IsScalar()) {
    error = "missing required integer field: check_interval_seconds";
    return std::nullopt;
  }
  try {
    config.check_interval_seconds = interval.as<int>();
  } catch (const YAML::Exception&) {
    error = "check_interval_seconds must be an integer";
    return std::nullopt;
  }
  if (config.check_interval_seconds < 5) {
    error = "check_interval_seconds must be at least 5 (got " +
            std::to_string(config.check_interval_seconds) + ")";
    return std::nullopt;
  }

  const YAML::Node urls = root["urls"];
  if (!urls || !urls.IsSequence() || urls.size() == 0) {
    error = "urls must be a non-empty list";
    return std::nullopt;
  }

  for (std::size_t i = 0; i < urls.size(); ++i) {
    const YAML::Node& entry = urls[i];
    UrlSpec spec;

    const YAML::Node url = entry["url"];
    if (!url || !url.IsScalar() || url.as<std::string>().empty()) {
      error = "urls[" + std::to_string(i) + "]: missing required field: url";
      return std::nullopt;
    }
    spec.url = url.as<std::string>();

    if (const YAML::Node timeout = entry["timeout_seconds"]) {
      try {
        spec.timeout_seconds = timeout.as<int>();
      } catch (const YAML::Exception&) {
        error = "urls[" + std::to_string(i) + "]: timeout_seconds must be an integer";
        return std::nullopt;
      }
      if (spec.timeout_seconds < 1) {
        error = "urls[" + std::to_string(i) + "]: timeout_seconds must be at least 1";
        return std::nullopt;
      }
    }

    config.urls.push_back(std::move(spec));
  }

  return config;
}

CliOptions parse_args(int argc, char** argv) {
  CliOptions opts;
  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    if (arg == "--help" || arg == "-h") {
      opts.help = true;
    } else if (arg == "--verbose") {
      opts.verbose = true;
    } else if (arg == "--stats") {
      opts.stats_only = true;
    } else if (arg == "--config") {
      if (i + 1 >= argc) {
        opts.error = "--config requires a path argument";
        return opts;
      }
      opts.config_path = argv[++i];
    } else if (arg == "--state-file") {
      if (i + 1 >= argc) {
        opts.error = "--state-file requires a path argument";
        return opts;
      }
      opts.state_file = argv[++i];
    } else {
      opts.error = "unknown option: " + arg;
      return opts;
    }
  }
  return opts;
}

std::string usage_text() {
  std::ostringstream out;
  out << "urlmon - URL uptime monitor (up iff final HTTP status is 200)\n"
      << "\n"
      << "Usage: urlmon [options]\n"
      << "\n"
      << "Options:\n"
      << "  --config <path>      Path to YAML config file (default: config.yaml)\n"
      << "  --state-file <path>  Path to JSON state file\n"
      << "                       (default: config path with extension replaced by .state.json)\n"
      << "  --verbose            Log every check result, not just transitions\n"
      << "  --stats              Print accumulated per-URL statistics and exit\n"
      << "  --help               Show this help text\n";
  return out.str();
}
