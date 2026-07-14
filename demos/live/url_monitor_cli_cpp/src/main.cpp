#include <iostream>

#include "checker.hpp"
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

  // Phase 2: one-shot check pass over all configured URLs.
  HttpClient client;
  for (const UrlSpec& u : config->urls) {
    CheckResult r = client.check(u);
    Status s = classify(r);
    std::cout << u.url << "  " << (s == Status::Up ? "UP" : "DOWN") << "  ";
    if (r.curl_code != 0) {
      std::cout << "(curl: " << r.curl_error_name << ")";
    } else {
      std::cout << "(HTTP " << r.http_status << ", " << static_cast<long>(r.total_ms)
                << "ms)";
    }
    std::cout << "\n";
  }
  return 0;
}
