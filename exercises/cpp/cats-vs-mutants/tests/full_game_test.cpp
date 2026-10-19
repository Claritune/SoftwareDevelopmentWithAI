#include <gtest/gtest.h>

#include <vector>

#include "test_helpers.hpp"
#include "waves.hpp"

using namespace cvm;
using namespace cvm::test;

namespace {

struct Move {
    int tick;  // place after the counter reaches this tick
    CatType type;
    int lane;
    int col;
};

// The same moves as scripts/demo.txt: a full winning game.
const std::vector<Move> kWinningGame = {
    {0, CatType::Rich, 2, 0},       {1, CatType::Rich, 1, 0},       {2, CatType::Rich, 3, 0},
    {81, CatType::Rich, 0, 0},      {100, CatType::Rich, 4, 0},     {162, CatType::Hissing, 2, 1},
    {241, CatType::Hissing, 0, 1},  {300, CatType::Hissing, 4, 1},  {322, CatType::Hissing, 1, 1},
    {401, CatType::Hissing, 3, 1},  {480, CatType::Hissing, 2, 2},  {500, CatType::Hissing, 1, 2},
    {561, CatType::Hissing, 3, 2},  {640, CatType::Hissing, 0, 2},  {660, CatType::Hissing, 4, 2},
    {790, CatType::Sleepy, 2, 6},   {801, CatType::Laser, 2, 3},    {882, CatType::Laser, 3, 3},
    {930, CatType::Sleepy, 3, 6},   {1010, CatType::Sleepy, 1, 6},  {1041, CatType::Laser, 1, 3},
    {1120, CatType::Hissing, 1, 2}, {1140, CatType::Hissing, 1, 1}, {1201, CatType::Hissing, 1, 1},
    {1281, CatType::Hissing, 1, 1}, {1308, CatType::Rich, 1, 0},    {1348, CatType::Rich, 1, 0},
    {1388, CatType::Rich, 1, 0},    {1428, CatType::Rich, 1, 0},    {1468, CatType::Rich, 1, 0},
    {1508, CatType::Rich, 1, 0},    {1548, CatType::Rich, 1, 0},    {1588, CatType::Rich, 1, 0},
    {1620, CatType::Laser, 0, 3},
};

Game play(const std::vector<Move>& moves, int maxTicks) {
    Game game(Config{}, defaultWaves());
    for (const Move& m : moves) {
        tickTo(game, m.tick);
        EXPECT_EQ(game.place(m.type, m.lane, m.col), PlaceResult::Ok)
            << "tick " << m.tick << " lane " << m.lane << " col " << m.col;
    }
    tickTo(game, maxTicks);
    return game;
}

}  // namespace

TEST(FullGame, SensiblePlayWinsAllThreeWaves) {
    const Game game = play(kWinningGame, 5000);
    EXPECT_EQ(game.status(), Status::Won);
    EXPECT_EQ(game.state().lives, 3);
    EXPECT_EQ(game.state().tick, 1648);
}

TEST(FullGame, NoCatsLosesDuringWaveOne) {
    const Game game = play({}, 5000);
    EXPECT_EQ(game.status(), Status::Lost);
    EXPECT_EQ(game.state().tick, 421);
    EXPECT_EQ(game.currentWave(), 1);
}

TEST(Determinism, SameInputsGiveSameState) {
    const Game a = play(kWinningGame, 1000);
    const Game b = play(kWinningGame, 1000);
    EXPECT_EQ(a.state(), b.state());
}

TEST(Determinism, GamesDivergeOnlyThroughInputs) {
    Game a(Config{}, defaultWaves());
    Game b(Config{}, defaultWaves());
    tickN(a, 300);
    tickN(b, 300);
    ASSERT_EQ(a.state(), b.state());

    ASSERT_EQ(a.place(CatType::Sleepy, 2, 4), PlaceResult::Ok);
    tickN(a, 50);
    tickN(b, 50);
    EXPECT_NE(a.state(), b.state());
}
