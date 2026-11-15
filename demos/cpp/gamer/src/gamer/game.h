#pragma once

#include <any>
#include <concepts>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <nlohmann/json.hpp>

namespace gamer {

using Seat = std::string;
using Json = nlohmann::json;

// The move is malformed or not allowed by the game's rules.
class IllegalMove : public std::runtime_error {
 public:
  using std::runtime_error::runtime_error;
};

struct GameStatus {
  std::optional<Seat> to_move;
  bool finished = false;
  std::optional<Seat> winner;
  std::map<Seat, int> scores;

  bool operator==(const GameStatus&) const = default;
};

// What a game module provides: typed rules with its own State and Move types.
template <class G>
concept GameRules = requires(const G g, const typename G::State state,
                             const typename G::Move move, const Seat seat, const Json raw) {
  { g.id() } -> std::convertible_to<std::string>;
  { g.name() } -> std::convertible_to<std::string>;
  { g.seats() } -> std::convertible_to<std::vector<Seat>>;
  { g.static_dir() } -> std::convertible_to<std::filesystem::path>;  // must contain view.js
  { g.initial_state() } -> std::same_as<typename G::State>;
  { g.legal_moves(state, seat) } -> std::same_as<std::vector<typename G::Move>>;
  { g.apply_move(state, seat, move) } -> std::same_as<typename G::State>;  // throws IllegalMove
  { g.status(state) } -> std::same_as<GameStatus>;
  { g.to_public(state) } -> std::same_as<Json>;
  { g.parse_move(raw) } -> std::same_as<typename G::Move>;  // throws IllegalMove
  { g.move_to_public(move) } -> std::same_as<Json>;
};

// The type-erased interface the server core talks to. States and moves are opaque.
class Game {
 public:
  virtual ~Game() = default;

  virtual std::string id() const = 0;
  virtual std::string name() const = 0;
  virtual std::vector<Seat> seats() const = 0;
  virtual std::filesystem::path static_dir() const = 0;  // served at /games/{id}/static

  virtual std::any initial_state() const = 0;
  virtual std::vector<std::any> legal_moves(const std::any& state, const Seat& seat) const = 0;
  virtual std::any apply_move(const std::any& state, const Seat& seat,
                              const std::any& move) const = 0;
  virtual GameStatus status(const std::any& state) const = 0;
  virtual Json to_public(const std::any& state) const = 0;
  virtual std::any parse_move(const Json& raw) const = 0;
  virtual Json move_to_public(const std::any& move) const = 0;
};

template <GameRules G>
class GameAdapter final : public Game {
  using S = typename G::State;
  using M = typename G::Move;

 public:
  explicit GameAdapter(G rules = {}) : rules_(std::move(rules)) {}

  std::string id() const override { return rules_.id(); }
  std::string name() const override { return rules_.name(); }
  std::vector<Seat> seats() const override { return rules_.seats(); }
  std::filesystem::path static_dir() const override { return rules_.static_dir(); }

  std::any initial_state() const override { return rules_.initial_state(); }

  std::vector<std::any> legal_moves(const std::any& state, const Seat& seat) const override {
    std::vector<std::any> moves;
    for (auto& m : rules_.legal_moves(std::any_cast<const S&>(state), seat)) moves.emplace_back(m);
    return moves;
  }

  std::any apply_move(const std::any& state, const Seat& seat,
                      const std::any& move) const override {
    return rules_.apply_move(std::any_cast<const S&>(state), seat, std::any_cast<const M&>(move));
  }

  GameStatus status(const std::any& state) const override {
    return rules_.status(std::any_cast<const S&>(state));
  }

  Json to_public(const std::any& state) const override {
    return rules_.to_public(std::any_cast<const S&>(state));
  }

  std::any parse_move(const Json& raw) const override { return rules_.parse_move(raw); }

  Json move_to_public(const std::any& move) const override {
    return rules_.move_to_public(std::any_cast<const M&>(move));
  }

 private:
  G rules_;
};

template <GameRules G>
std::shared_ptr<const Game> make_game(G rules = {}) {
  return std::make_shared<const GameAdapter<G>>(std::move(rules));
}

using Registry = std::vector<std::shared_ptr<const Game>>;  // directory order

}  // namespace gamer
