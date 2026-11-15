#include "test_server.h"

#include <stdexcept>

namespace {

TestServer::Response to_response(const httplib::Result& res) {
  if (!res) throw std::runtime_error("request failed: " + httplib::to_string(res.error()));
  return {res->status, gamer::Json::parse(res->body, nullptr, false),
          res->get_header_value("Content-Type")};
}

httplib::Headers headers_for(const std::string& token) {
  if (token.empty()) return {};
  return {{"X-Player-Token", token}};
}

}  // namespace

TestServer::TestServer(gamer::Registry registry) : app_(std::move(registry)) {
  port_ = app_.server().bind_to_any_port("127.0.0.1");
  if (port_ < 0) throw std::runtime_error("could not bind test server");
  thread_ = std::thread([this] { app_.server().listen_after_bind(); });
  app_.server().wait_until_ready();
}

TestServer::~TestServer() {
  app_.server().stop();
  thread_.join();
}

TestServer::Response TestServer::get(const std::string& path, const std::string& token) {
  httplib::Client client("127.0.0.1", port_);
  return to_response(client.Get(path, headers_for(token)));
}

TestServer::Response TestServer::post(const std::string& path, const gamer::Json& body,
                                      const std::string& token) {
  httplib::Client client("127.0.0.1", port_);
  return to_response(client.Post(path, headers_for(token), body.is_null() ? "" : body.dump(),
                                 "application/json"));
}

Match start_match(TestServer& server) {
  auto a = server.post("/api/games/othello/sessions").body;
  auto sid = a["session_id"].get<std::string>();
  auto b = server.post("/api/sessions/" + sid + "/join").body;
  return {sid, a["token"].get<std::string>(), b["token"].get<std::string>()};
}

gamer::Json move_body(const gamer::Json& move, std::int64_t version) {
  return {{"move", move}, {"version", version}};
}
