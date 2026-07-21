#include "monitor.hpp"

#include <atomic>
#include <chrono>
#include <csignal>
#include <iostream>
#include <thread>

#include "notifier.hpp"
#include "stats.hpp"

namespace {

std::atomic<bool> g_shutdown{false};

// Async-signal-safe: only sets the atomic flag. The interval wait polls it
// in short slices, so no condition_variable notify is needed from here.
extern "C" void handle_signal(int) { g_shutdown.store(true); }

// Sleeps up to `seconds`, returning early (true) if shutdown was requested.
bool interruptible_wait(int seconds) {
  using namespace std::chrono;
  const auto deadline = steady_clock::now() + std::chrono::seconds(seconds);
  while (steady_clock::now() < deadline) {
    if (g_shutdown.load()) return true;
    std::this_thread::sleep_for(milliseconds(200));
  }
  return g_shutdown.load();
}

}  // namespace

bool shutdown_requested() { return g_shutdown.load(); }

int run_monitor(MonitorContext& ctx, HttpClient& client) {
  std::signal(SIGINT, handle_signal);
  std::signal(SIGTERM, handle_signal);

  log_info("monitoring " + std::to_string(ctx.config.urls.size()) + " url(s) every " +
           std::to_string(ctx.config.check_interval_seconds) + "s");

  while (!g_shutdown.load()) {
    for (const UrlSpec& spec : ctx.config.urls) {
      if (g_shutdown.load()) break;  // finish the in-flight check, skip the rest

      CheckResult result = client.check(spec);
      Status now = classify(result);

      if (ctx.verbose) {
        log_check(spec.url, now, result);
      }

      UrlState& st = ctx.state.urls[spec.url];
      record(st.stats, result, now);

      // First check sets the baseline silently; only real changes notify.
      if (st.status != Status::Unknown && st.status != now) {
        emit_transition(spec.url, st.status, now, result);
      }
      st.status = now;
      st.last_checked = iso8601_now();
    }

    save_state(ctx.state_path, ctx.state);

    if (interruptible_wait(ctx.config.check_interval_seconds)) {
      break;
    }
  }

  log_info("shutting down");
  save_state(ctx.state_path, ctx.state);
  for (const auto& [url, st] : ctx.state.urls) {
    std::cout << format_stats(url, st.stats);
  }
  return 0;
}
