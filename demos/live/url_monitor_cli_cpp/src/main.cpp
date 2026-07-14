#include <iostream>

#include "checker.hpp"
#include "config.hpp"
#include "monitor.hpp"
#include "state.hpp"
#include "stats.hpp"

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

  const std::string state_path =
      opts.state_file ? *opts.state_file : derive_state_path(opts.config_path);

  if (opts.stats_only) {
    StateStore store = load_state(state_path);
    if (store.urls.empty()) {
      std::cout << "no statistics recorded yet (state file: " << state_path << ")\n";
      return 0;
    }
    for (const auto& [url, st] : store.urls) {
      std::cout << format_stats(url, st.stats);
    }
    return 0;
  }

  MonitorContext ctx;
  ctx.config = std::move(*config);
  ctx.state = load_state(state_path);
  ctx.state_path = state_path;
  ctx.verbose = opts.verbose;
  reconcile(ctx.state, ctx.config);

  HttpClient client;
  return run_monitor(ctx, client);
}
