#include <gtest/gtest.h>

#include "test_helpers.hpp"

using namespace cvm;
using namespace cvm::test;

TEST(Placement, PlacingDeductsCostAndCreatesCat) {
    Game game(Config{}, {kNever});

    ASSERT_EQ(game.place(CatType::Hissing, 2, 3), PlaceResult::Ok);

    EXPECT_EQ(game.state().treats, 50);
    ASSERT_EQ(game.state().cats.size(), 1u);
    const Cat& cat = game.state().cats.front();
    EXPECT_EQ(cat.type, CatType::Hissing);
    EXPECT_EQ(cat.lane, 2);
    EXPECT_EQ(cat.col, 3);
    EXPECT_EQ(cat.health, 60);
    EXPECT_EQ(cat.cooldown, 15);
}

TEST(Placement, EachCatTypeHasItsCostAndHealth) {
    struct Case { CatType type; int cost; int health; };
    for (const Case& c : {Case{CatType::Rich, 50, 40}, Case{CatType::Hissing, 100, 60},
                          Case{CatType::Sleepy, 50, 300}, Case{CatType::Laser, 175, 60}}) {
        Game game(quietConfig(), {kNever});
        ASSERT_EQ(game.place(c.type, 0, 0), PlaceResult::Ok);
        EXPECT_EQ(game.state().treats, 1000 - c.cost);
        EXPECT_EQ(game.state().cats.front().health, c.health);
    }
}

TEST(Placement, CostEqualToTreatsIsAllowed) {
    Config config;
    config.startingTreats = 175;
    Game game(config, {kNever});

    EXPECT_EQ(game.place(CatType::Laser, 0, 0), PlaceResult::Ok);
    EXPECT_EQ(game.state().treats, 0);
}

TEST(Placement, CostAboveTreatsIsRejected) {
    Config config;
    config.startingTreats = 99;
    Game game(config, {kNever});

    EXPECT_EQ(game.place(CatType::Hissing, 0, 0), PlaceResult::NotEnoughTreats);
    EXPECT_EQ(game.state().treats, 99);
    EXPECT_TRUE(game.state().cats.empty());
}

TEST(Placement, DefaultTreatsCannotAffordLaser) {
    Game game(Config{}, {kNever});
    EXPECT_EQ(game.place(CatType::Laser, 0, 0), PlaceResult::NotEnoughTreats);
}

TEST(Placement, OccupiedCellIsRejectedWithoutCharging) {
    Game game(Config{}, {kNever});
    ASSERT_EQ(game.place(CatType::Rich, 1, 1), PlaceResult::Ok);

    EXPECT_EQ(game.place(CatType::Sleepy, 1, 1), PlaceResult::CellOccupied);
    EXPECT_EQ(game.state().treats, 100);
    ASSERT_EQ(game.state().cats.size(), 1u);
    EXPECT_EQ(game.state().cats.front().type, CatType::Rich);
}

TEST(Placement, NeighbouringCellsAreIndependent) {
    Game game(quietConfig(), {kNever});
    ASSERT_EQ(game.place(CatType::Rich, 1, 1), PlaceResult::Ok);

    EXPECT_EQ(game.place(CatType::Rich, 1, 2), PlaceResult::Ok);
    EXPECT_EQ(game.place(CatType::Rich, 2, 1), PlaceResult::Ok);
    EXPECT_EQ(game.state().cats.size(), 3u);
}

TEST(Placement, OutOfBoundsIsRejected) {
    Game game(quietConfig(), {kNever});

    EXPECT_EQ(game.place(CatType::Rich, -1, 0), PlaceResult::OutOfBounds);
    EXPECT_EQ(game.place(CatType::Rich, 5, 0), PlaceResult::OutOfBounds);
    EXPECT_EQ(game.place(CatType::Rich, 0, -1), PlaceResult::OutOfBounds);
    EXPECT_EQ(game.place(CatType::Rich, 0, 9), PlaceResult::OutOfBounds);
    EXPECT_TRUE(game.state().cats.empty());
    EXPECT_EQ(game.state().treats, 1000);
}

TEST(Placement, BoardCornersAreInBounds) {
    Game game(quietConfig(), {kNever});

    EXPECT_EQ(game.place(CatType::Rich, 0, 0), PlaceResult::Ok);
    EXPECT_EQ(game.place(CatType::Rich, 4, 8), PlaceResult::Ok);
    EXPECT_EQ(game.place(CatType::Rich, 0, 8), PlaceResult::Ok);
    EXPECT_EQ(game.place(CatType::Rich, 4, 0), PlaceResult::Ok);
}

TEST(Placement, BoundsFollowConfig) {
    Config config = quietConfig();
    config.lanes = 2;
    config.cols = 3;
    Game game(config, {SpawnEvent{1'000'000, 0, MutantType::Blob}});

    EXPECT_EQ(game.place(CatType::Rich, 1, 2), PlaceResult::Ok);
    EXPECT_EQ(game.place(CatType::Rich, 2, 0), PlaceResult::OutOfBounds);
    EXPECT_EQ(game.place(CatType::Rich, 0, 3), PlaceResult::OutOfBounds);
}

TEST(Placement, BoundsAreCheckedBeforeTreats) {
    Config config;
    config.startingTreats = 0;
    Game game(config, {kNever});

    EXPECT_EQ(game.place(CatType::Rich, 9, 9), PlaceResult::OutOfBounds);
}

TEST(Placement, OccupancyIsCheckedBeforeTreats) {
    Config config;
    config.startingTreats = 50;
    Game game(config, {kNever});
    ASSERT_EQ(game.place(CatType::Rich, 0, 0), PlaceResult::Ok);

    EXPECT_EQ(game.place(CatType::Rich, 0, 0), PlaceResult::CellOccupied);
}

TEST(Placement, CannotPlaceAfterGameIsOver) {
    Game game(Config{}, {});
    game.tick();
    ASSERT_EQ(game.status(), Status::Won);

    EXPECT_EQ(game.place(CatType::Rich, 0, 0), PlaceResult::GameOver);
    EXPECT_TRUE(game.state().cats.empty());
}

TEST(Placement, CanPlaceOnCellHoldingAMutant) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    game.tick();  // runner now at step 89, cell 8

    EXPECT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);
}

TEST(Remove, RemovesCatWithoutRefund) {
    Game game(Config{}, {kNever});
    ASSERT_EQ(game.place(CatType::Sleepy, 3, 4), PlaceResult::Ok);

    EXPECT_TRUE(game.remove(3, 4));
    EXPECT_TRUE(game.state().cats.empty());
    EXPECT_EQ(game.state().treats, 100);
}

TEST(Remove, EmptyCellReturnsFalse) {
    Game game(Config{}, {kNever});
    EXPECT_FALSE(game.remove(0, 0));
}

TEST(Remove, OnlyTheTargetCatIsRemoved) {
    Game game(quietConfig(), {kNever});
    ASSERT_EQ(game.place(CatType::Rich, 0, 0), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 1), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Hissing, 1, 0), PlaceResult::Ok);

    EXPECT_TRUE(game.remove(0, 1));

    EXPECT_EQ(game.state().cats.size(), 2u);
    EXPECT_NE(game.catAt(0, 0), nullptr);
    EXPECT_EQ(game.catAt(0, 1), nullptr);
    EXPECT_NE(game.catAt(1, 0), nullptr);
}

TEST(Remove, CellCanBeReusedAfterRemoval) {
    Game game(quietConfig(), {kNever});
    ASSERT_EQ(game.place(CatType::Rich, 2, 2), PlaceResult::Ok);
    ASSERT_TRUE(game.remove(2, 2));

    EXPECT_EQ(game.place(CatType::Laser, 2, 2), PlaceResult::Ok);
    EXPECT_EQ(game.catAt(2, 2)->type, CatType::Laser);
}

TEST(Remove, CannotRemoveAfterGameIsOver) {
    Game game(Config{}, {});
    ASSERT_EQ(game.place(CatType::Rich, 0, 0), PlaceResult::Ok);
    game.tick();
    ASSERT_EQ(game.status(), Status::Won);

    EXPECT_FALSE(game.remove(0, 0));
    EXPECT_EQ(game.state().cats.size(), 1u);
}

TEST(CatAt, FindsCatByLaneAndColumn) {
    Game game(quietConfig(), {kNever});
    ASSERT_EQ(game.place(CatType::Laser, 3, 5), PlaceResult::Ok);

    const Cat* cat = game.catAt(3, 5);
    ASSERT_NE(cat, nullptr);
    EXPECT_EQ(cat->type, CatType::Laser);
    EXPECT_EQ(game.catAt(5, 3), nullptr);
    EXPECT_EQ(game.catAt(3, 4), nullptr);
}
