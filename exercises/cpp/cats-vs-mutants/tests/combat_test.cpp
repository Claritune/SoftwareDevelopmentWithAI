#include <gtest/gtest.h>

#include <algorithm>

#include "test_helpers.hpp"

using namespace cvm;
using namespace cvm::test;

namespace {

std::vector<int> hairballPositions(const Game& game) {
    std::vector<int> out;
    for (const Hairball& h : game.state().hairballs) out.push_back(h.position);
    std::sort(out.begin(), out.end());
    return out;
}

}  // namespace

// ---- Hissing Cat ------------------------------------------------------------

TEST(Hissing, SpitsEvery15TicksWhenMutantInLane) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Brute}, kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 0, 0), PlaceResult::Ok);

    tickTo(game, 14);
    EXPECT_TRUE(game.state().hairballs.empty());
    tickTo(game, 15);
    ASSERT_EQ(game.state().hairballs.size(), 1u);
    const Hairball& h = game.state().hairballs.front();
    EXPECT_EQ(h.lane, 0);
    EXPECT_EQ(h.position, 15);  // spawned at cell start + 10, then moved 5
    EXPECT_EQ(h.originCol, 0);
}

TEST(Hissing, HairballStartsAtTheCatsRightEdge) {
    Game game(quietConfig(), {SpawnEvent{1, 2, MutantType::Brute}, kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 2, 3), PlaceResult::Ok);

    tickTo(game, 15);
    ASSERT_EQ(game.state().hairballs.size(), 1u);
    EXPECT_EQ(game.state().hairballs.front().position, 45);
    EXPECT_EQ(game.state().hairballs.front().originCol, 3);
}

TEST(Hissing, NoMutantNoHairballAndTimerStillResets) {
    Game game(quietConfig(), {SpawnEvent{20, 0, MutantType::Brute}, kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 0, 0), PlaceResult::Ok);

    tickTo(game, 15);
    EXPECT_TRUE(game.state().hairballs.empty());
    EXPECT_EQ(game.catAt(0, 0)->cooldown, 15);
    tickTo(game, 29);
    EXPECT_TRUE(game.state().hairballs.empty());
    tickTo(game, 30);
    EXPECT_EQ(game.state().hairballs.size(), 1u);
}

TEST(Hissing, IgnoresMutantsInOtherLanes) {
    Game game(quietConfig(), {SpawnEvent{1, 1, MutantType::Brute}, kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 0, 0), PlaceResult::Ok);

    tickTo(game, 15);
    EXPECT_TRUE(game.state().hairballs.empty());
}

TEST(Hissing, IgnoresMutantsBehindIt) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    tickTo(game, 50);  // runner at step 40, cell 4
    ASSERT_EQ(game.place(CatType::Hissing, 0, 6), PlaceResult::Ok);

    tickTo(game, 65);
    EXPECT_TRUE(game.state().hairballs.empty());
}

TEST(Hissing, ShootsMutantInItsOwnCell) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 0, 8), PlaceResult::Ok);

    tickTo(game, 15);
    EXPECT_EQ(onlyMutant(game).health, 40);
    EXPECT_TRUE(game.state().hairballs.empty());
}

TEST(Hissing, MutantSpawnedThisTickCanBeTargeted) {
    // Spawning (step 3) runs before cats fire (step 4).
    Game game(quietConfig(), {SpawnEvent{15, 0, MutantType::Brute}, kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 0, 0), PlaceResult::Ok);

    tickTo(game, 15);
    EXPECT_EQ(game.state().hairballs.size(), 1u);
}

// ---- Hairballs --------------------------------------------------------------

TEST(Hairball, MovesFiveStepsPerTickAndHitsForTwenty) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Brute}, kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 0, 0), PlaceResult::Ok);

    tickTo(game, 16);
    EXPECT_EQ(hairballPositions(game), std::vector<int>{20});
    tickTo(game, 28);  // hairball 80, brute 81
    EXPECT_EQ(hairballPositions(game), std::vector<int>{80});
    EXPECT_EQ(onlyMutant(game).health, 300);
    tickTo(game, 29);  // hairball 85 passes brute at 81
    EXPECT_TRUE(game.state().hairballs.empty());
    EXPECT_EQ(onlyMutant(game).health, 280);
}

TEST(Hairball, HitsWhenPositionsAreEqual) {
    Config config = quietConfig();
    config.hairballSpeed = 79;  // 10 + 79 = 89, exactly where the runner waits
    Game game(config, {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 0, 0), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 15);
    EXPECT_EQ(onlyMutant(game).health, 40);
    EXPECT_TRUE(game.state().hairballs.empty());
}

TEST(Hairball, MissesWhenOneStepShort) {
    Config config = quietConfig();
    config.hairballSpeed = 78;  // 10 + 78 = 88, one short of the runner
    Game game(config, {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 0, 0), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 15);
    EXPECT_EQ(onlyMutant(game).health, 60);
    EXPECT_EQ(hairballPositions(game), std::vector<int>{88});
}

TEST(Hairball, DamageFollowsConfig) {
    Config config = quietConfig();
    config.hairballDamage = 7;
    Game game(config, {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 0, 8), PlaceResult::Ok);

    tickTo(game, 15);
    EXPECT_EQ(onlyMutant(game).health, 53);
}

TEST(Hairball, HitsTheMutantClosestToTheCat) {
    Config config = quietConfig();
    config.hairballSpeed = 79;  // reaches step 89 on the tick it is spat
    // The Blob spawns first but stops at 89; the Hopper jumps the Sleepy Cat and walks on.
    Game game(config, {SpawnEvent{1, 0, MutantType::Blob}, SpawnEvent{1, 0, MutantType::Hopper},
                       kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 0, 0), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 15);
    ASSERT_EQ(game.state().mutants.size(), 2u);
    const Mutant& blob = game.state().mutants[0];
    const Mutant& hopper = game.state().mutants[1];
    ASSERT_EQ(hopper.type, MutantType::Hopper);
    EXPECT_EQ(blob.position, 89);
    EXPECT_EQ(hopper.position, 73);
    EXPECT_EQ(blob.health, 100);
    EXPECT_EQ(hopper.health, 60);
}

TEST(Hairball, HitsOnlyOneMutant) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner},
                              SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 0, 8), PlaceResult::Ok);

    tickTo(game, 15);
    ASSERT_EQ(game.state().mutants.size(), 2u);
    EXPECT_EQ(game.state().mutants[0].health + game.state().mutants[1].health, 100);
}

TEST(Hairball, NeverHitsMutantsLeftOfTheCat) {
    Config config = quietConfig();
    config.hairballSpeed = 79;
    Game game(config, {SpawnEvent{1, 0, MutantType::Runner}, SpawnEvent{51, 0, MutantType::Runner},
                       kNever});
    tickTo(game, 50);  // first runner at step 40, already past column 5
    ASSERT_EQ(game.place(CatType::Hissing, 0, 5), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 2), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 65);
    ASSERT_EQ(game.state().mutants.size(), 2u);
    const Mutant& behind = game.state().mutants[0];
    const Mutant& ahead = game.state().mutants[1];
    EXPECT_EQ(behind.position, 29);
    EXPECT_EQ(ahead.position, 89);
    EXPECT_EQ(behind.health, 60);
    EXPECT_EQ(ahead.health, 40);
}

TEST(Hairball, IgnoresMutantAlreadyKilledThisTick) {
    Config config = quietConfig();
    config.laserDamage = 100;   // laser kills the runner outright
    config.hissing.interval = 30;  // hissing and laser fire on the same tick
    config.hairballSpeed = 80;  // hairball reaches step 90 immediately
    Game game(config, {SpawnEvent{1, 0, MutantType::Runner}, SpawnEvent{30, 0, MutantType::Blob},
                       kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 0, 0), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Laser, 0, 4), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 30);
    const Mutant& blob = onlyMutant(game);
    EXPECT_EQ(blob.type, MutantType::Blob);
    EXPECT_EQ(blob.health, 80);
}

TEST(Hairball, DisappearsAfterPassingStep90) {
    // The Equivalent Mutant keeps the cat spitting, but hairballs pass through it.
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Equivalent}, kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 0, 0), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 30);
    EXPECT_EQ(hairballPositions(game), (std::vector<int>{15, 90}));
    tickTo(game, 31);
    EXPECT_EQ(hairballPositions(game), std::vector<int>{20});
}

TEST(Hairball, CanHitMutantAtSpawnPositionAfterPassingIt) {
    Config config = quietConfig();
    config.hairballSpeed = 85;  // 10 + 85 = 95, past the edge, but the Blob at 90 is in reach
    Game game(config, {SpawnEvent{15, 0, MutantType::Blob}, kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 0, 0), PlaceResult::Ok);

    tickTo(game, 15);
    EXPECT_EQ(onlyMutant(game).health, 80);
    EXPECT_TRUE(game.state().hairballs.empty());
}

TEST(Hairball, StaysInItsLane) {
    Config config = quietConfig();
    config.hairballSpeed = 79;
    Game game(config, {SpawnEvent{1, 0, MutantType::Runner}, SpawnEvent{1, 1, MutantType::Runner},
                       kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 0, 0), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 1, 8), PlaceResult::Ok);

    tickTo(game, 15);
    EXPECT_EQ(game.state().mutants[0].health, 40);
    EXPECT_EQ(game.state().mutants[1].health, 60);
}

// ---- Laser Cat --------------------------------------------------------------

TEST(Laser, Deals30DamageEvery30Ticks) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Laser, 0, 4), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 29);
    EXPECT_EQ(onlyMutant(game).health, 60);
    tickTo(game, 30);
    EXPECT_EQ(onlyMutant(game).health, 30);
    tickTo(game, 59);
    EXPECT_EQ(onlyMutant(game).health, 30);
    tickTo(game, 60);
    EXPECT_TRUE(game.state().mutants.empty());  // exactly 0 health counts as dead
}

TEST(Laser, ReachesFourCellsToTheRight) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Laser, 0, 4), PlaceResult::Ok);  // covers cells 4..8
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 30);
    EXPECT_EQ(onlyMutant(game).health, 30);
}

TEST(Laser, DoesNotReachFiveCellsToTheRight) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Laser, 0, 3), PlaceResult::Ok);  // covers cells 3..7
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 30);
    EXPECT_EQ(onlyMutant(game).health, 60);
}

TEST(Laser, RangeAndDamageFollowConfig) {
    Config config = quietConfig();
    config.laserRange = 5;
    config.laserDamage = 11;
    Game game(config, {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Laser, 0, 3), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 30);
    EXPECT_EQ(onlyMutant(game).health, 49);
}

TEST(Laser, HitsEveryMutantInRangeInItsLaneOnly) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner},
                              SpawnEvent{1, 0, MutantType::Blob},
                              SpawnEvent{1, 1, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Laser, 0, 4), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 1, 8), PlaceResult::Ok);

    tickTo(game, 30);
    ASSERT_EQ(game.state().mutants.size(), 3u);
    EXPECT_EQ(game.state().mutants[0].health, 30);
    EXPECT_EQ(game.state().mutants[1].health, 70);
    EXPECT_EQ(game.state().mutants[2].health, 60);
}

TEST(Laser, HitsMutantInItsOwnCell) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Laser, 0, 8), PlaceResult::Ok);

    tickTo(game, 30);
    EXPECT_EQ(onlyMutant(game).health, 30);
}

TEST(Laser, IgnoresMutantsBehindIt) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner},
                              SpawnEvent{50, 0, MutantType::Runner}, kNever});
    tickTo(game, 50);  // first runner at step 40, cell 4
    ASSERT_EQ(game.place(CatType::Laser, 0, 5), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 2), PlaceResult::Ok);

    tickTo(game, 80);
    ASSERT_EQ(game.state().mutants.size(), 2u);
    EXPECT_EQ(game.state().mutants[0].position, 29);
    EXPECT_EQ(game.state().mutants[0].health, 60);
    EXPECT_EQ(game.state().mutants[1].health, 30);
}

TEST(Laser, TimerResetsEvenWithoutTarget) {
    Game game(quietConfig(), {SpawnEvent{31, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Laser, 0, 4), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 30);
    EXPECT_EQ(game.catAt(0, 4)->cooldown, 30);
    tickTo(game, 59);
    EXPECT_EQ(onlyMutant(game).health, 60);
    tickTo(game, 60);
    EXPECT_EQ(onlyMutant(game).health, 30);
}

TEST(Laser, CreatesNoHairballs) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Brute}, kNever});
    ASSERT_EQ(game.place(CatType::Laser, 0, 8), PlaceResult::Ok);
    tickTo(game, 30);
    EXPECT_TRUE(game.state().hairballs.empty());
}

// ---- Sleepy Cat -------------------------------------------------------------

TEST(Sleepy, NeverAttacks) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Runner}, kNever});
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 100);
    EXPECT_EQ(onlyMutant(game).health, 60);
    EXPECT_TRUE(game.state().hairballs.empty());
}

// ---- Equivalent Mutant ------------------------------------------------------

TEST(Equivalent, HairballsPassThroughIt) {
    Config config = quietConfig();
    config.hairballSpeed = 80;  // 10 + 80 = 90: already past the mutant waiting at 89
    Game game(config, {SpawnEvent{1, 0, MutantType::Equivalent}, kNever});
    ASSERT_EQ(game.place(CatType::Hissing, 0, 0), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 15);
    EXPECT_EQ(onlyMutant(game).health, 1);
    EXPECT_EQ(hairballPositions(game), std::vector<int>{90});
}

TEST(Equivalent, LaserCannotDamageIt) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Equivalent}, kNever});
    ASSERT_EQ(game.place(CatType::Laser, 0, 4), PlaceResult::Ok);
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 90);
    EXPECT_EQ(onlyMutant(game).health, 1);
}

TEST(Equivalent, CanBeBlockedAndBites) {
    Game game(quietConfig(), {SpawnEvent{1, 0, MutantType::Equivalent}, kNever});
    ASSERT_EQ(game.place(CatType::Sleepy, 0, 8), PlaceResult::Ok);

    tickTo(game, 10);
    EXPECT_EQ(game.catAt(0, 8)->health, 300);
    tickTo(game, 11);  // entered the cell on tick 2, so the first bite lands on tick 11
    EXPECT_EQ(game.catAt(0, 8)->health, 290);
    EXPECT_EQ(onlyMutant(game).position, 89);
}
