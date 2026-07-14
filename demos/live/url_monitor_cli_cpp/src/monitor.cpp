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

      UrlState& st = ctx.state.urls[spec.url];

      // First check sets the baseline silently; only real changes notify.
      if (st.status != Status::Unknown && st.status != now) {
        emit_transition(spec.url, st.status, now, result);
      }
      st.status = now;
      st.last_checked = iso8601_now();
    }

    save_state(ctx.state_path, ctx.state);

    // Phase 4: plain sleep; replaced by an interruptible wait in Phase 6.
    std::this_thread::sleep_for(
        std::chrono::seconds(ctx.config.check_interval_seconds));
  }
  return 0;
}
