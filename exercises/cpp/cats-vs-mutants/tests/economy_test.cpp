#include <gtest/gtest.h>

#include "test_helpers.hpp"

using namespace cvm;
using namespace cvm::test;

TEST(Economy, StartsWithConfiguredTreatsAndLives) {
    Game game(Config{}, {kNever});
    EXPECT_EQ(game.state().treats, 150);
    EXPECT_EQ(game.state().lives, 3);
    EXPECT_EQ(game.state().tick, 0);
    EXPECT_EQ(game.status(), Status::Playing);
}

TEST(Economy, PassiveIncomeEvery100Ticks) {
    Game game(Config{}, {kNever});

    tickTo(game, 99);
    EXPECT_EQ(game.state().treats, 150);
    tickTo(game, 100);
    EXPECT_EQ(game.state().treats, 175);
    tickTo(game, 199);
    EXPECT_EQ(game.state().treats, 175);
    tickTo(game, 200);
    EXPECT_EQ(game.state().treats, 200);
}

TEST(Economy, PassiveIncomeFollowsConfig) {
    Config config;
    config.passiveIncome = 7;
    config.passiveIncomeInterval = 3;
    Game game(config, {kNever});

    tickN(game, 9);
    EXPECT_EQ(game.state().treats, 150 + 3 * 7);
}

TEST(Economy, RichCatProducesEvery80TicksFromPlacement) {
    Config config = quietConfig();
    config.startingTreats = 50;
    Game game(config, {kNever});
    ASSERT_EQ(game.place(CatType::Rich, 0, 0), PlaceResult::Ok);

    tickTo(game, 79);
    EXPECT_EQ(game.state().treats, 0);
    tickTo(game, 80);
    EXPECT_EQ(game.state().treats, 25);
    tickTo(game, 159);
    EXPECT_EQ(game.state().treats, 25);
    tickTo(game, 160);
    EXPECT_EQ(game.state().treats, 50);
}

TEST(Economy, RichCatTimerStartsAtPlacementTick) {
    Config config = quietConfig();
    config.startingTreats = 50;
    Game game(config, {kNever});
    tickTo(game, 10);
    ASSERT_EQ(game.place(CatType::Rich, 0, 0), PlaceResult::Ok);

    tickTo(game, 89);
    EXPECT_EQ(game.state().treats, 0);
    tickTo(game, 90);
    EXPECT_EQ(game.state().treats, 25);
}

TEST(Economy, RichCatCooldownCountsDownAndResets) {
    Game game(quietConfig(), {kNever});
    ASSERT_EQ(game.place(CatType::Rich, 0, 0), PlaceResult::Ok);

    tickN(game, 1);
    EXPECT_EQ(game.state().cats.front().cooldown, 79);
    tickTo(game, 80);
    EXPECT_EQ(game.state().cats.front().cooldown, 80);
}

TEST(Economy, EachRichCatProduces) {
    Config config = quietConfig();
    config.startingTreats = 100;
    Game game(config, {kNever});
    ASSERT_EQ(game.place(CatType::Rich, 0, 0), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Rich, 1, 0), PlaceResult::Ok);

    tickTo(game, 80);
    EXPECT_EQ(game.state().treats, 50);
}

TEST(Economy, RichProductionFollowsConfig) {
    Config config = quietConfig();
    config.startingTreats = 50;
    config.richProduction = 3;
    config.rich.interval = 4;
    Game game(config, {kNever});
    ASSERT_EQ(game.place(CatType::Rich, 0, 0), PlaceResult::Ok);

    tickN(game, 12);
    EXPECT_EQ(game.state().treats, 9);
}

TEST(Economy, OtherCatsDoNotProduce) {
    Game game(quietConfig(), {kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 0, 0), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 1, 0), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Laser, 2, 0), PlaceResult::Ok);
    const int treats = game.state().treats;

    tickN(game, 240);
    EXPECT_EQ(game.state().treats, treats);
}

TEST(Economy, PassiveIncomeAndRichCatStack) {
    Config config;
    config.passiveIncomeInterval = 80;
    Game game(config, {kNever});
    ASSERT_EQ(game.place(CatType::Rich, 0, 0), PlaceResult::Ok);

    tickTo(game, 80);
    EXPECT_EQ(game.state().treats, 100 + 25 + 25);
}
