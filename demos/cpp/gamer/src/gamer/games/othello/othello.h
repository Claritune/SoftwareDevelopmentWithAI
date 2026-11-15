#pragma once

#include <array>
#include <optional>
#include <vector>

#include "gamer/game.h"

namespace gamer::othello {

inline const Seat kBlack = "black";
inline const Seat kWhite = "white";
inline const Seat kEmpty = "";
inline constexpr int kSize = 8;

using Board = std::array<std::array<Seat, kSize>, kSize>;

struct Move {  // 0-based, row 0 at the top
  int row = 0;
  int col = 0;

  auto operator<=>(const Move&) const = default;
};

struct OthelloState {
  Board board;
  std::optional<Seat> to_move;  // nullopt once neither side can move

  bool operator==(const OthelloState&) const = default;
};

class Othello {
 public:
  using State = OthelloState;
  using Move = othello::Move;

  std::string id() const { return "othello"; }
  std::string name() const { return "Othello"; }
  std::vector<Seat> seats() const { return {kBlack, kWhite}; }
  std::filesystem::path static_dir() const;

  State initial_state() const;
  GameStatus status(const State& state) const;
  Json to_public(const State& state) const;
  std::vector<Move> legal_moves(const State& state, const Seat& seat) const;
  State apply_move(const State& state, const Seat& seat, const Move& move) const;
  Move parse_move(const Json& raw) const;
  Json move_to_public(const Move& move) const;
};

}  // namespace gamer::othello
