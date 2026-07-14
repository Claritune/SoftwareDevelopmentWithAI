#include <iostream>

#include "config.hpp"

int main(int argc, char** argv) {
  CliOptions opts = parse_args(argc, argv);
  if (opts.error) {
    std::cerr << *opts.error << "\n\n" << usage_text();
    return 2;
  }
  if (opts.help) {
    std::cout << usage_text();
    return 0;
  }

  std::string err;
  std::optional<Config> config = load_config(opts.config_path, err);
  if (!config) {
    std::cerr << "config error: " << err << "\n";
    return 1;
  }

  std::cout << "interval: " << config->check_interval_seconds << "s\n";
  for (const UrlSpec& u : config->urls) {
    std::cout << "url: " << u.url << " (timeout " << u.timeout_seconds << "s)\n";
  }
  return 0;
}
