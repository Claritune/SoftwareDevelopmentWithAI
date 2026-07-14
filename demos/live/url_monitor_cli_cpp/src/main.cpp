#include <iostream>

#include "checker.hpp"
#include "config.hpp"
#include "monitor.hpp"

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

  HttpClient client;
  MonitorContext ctx;
  ctx.config = std::move(*config);
  ctx.verbose = opts.verbose;
  return run_monitor(ctx, client);
}
