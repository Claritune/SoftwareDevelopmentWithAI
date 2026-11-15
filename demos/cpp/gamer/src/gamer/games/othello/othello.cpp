#include "gamer/games/othello/othello.h"

#include <cstdint>
#include <utility>

namespace gamer::othello {

namespace {

constexpr std::array<std::pair<int, int>, 8> kDirections{
    {{-1, -1}, {-1, 0}, {-1, 1}, {0, -1}, {0, 1}, {1, -1}, {1, 0}, {1, 1}}};

const Seat& opponent(const Seat& seat) { return seat == kBlack ? kWhite : kBlack; }

bool on_board(int r, int c) { return 0 <= r && r < kSize && 0 <= c && c < kSize; }

std::vector<Move> flips(const Board& board, const Seat& seat, int row, int col) {
  if (board[row][col] != kEmpty) return {};
  const Seat& opp = opponent(seat);
  std::vector<Move> result;
  for (auto [dr, dc] : kDirections) {
    std::vector<Move> line;
    int r = row + dr, c = col + dc;
    while (on_board(r, c) && board[r][c] == opp) {
      line.push_back({r, c});
      r += dr;
      c += dc;
    }
    if (!line.empty() && on_board(r, c) && board[r][c] == seat)
      result.insert(result.end(), line.begin(), line.end());
  }
  return result;
}

std::vector<Move> moves(const Board& board, const Seat& seat) {
  std::vector<Move> result;
  for (int r = 0; r < kSize; ++r)
    for (int c = 0; c < kSize; ++c)
      if (!flips(board, seat, r, c).empty()) result.push_back({r, c});
  return result;
}

}  // namespace

std::filesystem::path Othello::static_dir() const {
  return std::filesystem::path(GAMER_SOURCE_DIR) / "src" / "gamer" / "games" / "othello" / "static";
}

OthelloState Othello::initial_state() const {
  Board board{};
  board[3][3] = board[4][4] = kWhite;
  board[3][4] = board[4][3] = kBlack;
  return {board, kBlack};
}

GameStatus Othello::status(const OthelloState& state) const {
  std::map<Seat, int> scores{{kBlack, 0}, {kWhite, 0}};
  for (const auto& row : state.board)
    for (const auto& cell : row)
      if (cell != kEmpty) ++scores[cell];
  bool finished = !state.to_move.has_value();
  std::optional<Seat> winner;
  if (finished && scores[kBlack] != scores[kWhite])
    winner = scores[kBlack] > scores[kWhite] ? kBlack : kWhite;
  return {state.to_move, finished, winner, scores};
}

Json Othello::to_public(const OthelloState& state) const { return {{"board", state.board}}; }

std::vector<Move> Othello::legal_moves(const OthelloState& state, const Seat& seat) const {
  return state.to_move == seat ? moves(state.board, seat) : std::vector<Move>{};
}

OthelloState Othello::apply_move(const OthelloState& state, const Seat& seat,
                                 const Move& move) const {
  if (state.to_move != seat) throw IllegalMove("not your turn");
  if (!on_board(move.row, move.col)) throw IllegalMove("move is off the board");
  auto flipped = flips(state.board, seat, move.row, move.col);
  if (flipped.empty()) throw IllegalMove("move must flip at least one disc");

  Board board = state.board;
  board[move.row][move.col] = seat;
  for (auto [r, c] : flipped) board[r][c] = seat;

  std::optional<Seat> to_move;
  if (!moves(board, opponent(seat)).empty())
    to_move = opponent(seat);
  else if (!moves(board, seat).empty())
    to_move = seat;  // opponent must pass
  // else: neither side can move
  return {board, to_move};
}

Move Othello::parse_move(const Json& raw) const {
  auto coord = [&](const char* key) -> std::optional<int> {
    if (!raw.is_object()) return std::nullopt;
    auto it = raw.find(key);
    if (it == raw.end() || !it->is_number_integer()) return std::nullopt;  // bools excluded
    auto v = it->get<std::int64_t>();
    if (v < 0 || v >= kSize) return std::nullopt;
    return static_cast<int>(v);
  };
  auto row = coord("row"), col = coord("col");
  if (!row || !col) throw IllegalMove("move must be {row, col} with integers 0-7");
  return {*row, *col};
}

Json Othello::move_to_public(const Move& move) const {
  return {{"row", move.row}, {"col", move.col}};
}

}  // namespace gamer::othello
