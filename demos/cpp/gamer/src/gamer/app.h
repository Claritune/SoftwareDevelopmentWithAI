#pragma once

#include <mutex>
#include <optional>

#include <httplib.h>

#include "gamer/game.h"
#include "gamer/games/registry.h"
#include "gamer/sessions.h"

namespace gamer {

// Session state as one player (or a watcher, with no seat) sees it.
Json build_state(const Session& session, const std::optional<Seat>& seat);

// The HTTP server: JSON API, the HTML client, and each game's static view.
class App {
 public:
  explicit App(Registry registry = default_registry());

  httplib::Server& server() { return server_; }

 private:
  void add_routes();

  SessionManager manager_;
  std::mutex mutex_;  // serialises all session access; never held during network I/O
  httplib::Server server_;
};

}  // namespace gamer
