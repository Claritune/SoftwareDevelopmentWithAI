#pragma once

#include <cstdint>
#include <functional>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "gamer/game.h"

namespace gamer {

enum class Lifecycle { Waiting, Playing, Finished };

std::string to_string(Lifecycle lifecycle);

class SessionError : public std::runtime_error {
 public:
  using std::runtime_error::runtime_error;
};

struct GameNotFound : SessionError {
  GameNotFound() : SessionError("unknown game") {}
};

struct SessionNotFound : SessionError {
  SessionNotFound() : SessionError("unknown session") {}
};

struct SessionFull : SessionError {
  SessionFull() : SessionError("session is full") {}
};

struct BadToken : SessionError {
  BadToken() : SessionError("invalid or missing player token") {}
};

struct StaleVersion : SessionError {
  StaleVersion() : SessionError("board changed, refresh and try again") {}
};

struct NotYourTurn : SessionError {
  NotYourTurn() : SessionError("not your turn") {}
};

struct SeatAssignment {
  Seat seat;
  std::string token;
};

// Not thread-safe: callers serialise access (the app holds one lock per request).
class Session {
 public:
  Session(std::string id, std::shared_ptr<const Game> game);

  const std::string& id() const { return id_; }
  const Game& game() const { return *game_; }
  const std::any& state() const { return state_; }
  int version() const { return version_; }

  Lifecycle lifecycle() const;
  std::optional<Seat> seat_for(std::string_view token) const;  // empty token: none given
  std::set<Seat> taken_seats() const;

  SeatAssignment claim_seat();  // version unchanged
  SeatAssignment join();        // claims a seat and bumps the version
  void move(std::string_view token, const Json& raw_move, std::int64_t version);

 private:
  std::string id_;
  std::shared_ptr<const Game> game_;
  std::any state_;
  int version_ = 1;
  std::map<std::string, Seat, std::less<>> seat_tokens_;  // token -> seat
};

class SessionManager {
 public:
  explicit SessionManager(Registry registry);

  const Registry& registry() const { return registry_; }
  const std::shared_ptr<const Game>& game(std::string_view game_id) const;
  std::pair<Session&, SeatAssignment> create(std::string_view game_id);  // creator: first seat
  Session& get(std::string_view session_id);
  std::vector<const Session*> list_open(std::string_view game_id) const;

 private:
  Registry registry_;
  std::vector<std::unique_ptr<Session>> sessions_;  // creation order
  std::map<std::string, Session*, std::less<>> by_id_;
};

}  // namespace gamer
