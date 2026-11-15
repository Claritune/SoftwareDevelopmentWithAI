#include "stub_game/stub_game.h"

#include <algorithm>

namespace stub {

std::filesystem::path StubGame::static_dir() const {
  return std::filesystem::path(GAMER_SOURCE_DIR) / "tests" / "stub_game" / "static";
}

StubState StubGame::initial_state() const { return {{}, "x"}; }

std::vector<int> StubGame::legal_moves(const StubState& state, const gamer::Seat& seat) const {
  std::vector<int> moves;
  if (state.to_move != seat) return moves;
  for (int i = 0; i < 4; ++i)
    if (state.claims[i].empty()) moves.push_back(i);
  return moves;
}

StubState StubGame::apply_move(const StubState& state, const gamer::Seat& seat,
                               const int& move) const {
  auto legal = legal_moves(state, seat);
  if (std::find(legal.begin(), legal.end(), move) == legal.end())
    throw gamer::IllegalMove("cell not available");
  StubState next = state;
  next.claims[move] = seat;
  if (std::count(next.claims.begin(), next.claims.end(), seat) >= 2)
    next.to_move.reset();
  else
    next.to_move = seat == "x" ? "o" : "x";
  return next;
}

gamer::GameStatus StubGame::status(const StubState& state) const {
  gamer::GameStatus status{state.to_move, !state.to_move.has_value(), std::nullopt, {}};
  for (const auto& s : seats()) {
    int n = static_cast<int>(std::count(state.claims.begin(), state.claims.end(), s));
    status.scores[s] = n;
    if (n >= 2 && !status.winner) status.winner = s;
  }
  return status;
}

gamer::Json StubGame::to_public(const StubState& state) const { return {{"claims", state.claims}}; }

int StubGame::parse_move(const gamer::Json& raw) const {
  auto cell = raw.is_object() ? raw.find("cell") : raw.end();
  if (cell == raw.end() || !cell->is_number_integer() || cell->get<std::int64_t>() < 0 ||
      cell->get<std::int64_t>() >= 4)
    throw gamer::IllegalMove("cell must be 0-3");
  return cell->get<int>();
}

gamer::Json StubGame::move_to_public(const int& move) const { return {{"cell", move}}; }

}  // namespace stub
