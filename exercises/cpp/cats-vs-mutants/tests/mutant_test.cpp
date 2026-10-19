#include <gtest/gtest.h>

#include "test_helpers.hpp"

using namespace cvm;
using namespace cvm::test;

// ---- Spawning ---------------------------------------------------------------

TEST(Spawn, MutantAppearsOnItsTickAtSpawnPosition) {
    Game game(quietConfig(), {SpawnEvent{5, 3, MutantType::Brute}, kNever});

    tickTo(game, 4);
    EXPECT_TRUE(game.state().mutants.empty());
    tickTo(game, 5);
    const Mutant& m = onlyMutant(game);
    EXPECT_EQ(m.type, MutantType::Brute);
    EXPECT_EQ(m.lane, 3);
    EXPECT_EQ(m.position, 90);
    EXPECT_EQ(m.health, 300);
    EXPECT_EQ(m.biteCooldown, 10);
    EXPECT_FALSE(m.hasJumped);
}

TEST(Spawn, EachTypeGetsItsConfiguredHealth) {
    struct Case { MutantType type; int health; };
    for (const Case& c : {Case{MutantType::Blob, 100}, Case{MutantType::Runner, 60},
                          Case{MutantType::Brute, 300}, Case{MutantType::Hopper, 80},
                          Case{MutantType::Equivalent, 1}}) {
        Game game(quietConfig(), {SpawnEvent{1, 0, c.type}, kNever});
        game.tick();
        EXPECT_EQ(onlyMutant(game).health, c.health);
    }
}

TEST(Spawn, SpawnPositionFollowsBoardSize) {
    Config config = quietConfig();
    config.cols = 4;
    config.cellSize = 5;
    Game game(config, {SpawnEvent{1, 0, MutantType::Brute}, kNever});
    game.tick();
    EXPECT_EQ(onlyMutant(game).position, 20);
}

TEST(Spawn, AllEventsOnTheSameTickSpawn) {
    Game game(quietConfig(), {SpawnEvent{3, 0, MutantType::Blob},
                              SpawnEvent{3, 1, MutantType::Runner},
                              SpawnEvent{3, 2, MutantType::Brute}, kNever});
    tickTo(game, 3);
    EXPECT_EQ(game.state().mutants.size(), 3u);
    EXPECT_EQ(game.state().nextSpawn, 3u);
}

TEST(Spawn, EventsAreSortedByTick) {
    Game game(quietConfig(), {SpawnEvent{10, 1, MutantType::Runner},
                              SpawnEvent{5, 0, MutantType::Blob}, kNever});

    tickTo(game, 5);
    ASSERT_EQ(game.state().mutants.size(), 1u);
    EXPECT_EQ(game.state().mutants[0].type, MutantType::Blob);
    tickTo(game, 10);
    ASSERT_EQ(game.state().mutants.size(), 2u);
    EXPECT_EQ(game.state().mutants[1].type, MutantType::Runner);
}

TEST(Spawn, EventAtTickZeroSpawnsOnFirstTick) {
    Game game(quietConfig(), {SpawnEvent{0, 0, MutantType::Brute}, kNever});
    game.tick();
    EXPECT_EQ(game.state().mutants.size(), 1u);
}

// ---- Movement ---------------------------------------------------------------

TEST(Movement, BlobMovesOneStepEveryTwoTicks) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Blob}, kNever});

    tickTo(game, 1);
    EXPECT_EQ(onlyMutant(game).position, 90);
    tickTo(game, 2);
    EXPECT_EQ(onlyMutant(game).position, 89);
    tickTo(game, 3);
    EXPECT_EQ(onlyMutant(game).position, 89);
    tickTo(game, 4);
    EXPECT_EQ(onlyMutant(game).position, 88);
    tickTo(game, 40);
    EXPECT_EQ(onlyMutant(game).position, 70);
}

TEST(Movement, RunnerMovesEveryTick) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner}, kNever});

    tickTo(game, 1);
    EXPECT_EQ(onlyMutant(game).position, 89);
    tickTo(game, 30);
    EXPECT_EQ(onlyMutant(game).position, 60);
}

TEST(Movement, BruteMovesOneStepEveryThreeTicks) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Brute}, kNever});

    tickTo(game, 2);
    EXPECT_EQ(onlyMutant(game).position, 90);
    tickTo(game, 3);
    EXPECT_EQ(onlyMutant(game).position, 89);
    tickTo(game, 30);
    EXPECT_EQ(onlyMutant(game).position, 80);
}

TEST(Movement, HopperAndEquivalentMoveLikeBlobs) {
    for (MutantType type : {MutantType::Hopper, MutantType::Equivalent}) {
        Game game(quietConfig(), {SpawnEvent{1, 0, type}, kNever});
        tickTo(game, 40);
        EXPECT_EQ(onlyMutant(game).position, 70);
    }
}

TEST(Movement, SpeedFollowsConfig) {
    Config config = quietConfig();
    config.blob.moveInterval = 5;
    Game game(config, {SpawnEvent{1, 0, MutantType::Blob}, kNever});
    tickTo(game, 50);
    EXPECT_EQ(onlyMutant(game).position, 80);
}

// ---- Blocking ---------------------------------------------------------------

TEST(Blocking, CatInMutantCellStopsIt) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 1);
    EXPECT_EQ(onlyMutant(game).position, 89);
    tickTo(game, 50);
    EXPECT_EQ(onlyMutant(game).position, 89);
}

TEST(Blocking, MutantWalksUpToTheCatCell) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 4), PlaceResult::Ok);

    tickTo(game, 100);
    EXPECT_EQ(onlyMutant(game).position, 49);
}

TEST(Blocking, CatInAnotherLaneDoesNotBlock) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Sleepy, 1, 8), PlaceResult::Ok);

    tickTo(game, 10);
    EXPECT_EQ(onlyMutant(game).position, 80);
}

TEST(Blocking, MutantResumesWhenCatIsRemoved) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);
    tickTo(game, 20);
    ASSERT_TRUE(game.remove(0, 8));

    tickTo(game, 21);
    EXPECT_EQ(onlyMutant(game).position, 88);
}

// ---- Bites ------------------------------------------------------------------

TEST(Bites, BlockedMutantBitesEveryTenTicks) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 9);
    EXPECT_EQ(game.catAt(0, 8)->health, 300);
    tickTo(game, 10);
    EXPECT_EQ(game.catAt(0, 8)->health, 290);
    tickTo(game, 19);
    EXPECT_EQ(game.catAt(0, 8)->health, 290);
    tickTo(game, 20);
    EXPECT_EQ(game.catAt(0, 8)->health, 280);
}

TEST(Bites, BiteDamageAndIntervalFollowConfig) {
    Config config = quietConfig();
    config.biteDamage = 7;
    config.biteInterval = 3;
    Game game(config, {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 9);
    EXPECT_EQ(game.catAt(0, 8)->health, 300 - 3 * 7);
}

TEST(Bites, EveryBlockedMutantBites) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner},
                              SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 10);
    EXPECT_EQ(game.catAt(0, 8)->health, 280);
}

TEST(Bites, CatAtZeroHealthIsRemovedAndMutantMovesOn) {
    Config config = quietConfig();
    config.sleepy.health = 20;
    Game game(config, {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 19);
    ASSERT_NE(game.catAt(0, 8), nullptr);
    EXPECT_EQ(game.catAt(0, 8)->health, 10);
    tickTo(game, 20);
    EXPECT_EQ(game.catAt(0, 8), nullptr);
    EXPECT_EQ(onlyMutant(game).position, 89);
    tickTo(game, 21);
    EXPECT_EQ(onlyMutant(game).position, 88);
}

TEST(Bites, BiteTimerResetsWhenNoLongerBlocked) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);
    tickTo(game, 5);
    EXPECT_EQ(onlyMutant(game).biteCooldown, 5);
    ASSERT_TRUE(game.remove(0, 8));

    tickTo(game, 6);
    EXPECT_EQ(onlyMutant(game).biteCooldown, 10);
}

TEST(Bites, UnblockedMutantNeverBites) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Sleepy, 1, 8), PlaceResult::Ok);

    tickTo(game, 30);
    EXPECT_EQ(game.catAt(1, 8)->health, 300);
}

TEST(Bites, MutantKilledThisTickDoesNotBite) {
    Config config = quietConfig();
    config.hairballDamage = 60;  // one hairball kills a Runner
    config.biteInterval = 15;    // the bite would land on the same tick as the hairball
    Game game(config, {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 0, 8), PlaceResult::Ok);

    tickTo(game, 15);
    EXPECT_TRUE(game.state().mutants.empty());
    EXPECT_EQ(game.catAt(0, 8)->health, 60);
}

// ---- Hopper -----------------------------------------------------------------

TEST(Hopper, JumpsToTheCellLeftOfTheFirstBlockingCat) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Hopper}, kNever});
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 5), PlaceResult::Ok);

    tickTo(game, 62);
    EXPECT_EQ(onlyMutant(game).position, 59);
    EXPECT_FALSE(onlyMutant(game).hasJumped);
    tickTo(game, 63);
    EXPECT_EQ(onlyMutant(game).position, 49);
    EXPECT_TRUE(onlyMutant(game).hasJumped);
    tickTo(game, 64);
    EXPECT_EQ(onlyMutant(game).position, 49);
    tickTo(game, 65);
    EXPECT_EQ(onlyMutant(game).position, 48);
    EXPECT_EQ(game.catAt(0, 5)->health, 300);  // it never stopped to bite
}

TEST(Hopper, SecondBlockingCatStopsIt) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Hopper}, kNever});
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 5), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 4), PlaceResult::Ok);

    tickTo(game, 100);
    EXPECT_EQ(onlyMutant(game).position, 49);
    EXPECT_LT(game.catAt(0, 4)->health, 300);
}

TEST(Hopper, JumpingOverCatInColumnZeroReachesHome) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Hopper}, kNever});
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 0), PlaceResult::Ok);

    tickTo(game, 162);
    EXPECT_EQ(onlyMutant(game).position, 9);
    EXPECT_EQ(game.state().lives, 3);
    tickTo(game, 163);
    EXPECT_TRUE(game.state().mutants.empty());
    EXPECT_EQ(game.state().lives, 2);
}

TEST(Hopper, OtherMutantsNeverJump) {
    for (MutantType type : {MutantType::Blob, MutantType::Runner, MutantType::Brute,
                            MutantType::Equivalent}) {
        Game game(quietConfig(), {SpawnEvent{1, 0, type}, kNever});
        ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);
        tickTo(game, 20);
        EXPECT_EQ(onlyMutant(game).position, 89);
        EXPECT_FALSE(onlyMutant(game).hasJumped);
    }
}

// ---- Reaching home ----------------------------------------------------------

TEST(Home, MutantBelowStepZeroCostsALife) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner}, kNever});

    tickTo(game, 90);
    EXPECT_EQ(onlyMutant(game).position, 0);
    EXPECT_EQ(game.state().lives, 3);
    tickTo(game, 91);
    EXPECT_TRUE(game.state().mutants.empty());
    EXPECT_EQ(game.state().lives, 2);
}

TEST(Home, EachMutantCostsOneLife) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner},
                              SpawnEvent{1, 1, MutantType::Runner}, kNever});
    tickTo(game, 91);
    EXPECT_EQ(game.state().lives, 1);
    EXPECT_EQ(game.status(), Status::Playing);
}

TEST(Home, EquivalentMutantCostsNoLife) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Equivalent}, kNever});

    tickTo(game, 181);
    EXPECT_EQ(onlyMutant(game).position, 0);
    tickTo(game, 182);
    EXPECT_TRUE(game.state().mutants.empty());
    EXPECT_EQ(game.state().lives, 3);
}
