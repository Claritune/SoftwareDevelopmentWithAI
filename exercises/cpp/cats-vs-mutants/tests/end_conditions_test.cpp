#include <gtest/gtest.h>

#include "test_helpers.hpp"

using namespace cvm;
using namespace cvm::test;

TEST(Tick, AdvancesTheCounter) {
    Game game(Config{}, {kNever});
    tickN(game, 7);
    EXPECT_EQ(game.state().tick, 7);
}

TEST(Win, NoWavesMeansWinOnFirstTick) {
    Game game(Config{}, {});
    EXPECT_EQ(game.status(), Status::Playing);
    game.tick();
    EXPECT_EQ(game.status(), Status::Won);
    EXPECT_EQ(game.state().status, Status::Won);
}

TEST(Win, NotWonWhileSpawnsArePending) {
    Game game(Config{}, {SpawnEvent{50, 0, MutantType::Runner}});
    tickTo(game, 49);
    EXPECT_TRUE(game.state().mutants.empty());
    EXPECT_EQ(game.status(), Status::Playing);
}

TEST(Win, NotWonWhileMutantsRemain) {
    Game game(Config{}, {SpawnEvent{1, 0, MutantType::Runner}});
    game.tick();
    EXPECT_EQ(game.state().nextSpawn, 1u);
    EXPECT_EQ(game.status(), Status::Playing);
}

TEST(Win, WonWhenLastMutantDies) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner}});
    ASSERT_EQ(game.place(CatType::Laser, 0, 4), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 59);
    EXPECT_EQ(game.status(), Status::Playing);
    tickTo(game, 60);
    EXPECT_EQ(game.status(), Status::Won);
}

TEST(Win, EquivalentMutantMustLeaveBeforeYouWin) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Equivalent}});
    tickTo(game, 181);
    EXPECT_EQ(game.status(), Status::Playing);
    tickTo(game, 182);
    EXPECT_EQ(game.status(), Status::Won);
    EXPECT_EQ(game.state().lives, 3);
}

TEST(Lose, LosingLastLifeLosesTheGame) {
    Config config = quietConfig();
    config.startingLives = 1;
    Game game(config, {SpawnEvent{1, 0, MutantType::Runner}, kNever});

    tickTo(game, 90);
    EXPECT_EQ(game.status(), Status::Playing);
    game.tick();
    EXPECT_EQ(game.status(), Status::Lost);
    EXPECT_EQ(game.state().lives, 0);
}

TEST(Lose, LivesNeverGoBelowZero) {
    Config config = quietConfig();
    config.startingLives = 1;
    Game game(config, {SpawnEvent{1, 0, MutantType::Runner}, SpawnEvent{1, 1, MutantType::Runner},
                       SpawnEvent{1, 2, MutantType::Runner}, kNever});
    tickTo(game, 91);
    EXPECT_EQ(game.status(), Status::Lost);
    EXPECT_EQ(game.state().lives, 0);
}

TEST(Lose, LossBeatsWinOnTheSameTick) {
    // The last mutant reaches home: the board is empty and every wave has spawned.
    Config config = quietConfig();
    config.startingLives = 1;
    Game game(config, {SpawnEvent{1, 0, MutantType::Runner}});
    tickTo(game, 91);
    EXPECT_EQ(game.status(), Status::Lost);
}

TEST(GameOver, TickDoesNothingAfterWin) {
    Game game(Config{}, {});
    ASSERT_EQ(game.place(CatType::Rich, 0, 0), PlaceResult::Ok);
    game.tick();
    ASSERT_EQ(game.status(), Status::Won);
    const GameState before = game.state();

    tickN(game, 200);
    EXPECT_EQ(game.state(), before);
}

TEST(GameOver, TickDoesNothingAfterLoss) {
    Config config;
    config.startingLives = 1;
    Game game(config, {SpawnEvent{1, 0, MutantType::Runner}, SpawnEvent{150, 0, MutantType::Blob}});
    tickTo(game, 91);
    ASSERT_EQ(game.status(), Status::Lost);
    const GameState before = game.state();

    tickN(game, 200);
    EXPECT_EQ(game.state(), before);
    EXPECT_EQ(game.state().nextSpawn, 1u);
}
