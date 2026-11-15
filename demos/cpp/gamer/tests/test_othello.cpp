#include <set>
#include <string>
#include <vector>

#include <gtest/gtest.h>

#include "gamer/games/othello/othello.h"

using namespace gamer;
using namespace gamer::othello;

namespace {

const Othello kOthello;

// rows: 8 strings of 8 chars, 'B' black / 'W' white / '.' empty.
OthelloState state_from(const std::vector<std::string>& rows,
                        std::optional<Seat> to_move = kBlack) {
  OthelloState state{{}, std::move(to_move)};
  for (int r = 0; r < kSize; ++r)
    for (int c = 0; c < kSize; ++c) {
      char ch = rows.at(r).at(c);
      state.board[r][c] = ch == 'B' ? kBlack : ch == 'W' ? kWhite : kEmpty;
    }
  return state;
}

const std::string kEmptyRow(kSize, '.');

std::vector<std::string> with_empty_rows(std::vector<std::string> rows) {
  rows.resize(kSize, kEmptyRow);
  return rows;
}

int count(const Board& board, const Seat& seat) {
  int n = 0;
  for (const auto& row : board)
    for (const auto& cell : row) n += cell == seat;
  return n;
}

std::map<Seat, int> scores(int black, int white) { return {{kBlack, black}, {kWhite, white}}; }

}  // namespace

TEST(Othello, InitialStateLayout) {
  auto state = kOthello.initial_state();
  EXPECT_EQ(state.board[3][3], kWhite);
  EXPECT_EQ(state.board[4][4], kWhite);
  EXPECT_EQ(state.board[3][4], kBlack);
  EXPECT_EQ(state.board[4][3], kBlack);
  EXPECT_EQ(count(state.board, kEmpty), 60);
  EXPECT_EQ(state.to_move, "black");
}

TEST(Othello, InitialStatus) {
  auto status = kOthello.status(kOthello.initial_state());
  EXPECT_EQ(status.scores, scores(2, 2));
  EXPECT_FALSE(status.finished);
  EXPECT_EQ(status.winner, std::nullopt);
}

TEST(Othello, ToPublicIs8x8Lists) {
  auto board = kOthello.to_public(kOthello.initial_state())["board"];
  ASSERT_TRUE(board.is_array());
  ASSERT_EQ(board.size(), 8u);
  for (const auto& row : board) {
    ASSERT_TRUE(row.is_array());
    EXPECT_EQ(row.size(), 8u);
  }
  EXPECT_EQ(board[3][3], "white");
  EXPECT_EQ(board[0][0], "");
}

TEST(Othello, OpeningLegalMoves) {
  auto init = kOthello.initial_state();
  auto moves = kOthello.legal_moves(init, kBlack);
  EXPECT_EQ(std::set<Move>(moves.begin(), moves.end()),
            (std::set<Move>{{2, 3}, {3, 2}, {4, 5}, {5, 4}}));
  EXPECT_TRUE(kOthello.legal_moves(init, kWhite).empty());
}

TEST(Othello, OpeningMoveFlipsAndPassesTurn) {
  auto after = kOthello.apply_move(kOthello.initial_state(), kBlack, {2, 3});
  EXPECT_EQ(after.board[2][3], kBlack);
  EXPECT_EQ(after.board[3][3], kBlack);
  EXPECT_EQ(kOthello.status(after).scores, scores(4, 1));
  EXPECT_EQ(after.to_move, kWhite);
}

TEST(Othello, FlipsInAllEightDirections) {
  auto state = state_from({
      "........",
      "........",
      "..B.B.B.",
      "...WWW..",
      "..BW.WB.",
      "...WWW..",
      "..B.B.B.",
      "........",
  });
  auto after = kOthello.apply_move(state, kBlack, {4, 4});
  EXPECT_EQ(after.board[4][4], kBlack);
  EXPECT_EQ(count(after.board, kWhite), 0);
  auto status = kOthello.status(after);
  EXPECT_EQ(status.scores, scores(17, 0));
  // Neither side can move, but the board isn't full: the game ends early.
  EXPECT_TRUE(status.finished);
  EXPECT_EQ(status.winner, kBlack);
}

TEST(Othello, MultiDiscFlip) {
  auto after = kOthello.apply_move(state_from(with_empty_rows({"BWW....."})), kBlack, {0, 3});
  for (int c = 0; c < 4; ++c) EXPECT_EQ(after.board[0][c], kBlack) << c;
}

TEST(Othello, OccupiedSquareIsIllegal) {
  EXPECT_THROW(kOthello.apply_move(kOthello.initial_state(), kBlack, {3, 3}), IllegalMove);
}

TEST(Othello, MoveThatFlipsNothingIsIllegal) {
  EXPECT_THROW(kOthello.apply_move(kOthello.initial_state(), kBlack, {0, 0}), IllegalMove);
}

TEST(Othello, BrokenRunDoesNotFlip) {
  auto state = state_from(with_empty_rows({"BW.W...."}));
  EXPECT_THROW(kOthello.apply_move(state, kBlack, {0, 4}), IllegalMove);
}

TEST(Othello, WrongSeatIsIllegal) {
  EXPECT_THROW(kOthello.apply_move(kOthello.initial_state(), kWhite, {2, 4}), IllegalMove);
}

TEST(Othello, OffBoardMoveIsIllegal) {
  EXPECT_THROW(kOthello.apply_move(kOthello.initial_state(), kBlack, {8, 0}), IllegalMove);
}

class OthelloParseMoveRejects : public ::testing::TestWithParam<const char*> {};

TEST_P(OthelloParseMoveRejects, BadInput) {
  EXPECT_THROW(kOthello.parse_move(Json::parse(GetParam())), IllegalMove);
}

INSTANTIATE_TEST_SUITE_P(Othello, OthelloParseMoveRejects,
                         ::testing::Values(R"({"row": 8, "col": 0})", R"({"row": -1, "col": 0})",
                                           R"({"row": "a", "col": 1})", R"({"row": true, "col": 1})",
                                           R"({"row": 1.0, "col": 1})", R"({})", R"([2, 3])"));

TEST(Othello, ParseMoveAcceptsValidInput) {
  EXPECT_EQ(kOthello.parse_move({{"row", 2}, {"col", 3}}), (Move{2, 3}));
  EXPECT_EQ(kOthello.move_to_public({2, 3}), (Json{{"row", 2}, {"col", 3}}));
}

TEST(Othello, ForcedPassKeepsTurn) {
  std::vector<std::string> rows(kSize, kEmptyRow);
  rows[0] = rows[7] = "BW......";
  auto after = kOthello.apply_move(state_from(rows), kBlack, {0, 2});
  EXPECT_TRUE(kOthello.legal_moves({after.board, kWhite}, kWhite).empty());
  EXPECT_EQ(after.to_move, kBlack);
}

TEST(Othello, BoardFilledFinish) {
  std::vector<std::string> rows(7, "BBBBBBBB");
  rows.push_back("BBBBBBW.");
  auto after = kOthello.apply_move(state_from(rows), kBlack, {7, 7});
  EXPECT_EQ(after.to_move, std::nullopt);
  auto status = kOthello.status(after);
  EXPECT_TRUE(status.finished);
  EXPECT_EQ(status.winner, kBlack);
  EXPECT_EQ(status.scores, scores(64, 0));
}

TEST(Othello, Draw) {
  auto status = kOthello.status(state_from(with_empty_rows({"BBWW...."}), std::nullopt));
  EXPECT_TRUE(status.finished);
  EXPECT_EQ(status.winner, std::nullopt);
  EXPECT_EQ(status.scores, scores(2, 2));
}

TEST(Othello, SatisfiesGameRules) {
  static_assert(GameRules<Othello>);
  auto game = make_game(Othello{});
  EXPECT_EQ(game->id(), "othello");
  EXPECT_EQ(game->seats(), (std::vector<Seat>{kBlack, kWhite}));
  EXPECT_TRUE(std::filesystem::exists(game->static_dir() / "view.js"));
}
