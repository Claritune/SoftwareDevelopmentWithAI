#include "monitor.hpp"

#include <chrono>
#include <thread>

#include "notifier.hpp"

int run_monitor(MonitorContext& ctx, HttpClient& client) {
  log_info("monitoring " + std::to_string(ctx.config.urls.size()) + " url(s) every " +
           std::to_string(ctx.config.check_interval_seconds) + "s");

  while (true) {
    for (const UrlSpec& spec : ctx.config.urls) {
      CheckResult result = client.check(spec);
      Status now = classify(result);

      if (ctx.verbose) {
        log_check(spec.url, now, result);
      }

      Status prev = Status::Unknown;
      auto it = ctx.status.find(spec.url);
      if (it != ctx.status.end()) {
        prev = it->second;
      }

      // First check sets the baseline silently; only real changes notify.
      if (prev != Status::Unknown && prev != now) {
        emit_transition(spec.url, prev, now, result);
      }
      ctx.status[spec.url] = now;
    }

    // Phase 3: plain sleep; replaced by an interruptible wait in Phase 6.
    std::this_thread::sleep_for(
        std::chrono::seconds(ctx.config.check_interval_seconds));
  }
  return 0;
}
