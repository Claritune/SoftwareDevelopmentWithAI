#include "gamer/app.h"

#include <exception>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>

#include "gamer/protocol.h"

namespace gamer {

namespace {

using httplib::Request;
using httplib::Response;

const std::filesystem::path kStaticDir =
    std::filesystem::path(GAMER_SOURCE_DIR) / "src" / "gamer" / "static";

int status_for(const SessionError& e) {
  if (dynamic_cast<const GameNotFound*>(&e) || dynamic_cast<const SessionNotFound*>(&e))
    return 404;
  if (dynamic_cast<const BadToken*>(&e)) return 403;
  return 409;  // SessionFull, StaleVersion, NotYourTurn
}

void send_json(Response& res, const Json& body, int status = 200) {
  res.status = status;
  res.set_content(body.dump(), "application/json");
}

void send_error(Response& res, int status, const std::string& detail) {
  send_json(res, {{"detail", detail}}, status);
}

void send_page(Response& res, const std::string& name) {
  std::ifstream in(kStaticDir / name, std::ios::binary);
  if (!in) return send_error(res, 500, "missing page " + name);
  std::ostringstream content;
  content << in.rdbuf();
  res.set_content(content.str(), "text/html; charset=utf-8");
}

std::string token_of(const Request& req) { return req.get_header_value("X-Player-Token"); }

const std::string& param(const Request& req, const char* name) {
  return req.path_params.at(name);
}

// Runs a handler under the session lock and maps domain errors to HTTP statuses.
template <class F>
httplib::Server::Handler guarded(std::mutex& mutex, F handler) {
  return [&mutex, handler](const Request& req, Response& res) {
    std::scoped_lock lock(mutex);
    try {
      handler(req, res);
    } catch (const SessionError& e) {
      send_error(res, status_for(e), e.what());
    } catch (const IllegalMove& e) {
      send_error(res, 400, e.what());
    } catch (const protocol::InvalidRequest& e) {
      send_error(res, 422, e.what());
    }
  };
}

}  // namespace

Json build_state(const Session& session, const std::optional<Seat>& seat) {
  const Game& game = session.game();
  const auto& state = session.state();
  bool playing = seat && session.lifecycle() == Lifecycle::Playing;

  Json legal = Json::array();
  if (playing)
    for (const auto& move : game.legal_moves(state, *seat)) legal.push_back(game.move_to_public(move));

  auto taken = session.taken_seats();
  Json seats = Json::object();
  for (const auto& s : game.seats()) seats[s] = taken.contains(s);

  return {{"session_id", session.id()},
          {"game_id", game.id()},
          {"version", session.version()},
          {"lifecycle", to_string(session.lifecycle())},
          {"public_state", game.to_public(state)},
          {"status", protocol::status(game.status(state))},
          {"legal_moves", legal},
          {"seats", seats},
          {"your_seat", protocol::seat_or_null(seat)}};
}

App::App(Registry registry) : manager_(std::move(registry)) {
  if (!server_.set_mount_point("/static", kStaticDir.string()))
    throw std::runtime_error("static directory not found: " + kStaticDir.string());
  for (const auto& game : manager_.registry()) {
    auto dir = game->static_dir();
    if (!server_.set_mount_point("/games/" + game->id() + "/static", dir.string()))
      throw std::runtime_error("static directory not found: " + dir.string());
  }
  server_.set_exception_handler([](const Request&, Response& res, std::exception_ptr ep) {
    std::string detail = "internal server error";
    try {
      std::rethrow_exception(ep);
    } catch (const std::exception& e) {
      detail = e.what();
    } catch (...) {
    }
    send_error(res, 500, detail);
  });
  add_routes();
}

void App::add_routes() {
  server_.Get("/api/games", guarded(mutex_, [this](const Request&, Response& res) {
    Json games = Json::array();
    for (const auto& game : manager_.registry()) games.push_back(protocol::game_info(*game));
    send_json(res, games);
  }));

  server_.Get("/api/games/:game_id/sessions", guarded(mutex_, [this](const Request& req, Response& res) {
    Json sessions = Json::array();
    for (const auto* s : manager_.list_open(param(req, "game_id")))
      sessions.push_back(protocol::session_summary(*s));
    send_json(res, sessions);
  }));

  server_.Post("/api/games/:game_id/sessions", guarded(mutex_, [this](const Request& req, Response& res) {
    auto [session, assignment] = manager_.create(param(req, "game_id"));
    send_json(res, protocol::seat_assignment(session.id(), assignment), 201);
  }));

  server_.Post("/api/sessions/:session_id/join", guarded(mutex_, [this](const Request& req, Response& res) {
    auto& session = manager_.get(param(req, "session_id"));
    send_json(res, protocol::seat_assignment(session.id(), session.join()));
  }));

  server_.Get("/api/sessions/:session_id/state", guarded(mutex_, [this](const Request& req, Response& res) {
    auto& session = manager_.get(param(req, "session_id"));
    auto token = token_of(req);
    auto seat = session.seat_for(token);
    if (!token.empty() && !seat) throw BadToken();
    send_json(res, build_state(session, seat));
  }));

  server_.Post("/api/sessions/:session_id/moves", guarded(mutex_, [this](const Request& req, Response& res) {
    auto body = protocol::parse_move_request(req.body);  // validated first, like FastAPI
    auto& session = manager_.get(param(req, "session_id"));
    auto token = token_of(req);
    session.move(token, body.move, body.version);
    send_json(res, build_state(session, session.seat_for(token)));
  }));

  server_.Get("/", [](const Request&, Response& res) { send_page(res, "index.html"); });

  server_.Get("/games/:game_id", guarded(mutex_, [this](const Request& req, Response& res) {
    manager_.game(param(req, "game_id"));
    send_page(res, "lobby.html");
  }));

  server_.Get("/games/:game_id/sessions/:session_id",
              guarded(mutex_, [this](const Request& req, Response& res) {
                manager_.game(param(req, "game_id"));
                send_page(res, "game.html");
              }));
}

}  // namespace gamer
