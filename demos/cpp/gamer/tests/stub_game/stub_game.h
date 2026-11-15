#pragma once

#include <array>
#include <optional>

#include "gamer/game.h"

namespace stub {

struct StubState {
  std::array<gamer::Seat, 4> claims;  // "" or the seat that claimed the cell
  std::optional<gamer::Seat> to_move;
};

// Players take turns claiming cells 0-3. The first to hold 2 cells wins.
class StubGame {
 public:
  using State = StubState;
  using Move = int;

  std::string id() const { return "stub"; }
  std::string name() const { return "Stub"; }
  std::vector<gamer::Seat> seats() const { return {"x", "o"}; }
  std::filesystem::path static_dir() const;

  State initial_state() const;
  std::vector<Move> legal_moves(const State& state, const gamer::Seat& seat) const;
  State apply_move(const State& state, const gamer::Seat& seat, const Move& move) const;
  gamer::GameStatus status(const State& state) const;
  gamer::Json to_public(const State& state) const;
  Move parse_move(const gamer::Json& raw) const;
  gamer::Json move_to_public(const Move& move) const;
};

}  // namespace stub
