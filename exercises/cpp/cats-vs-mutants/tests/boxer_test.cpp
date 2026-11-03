#include <gtest/gtest.h>

#include <vector>

#include "test_helpers.hpp"

// Boxer Cat (ambush trap). Spec: docs/features/boxer-cat.md. Plan: docs/qa/boxer-cat.md.
//
// Reference timings with the defaults and a Boxer Cat at (0, 8), mutant scheduled at tick 0:
//   Runner: at 89 after tick 1, ambushed on tick 2, stunned 2..51, first step on 52.
//   Blob:   at 89 after tick 2, ambushed on tick 3, stunned 3..52, first step on 54.
//   Brute:  at 89 after tick 3, ambushed on tick 4, stunned 4..53, first step on 56.

namespace cvm::test {
namespace {

void placeOk(Game& game, CatType type, int lane, int col) {
    ASSERT_EQ(game.place(type, lane, col), PlaceResult::Ok)
        << "lane " << lane << " col " << col;
}

// A game with a Boxer Cat at (0, 8) and one mutant of `type` scheduled at tick 0 in lane 0.
Game boxerAt8(Config config, MutantType type, bool keepRunning = true) {
    std::vector<SpawnEvent> waves{{0, 0, type}};
    if (keepRunning) waves.push_back(kNever);
    Game game(config, waves);
    placeOk(game, CatType::Boxer, 0, 8);
    return game;
}

}  // namespace

// ---- Stats, placement, no action ---------------------------------------------

TEST(BoxerStats, DefaultConfig) {
    const Config config{};
    EXPECT_EQ(config.cat(CatType::Boxer).cost, 25);
    EXPECT_EQ(config.cat(CatType::Boxer).health, 20);
    EXPECT_EQ(config.cat(CatType::Boxer).interval, 0);
    EXPECT_EQ(config.ambushDamage, 40);
    EXPECT_EQ(config.stunDuration, 50);
}

TEST(BoxerStats, PlacingCostsExactlyAllTreatsAndDoesNothing) {
    Config config = quietConfig();
    config.startingTreats = 25;
    config.passiveIncome = 0;
    Game game(config, {SpawnEvent{1000, 1, MutantType::Blob}});

    EXPECT_EQ(game.place(CatType::Boxer, 0, 0), PlaceResult::Ok);
    EXPECT_EQ(game.state().treats, 0);

    tickN(game, 200);
    ASSERT_EQ(game.status(), Status::Playing);
    EXPECT_EQ(game.state().treats, 0);
    ASSERT_NE(game.catAt(0, 0), nullptr);
    EXPECT_EQ(game.catAt(0, 0)->type, CatType::Boxer);
    EXPECT_EQ(game.catAt(0, 0)->health, 20);
    EXPECT_EQ(game.catAt(0, 0)->cooldown, 0);  // no step ever counts it down
    EXPECT_TRUE(game.state().hairballs.empty());
}

TEST(BoxerStats, OneTreatShortIsRejected) {
    Config config = quietConfig();
    config.startingTreats = 24;
    Game game(config, {kNever});

    EXPECT_EQ(game.place(CatType::Boxer, 0, 0), PlaceResult::NotEnoughTreats);
    EXPECT_EQ(game.state().treats, 24);
    EXPECT_EQ(game.catAt(0, 0), nullptr);
}

TEST(BoxerStats, OneTreatOverLeavesOne) {
    Config config = quietConfig();
    config.startingTreats = 26;
    Game game(config, {kNever});

    EXPECT_EQ(game.place(CatType::Boxer, 0, 0), PlaceResult::Ok);
    EXPECT_EQ(game.state().treats, 1);
}

TEST(BoxerStats, SameCellRulesAsOtherCats) {
    Game game(quietConfig(), {kNever});
    placeOk(game, CatType::Boxer, 0, 3);

    EXPECT_EQ(game.place(CatType::Sleepy, 0, 3), PlaceResult::CellOccupied);
    EXPECT_EQ(game.place(CatType::Boxer, 0, 3), PlaceResult::CellOccupied);
    EXPECT_EQ(game.place(CatType::Boxer, 5, 0), PlaceResult::OutOfBounds);
    EXPECT_EQ(game.place(CatType::Boxer, 0, 9), PlaceResult::OutOfBounds);
    EXPECT_EQ(game.state().treats, 975);
    EXPECT_EQ(game.state().cats.size(), 1u);
}

TEST(BoxerStats, RemoveGivesNoRefund) {
    Game game(quietConfig(), {kNever});
    placeOk(game, CatType::Boxer, 0, 3);

    EXPECT_TRUE(game.remove(0, 3));
    EXPECT_EQ(game.catAt(0, 3), nullptr);
    EXPECT_EQ(game.state().treats, 975);
}

TEST(BoxerStats, DoesNotHurtMutantsOutsideItsCell) {
    Game game(quietConfig(), {SpawnEvent{0, 0, MutantType::Runner}, kNever});
    placeOk(game, CatType::Boxer, 0, 0);

    tickTo(game, 81);
    const Mutant& m = onlyMutant(game);
    EXPECT_EQ(m.position, 9);
    EXPECT_EQ(m.health, 60);
    EXPECT_FALSE(m.ambushed);
    EXPECT_TRUE(game.state().hairballs.empty());
    EXPECT_NE(game.catAt(0, 0), nullptr);
}

// ---- The ambush ---------------------------------------------------------------

TEST(BoxerAmbush, RunnerIsAmbushedAndStunned) {
    Game game = boxerAt8(quietConfig(), MutantType::Runner);

    tickTo(game, 1);  // entered cell 8 this tick; not processed there yet
    ASSERT_NE(game.catAt(0, 8), nullptr);
    EXPECT_EQ(onlyMutant(game).position, 89);
    EXPECT_EQ(onlyMutant(game).health, 60);
    EXPECT_EQ(onlyMutant(game).stunTicks, 0);
    EXPECT_FALSE(onlyMutant(game).ambushed);

    tickTo(game, 2);
    EXPECT_EQ(game.catAt(0, 8), nullptr);
    const Mutant& m = onlyMutant(game);
    EXPECT_EQ(m.position, 89);
    EXPECT_EQ(m.health, 20);
    EXPECT_EQ(m.stunTicks, 49);
    EXPECT_TRUE(m.ambushed);
}

TEST(BoxerAmbush, AmbushCanKillAndWinsOnThatTick) {
    Config config = quietConfig();
    config.ambushDamage = 60;
    Game game = boxerAt8(config, MutantType::Runner, /*keepRunning=*/false);

    tickTo(game, 2);
    EXPECT_TRUE(game.state().mutants.empty());
    EXPECT_EQ(game.status(), Status::Won);
    EXPECT_EQ(game.state().tick, 2);
    EXPECT_EQ(game.catAt(0, 8), nullptr);
}

TEST(BoxerAmbush, AmbushOneShortOfLethalLeavesOneHealth) {
    Config config = quietConfig();
    config.ambushDamage = 59;
    Game game = boxerAt8(config, MutantType::Runner, /*keepRunning=*/false);

    tickTo(game, 2);
    EXPECT_EQ(game.status(), Status::Playing);
    EXPECT_EQ(onlyMutant(game).health, 1);
}

TEST(BoxerAmbush, CustomAmbushDamageIsUsed) {
    Config config = quietConfig();
    config.ambushDamage = 15;
    Game game = boxerAt8(config, MutantType::Runner);

    tickTo(game, 2);
    EXPECT_EQ(onlyMutant(game).health, 45);
}

TEST(BoxerAmbush, MutantKilledByHairballEarlierInTickDoesNotSpringIt) {
    Config config = quietConfig();
    config.hissing = {100, 60, 2};
    config.hairballSpeed = 79;
    config.hairballDamage = 60;
    Game game(config, {SpawnEvent{0, 0, MutantType::Runner}});
    placeOk(game, CatType::Hissing, 0, 0);
    placeOk(game, CatType::Boxer, 0, 8);

    tickTo(game, 2);
    EXPECT_TRUE(game.state().mutants.empty());
    ASSERT_NE(game.catAt(0, 8), nullptr);
    EXPECT_EQ(game.catAt(0, 8)->type, CatType::Boxer);
    EXPECT_EQ(game.catAt(0, 8)->health, 20);
}

TEST(BoxerAmbush, MutantSurvivingTheHairballStillSpringsIt) {
    Config config = quietConfig();
    config.hissing = {100, 60, 2};
    config.hairballSpeed = 79;
    config.hairballDamage = 59;  // Runner left on 1 health going into step 6
    Game game(config, {SpawnEvent{0, 0, MutantType::Runner}, kNever});
    placeOk(game, CatType::Hissing, 0, 0);
    placeOk(game, CatType::Boxer, 0, 8);

    tickTo(game, 2);
    EXPECT_TRUE(game.state().mutants.empty());
    EXPECT_EQ(game.catAt(0, 8), nullptr);
}

TEST(BoxerAmbush, EquivalentNeverTriggersIt) {
    Game game = boxerAt8(quietConfig(), MutantType::Equivalent);

    auto expectUntouched = [&](int tick) {
        const Mutant& m = onlyMutant(game);
        EXPECT_EQ(m.health, 1) << "tick " << tick;
        EXPECT_EQ(m.stunTicks, 0) << "tick " << tick;
        EXPECT_FALSE(m.ambushed) << "tick " << tick;
    };

    tickTo(game, 2);
    EXPECT_EQ(onlyMutant(game).position, 89);
    tickTo(game, 3);
    EXPECT_EQ(onlyMutant(game).position, 89);
    ASSERT_NE(game.catAt(0, 8), nullptr);
    EXPECT_EQ(game.catAt(0, 8)->health, 20);
    expectUntouched(3);

    tickTo(game, 10);
    ASSERT_NE(game.catAt(0, 8), nullptr);
    EXPECT_EQ(game.catAt(0, 8)->health, 20);
    tickTo(game, 11);
    ASSERT_NE(game.catAt(0, 8), nullptr);
    EXPECT_EQ(game.catAt(0, 8)->health, 10);
    tickTo(game, 20);
    ASSERT_NE(game.catAt(0, 8), nullptr);
    EXPECT_EQ(game.catAt(0, 8)->health, 10);
    expectUntouched(20);

    tickTo(game, 21);
    EXPECT_EQ(game.catAt(0, 8), nullptr);
    EXPECT_EQ(onlyMutant(game).position, 89);
    tickTo(game, 22);
    EXPECT_EQ(onlyMutant(game).position, 89);
    tickTo(game, 23);
    EXPECT_EQ(onlyMutant(game).position, 88);
    expectUntouched(23);
}

TEST(BoxerAmbush, PlacedOnAWalkingMutant) {
    Game game(quietConfig(), {SpawnEvent{0, 0, MutantType::Runner}, kNever});
    tickTo(game, 5);
    ASSERT_EQ(onlyMutant(game).position, 85);
    placeOk(game, CatType::Boxer, 0, 8);

    game.tick();
    EXPECT_EQ(game.state().tick, 6);
    const Mutant& m = onlyMutant(game);
    EXPECT_EQ(m.position, 85);
    EXPECT_EQ(m.health, 20);
    EXPECT_EQ(m.stunTicks, 49);
    EXPECT_EQ(game.catAt(0, 8), nullptr);
}

TEST(BoxerAmbush, AmbushResetsMoveCooldown) {
    // A Blob steps on even ticks. After tick 5 it is at 88 with one tick left on its cooldown.
    Game game(quietConfig(), {SpawnEvent{0, 0, MutantType::Blob}, kNever});
    tickTo(game, 5);
    ASSERT_EQ(onlyMutant(game).position, 88);
    ASSERT_EQ(onlyMutant(game).moveCooldown, 1);
    placeOk(game, CatType::Boxer, 0, 8);

    tickTo(game, 6);  // ambush
    EXPECT_EQ(onlyMutant(game).moveCooldown, 2);
    EXPECT_EQ(onlyMutant(game).stunTicks, 49);
    tickTo(game, 55);  // last stunned tick
    EXPECT_EQ(onlyMutant(game).position, 88);
    tickTo(game, 56);  // T + 50 + 2 - 1 = 57 is the first step, not 56
    EXPECT_EQ(onlyMutant(game).position, 88);
    tickTo(game, 57);
    EXPECT_EQ(onlyMutant(game).position, 87);
}

TEST(BoxerAmbush, RemovingTheBoxWithAMutantInItsCellNeverAmbushes) {
    Game game = boxerAt8(quietConfig(), MutantType::Runner);
    tickTo(game, 1);
    ASSERT_EQ(onlyMutant(game).position, 89);

    EXPECT_TRUE(game.remove(0, 8));
    EXPECT_EQ(onlyMutant(game).health, 60);
    EXPECT_FALSE(onlyMutant(game).ambushed);

    tickTo(game, 2);
    const Mutant& m = onlyMutant(game);
    EXPECT_EQ(m.position, 88);
    EXPECT_EQ(m.health, 60);
    EXPECT_EQ(m.stunTicks, 0);
    EXPECT_FALSE(m.ambushed);
}

TEST(BoxerAmbush, RemovedBeforeArrivalDoesNothing) {
    Game game = boxerAt8(quietConfig(), MutantType::Runner);
    ASSERT_TRUE(game.remove(0, 8));

    tickTo(game, 2);
    EXPECT_EQ(onlyMutant(game).position, 88);
    EXPECT_EQ(onlyMutant(game).health, 60);
    EXPECT_FALSE(onlyMutant(game).ambushed);
}

TEST(BoxerAmbush, OnlyItsOwnLane) {
    Game game(quietConfig(), {SpawnEvent{0, 0, MutantType::Runner},
                              SpawnEvent{0, 2, MutantType::Runner}, kNever});
    placeOk(game, CatType::Boxer, 0, 8);
    placeOk(game, CatType::Boxer, 1, 8);

    tickTo(game, 2);
    EXPECT_EQ(game.catAt(0, 8), nullptr);
    ASSERT_NE(game.catAt(1, 8), nullptr);
    EXPECT_EQ(game.catAt(1, 8)->health, 20);

    ASSERT_EQ(game.state().mutants.size(), 2u);
    const Mutant& lane0 = game.state().mutants[0];
    const Mutant& lane2 = game.state().mutants[1];
    ASSERT_EQ(lane0.lane, 0);
    ASSERT_EQ(lane2.lane, 2);
    EXPECT_TRUE(lane0.ambushed);
    EXPECT_EQ(lane2.position, 88);
    EXPECT_EQ(lane2.health, 60);
    EXPECT_EQ(lane2.stunTicks, 0);
    EXPECT_FALSE(lane2.ambushed);
}

TEST(BoxerAmbush, AlreadyAmbushedMutantTreatsNextBoxAsAWall) {
    Game game(quietConfig(), {SpawnEvent{0, 0, MutantType::Runner}, kNever});
    placeOk(game, CatType::Boxer, 0, 8);
    placeOk(game, CatType::Boxer, 0, 7);

    auto box7Health = [&]() {
        const Cat* cat = game.catAt(0, 7);
        return cat == nullptr ? -1 : cat->health;
    };
    auto expectRunner = [&](int tick, int position) {
        const Mutant& m = onlyMutant(game);
        EXPECT_EQ(m.position, position) << "tick " << tick;
        EXPECT_EQ(m.health, 20) << "tick " << tick;
        EXPECT_EQ(m.stunTicks, 0) << "tick " << tick;
        EXPECT_TRUE(m.ambushed) << "tick " << tick;
    };

    tickTo(game, 2);
    EXPECT_EQ(game.catAt(0, 8), nullptr);
    EXPECT_EQ(box7Health(), 20);  // only the box in the mutant's own cell is used up

    tickTo(game, 60);
    expectRunner(60, 80);
    tickTo(game, 61);  // enters cell 7 this tick
    expectRunner(61, 79);
    EXPECT_EQ(box7Health(), 20);
    tickTo(game, 62);  // processed in cell 7: blocked, not ambushed
    expectRunner(62, 79);
    EXPECT_EQ(box7Health(), 20);

    tickTo(game, 69);  // spec AC7: "Boxer Cat health 20 after tick 69"
    EXPECT_EQ(box7Health(), 20);
    tickTo(game, 70);
    EXPECT_EQ(box7Health(), 10);
    expectRunner(70, 79);
    tickTo(game, 79);
    EXPECT_EQ(box7Health(), 10);
    tickTo(game, 80);
    EXPECT_EQ(box7Health(), -1);
    expectRunner(80, 79);
    tickTo(game, 81);
    expectRunner(81, 78);
}

TEST(BoxerAmbush, StunnedMutantIgnoresBoxPlacedOnItsCell) {
    Game game = boxerAt8(quietConfig(), MutantType::Runner);
    tickTo(game, 2);
    ASSERT_EQ(onlyMutant(game).stunTicks, 49);
    placeOk(game, CatType::Boxer, 0, 8);

    tickTo(game, 51);
    ASSERT_NE(game.catAt(0, 8), nullptr);
    EXPECT_EQ(game.catAt(0, 8)->health, 20);
    tickTo(game, 52);  // stun over: blocked by the box, bite timer starts
    ASSERT_NE(game.catAt(0, 8), nullptr);
    EXPECT_EQ(onlyMutant(game).stunTicks, 0);
    tickTo(game, 60);
    ASSERT_NE(game.catAt(0, 8), nullptr);
    EXPECT_EQ(game.catAt(0, 8)->health, 20);
    tickTo(game, 61);
    ASSERT_NE(game.catAt(0, 8), nullptr);
    EXPECT_EQ(game.catAt(0, 8)->health, 10);
    tickTo(game, 71);
    EXPECT_EQ(game.catAt(0, 8), nullptr);
    EXPECT_EQ(onlyMutant(game).position, 89);
    tickTo(game, 72);
    const Mutant& m = onlyMutant(game);
    EXPECT_EQ(m.position, 88);
    EXPECT_EQ(m.health, 20);
    EXPECT_EQ(m.stunTicks, 0);
}

TEST(BoxerAmbush, SameInputsSameState) {
    auto run = []() {
        Game game(quietConfig(), {SpawnEvent{0, 0, MutantType::Runner},
                                  SpawnEvent{0, 0, MutantType::Hopper}, kNever});
        placeOk(game, CatType::Boxer, 0, 8);
        placeOk(game, CatType::Boxer, 0, 7);
        tickN(game, 100);
        return game.state();
    };
    EXPECT_EQ(run(), run());
}

// ---- The stun -------------------------------------------------------------------

TEST(BoxerStun, RunnerStunLength) {
    Game game = boxerAt8(quietConfig(), MutantType::Runner);

    tickTo(game, 50);
    EXPECT_EQ(onlyMutant(game).stunTicks, 1);
    EXPECT_EQ(onlyMutant(game).position, 89);
    tickTo(game, 51);  // last stunned tick
    EXPECT_EQ(onlyMutant(game).stunTicks, 0);
    EXPECT_EQ(onlyMutant(game).position, 89);
    tickTo(game, 52);  // T + 50 + 1 - 1
    EXPECT_EQ(onlyMutant(game).position, 88);
    tickTo(game, 53);
    EXPECT_EQ(onlyMutant(game).position, 87);
}

TEST(BoxerStun, BlobStunLength) {
    Game game = boxerAt8(quietConfig(), MutantType::Blob);

    tickTo(game, 2);
    EXPECT_EQ(onlyMutant(game).position, 89);
    EXPECT_EQ(onlyMutant(game).health, 100);
    EXPECT_NE(game.catAt(0, 8), nullptr);

    tickTo(game, 3);
    EXPECT_EQ(onlyMutant(game).health, 60);
    EXPECT_EQ(onlyMutant(game).stunTicks, 49);
    EXPECT_EQ(onlyMutant(game).moveCooldown, 2);
    EXPECT_EQ(game.catAt(0, 8), nullptr);

    tickTo(game, 52);  // last stunned tick: cooldown frozen
    EXPECT_EQ(onlyMutant(game).moveCooldown, 2);
    EXPECT_EQ(onlyMutant(game).stunTicks, 0);
    tickTo(game, 53);
    EXPECT_EQ(onlyMutant(game).position, 89);
    tickTo(game, 54);  // T + 50 + 2 - 1
    EXPECT_EQ(onlyMutant(game).position, 88);
}

TEST(BoxerStun, BruteStunLength) {
    Game game = boxerAt8(quietConfig(), MutantType::Brute);

    tickTo(game, 3);
    EXPECT_EQ(onlyMutant(game).position, 89);
    EXPECT_EQ(onlyMutant(game).health, 300);
    tickTo(game, 4);
    EXPECT_EQ(onlyMutant(game).health, 260);
    EXPECT_EQ(onlyMutant(game).stunTicks, 49);
    tickTo(game, 55);
    EXPECT_EQ(onlyMutant(game).position, 89);
    tickTo(game, 56);  // T + 50 + 3 - 1
    EXPECT_EQ(onlyMutant(game).position, 88);
}

TEST(BoxerStun, CustomStunDuration) {
    Config config = quietConfig();
    config.stunDuration = 5;
    Game game = boxerAt8(config, MutantType::Runner);

    tickTo(game, 2);
    EXPECT_EQ(onlyMutant(game).stunTicks, 4);
    tickTo(game, 6);  // last stunned tick, T + 5 - 1
    EXPECT_EQ(onlyMutant(game).position, 89);
    EXPECT_EQ(onlyMutant(game).stunTicks, 0);
    tickTo(game, 7);
    EXPECT_EQ(onlyMutant(game).position, 88);
}

TEST(BoxerStun, StunDurationOneMovesOnTheNextTick) {
    Config config = quietConfig();
    config.stunDuration = 1;
    Game game = boxerAt8(config, MutantType::Runner);

    tickTo(game, 2);
    EXPECT_EQ(onlyMutant(game).position, 89);
    EXPECT_EQ(onlyMutant(game).stunTicks, 0);
    EXPECT_TRUE(onlyMutant(game).ambushed);
    tickTo(game, 3);
    EXPECT_EQ(onlyMutant(game).position, 88);
}

TEST(BoxerStun, ZeroStunStillSkipsTheAmbushTick) {
    Config config = quietConfig();
    config.stunDuration = 0;
    Game game = boxerAt8(config, MutantType::Runner);

    tickTo(game, 2);
    const Mutant& m = onlyMutant(game);
    EXPECT_EQ(m.position, 89);
    EXPECT_EQ(m.health, 20);
    EXPECT_EQ(m.stunTicks, 0);
    EXPECT_TRUE(m.ambushed);
    EXPECT_EQ(game.catAt(0, 8), nullptr);

    tickTo(game, 3);  // T + moveInterval
    EXPECT_EQ(onlyMutant(game).position, 88);
    EXPECT_EQ(onlyMutant(game).stunTicks, 0);
    tickTo(game, 4);
    EXPECT_EQ(onlyMutant(game).position, 87);
    EXPECT_EQ(onlyMutant(game).stunTicks, 0);
}

TEST(BoxerStun, ZeroStunBlobFirstStepsAtTPlusInterval) {
    Config config = quietConfig();
    config.stunDuration = 0;
    Game game = boxerAt8(config, MutantType::Blob);

    tickTo(game, 3);
    EXPECT_TRUE(onlyMutant(game).ambushed);
    EXPECT_EQ(onlyMutant(game).position, 89);
    tickTo(game, 4);
    EXPECT_EQ(onlyMutant(game).position, 89);
    tickTo(game, 5);  // 3 + 2
    EXPECT_EQ(onlyMutant(game).position, 88);
}

TEST(BoxerStun, StunnedMutantDoesNotBiteAndTimerRestarts) {
    // The Runner entered cell 8 on tick 1 while the box was there, so its bite timer read 9
    // going into the ambush. The stun must put it back to 10.
    Game game = boxerAt8(quietConfig(), MutantType::Runner);
    tickTo(game, 2);
    EXPECT_EQ(onlyMutant(game).biteCooldown, 10);
    placeOk(game, CatType::Sleepy, 0, 8);

    tickTo(game, 51);
    ASSERT_NE(game.catAt(0, 8), nullptr);
    EXPECT_EQ(game.catAt(0, 8)->health, 300);
    EXPECT_EQ(onlyMutant(game).biteCooldown, 10);
    tickTo(game, 60);
    ASSERT_NE(game.catAt(0, 8), nullptr);
    EXPECT_EQ(game.catAt(0, 8)->health, 300);
    EXPECT_EQ(onlyMutant(game).position, 89);
    tickTo(game, 61);  // T + 50 + 10 - 1
    ASSERT_NE(game.catAt(0, 8), nullptr);
    EXPECT_EQ(game.catAt(0, 8)->health, 290);
    EXPECT_EQ(onlyMutant(game).position, 89);
}

TEST(BoxerStun, StunnedMutantStillTakesHairballs) {
    Config config = quietConfig();
    config.hissing = {100, 60, 10};
    config.hairballSpeed = 79;
    Game game = boxerAt8(config, MutantType::Runner);
    tickTo(game, 2);
    placeOk(game, CatType::Hissing, 0, 0);

    tickTo(game, 11);
    EXPECT_EQ(onlyMutant(game).health, 20);
    EXPECT_EQ(onlyMutant(game).stunTicks, 40);
    tickTo(game, 12);
    EXPECT_TRUE(game.state().mutants.empty());
}

TEST(BoxerStun, StunnedMutantStillTakesLaser) {
    Game game = boxerAt8(quietConfig(), MutantType::Runner);
    tickTo(game, 2);
    placeOk(game, CatType::Laser, 0, 4);

    tickTo(game, 31);
    EXPECT_EQ(onlyMutant(game).health, 20);
    tickTo(game, 32);
    EXPECT_TRUE(game.state().mutants.empty());
}

TEST(BoxerStun, StunnedMutantCountsForWinCheck) {
    Game game = boxerAt8(quietConfig(), MutantType::Runner, /*keepRunning=*/false);

    tickTo(game, 51);
    EXPECT_EQ(game.status(), Status::Playing);
    EXPECT_EQ(game.state().tick, 51);
    EXPECT_EQ(game.state().mutants.size(), 1u);
}

// ---- Several mutants in one cell, vector order ----------------------------------

TEST(BoxerOrder, SecondRunnerInCellWalksOn) {
    Game game(quietConfig(), {SpawnEvent{0, 0, MutantType::Runner},
                              SpawnEvent{0, 0, MutantType::Runner}, kNever});
    placeOk(game, CatType::Boxer, 0, 8);

    tickTo(game, 2);
    ASSERT_EQ(game.state().mutants.size(), 2u);
    const Mutant& first = game.state().mutants[0];
    const Mutant& second = game.state().mutants[1];
    EXPECT_EQ(first.position, 89);
    EXPECT_EQ(first.health, 20);
    EXPECT_EQ(first.stunTicks, 49);
    EXPECT_TRUE(first.ambushed);
    EXPECT_EQ(second.position, 88);
    EXPECT_EQ(second.health, 60);
    EXPECT_EQ(second.stunTicks, 0);
    EXPECT_FALSE(second.ambushed);
    EXPECT_EQ(game.catAt(0, 8), nullptr);
}

TEST(BoxerOrder, ThreeInCellOnlyFirstIsAmbushed) {
    Game game(quietConfig(), {SpawnEvent{0, 0, MutantType::Runner},
                              SpawnEvent{0, 0, MutantType::Runner},
                              SpawnEvent{0, 0, MutantType::Runner}, kNever});
    placeOk(game, CatType::Boxer, 0, 8);

    tickTo(game, 2);
    ASSERT_EQ(game.state().mutants.size(), 3u);
    EXPECT_TRUE(game.state().mutants[0].ambushed);
    EXPECT_EQ(game.state().mutants[0].health, 20);
    for (int i : {1, 2}) {
        const Mutant& m = game.state().mutants[static_cast<std::size_t>(i)];
        EXPECT_EQ(m.position, 88) << "mutant " << i;
        EXPECT_EQ(m.health, 60) << "mutant " << i;
        EXPECT_FALSE(m.ambushed) << "mutant " << i;
    }
}

TEST(BoxerOrder, EarlierEquivalentDoesNotUseUpTheBox) {
    Game game(quietConfig(), {SpawnEvent{0, 0, MutantType::Equivalent},
                              SpawnEvent{2, 0, MutantType::Runner}, kNever});
    placeOk(game, CatType::Boxer, 0, 8);

    tickTo(game, 2);
    ASSERT_EQ(game.state().mutants.size(), 2u);
    ASSERT_EQ(game.state().mutants[0].type, MutantType::Equivalent);
    ASSERT_EQ(game.state().mutants[1].type, MutantType::Runner);
    EXPECT_EQ(game.state().mutants[0].position, 89);
    EXPECT_EQ(game.state().mutants[1].position, 89);
    EXPECT_NE(game.catAt(0, 8), nullptr);

    tickTo(game, 3);
    EXPECT_EQ(game.catAt(0, 8), nullptr);
    const Mutant& equivalent = game.state().mutants[0];
    const Mutant& runner = game.state().mutants[1];
    EXPECT_EQ(runner.position, 89);
    EXPECT_EQ(runner.health, 20);
    EXPECT_EQ(runner.stunTicks, 49);
    EXPECT_TRUE(runner.ambushed);
    EXPECT_EQ(equivalent.position, 89);
    EXPECT_EQ(equivalent.stunTicks, 0);
    EXPECT_FALSE(equivalent.ambushed);

    tickTo(game, 4);
    EXPECT_EQ(game.state().mutants[0].position, 89);
    tickTo(game, 5);
    EXPECT_EQ(game.state().mutants[0].position, 88);
}

TEST(BoxerOrder, EarlierSpawnedMutantIsAmbushedFirst) {
    // Both stand at 89 going into tick 3. The Blob is first in vector order.
    Game game(quietConfig(), {SpawnEvent{0, 0, MutantType::Blob},
                              SpawnEvent{2, 0, MutantType::Runner}, kNever});
    placeOk(game, CatType::Boxer, 0, 8);

    tickTo(game, 2);
    ASSERT_EQ(game.state().mutants.size(), 2u);
    EXPECT_EQ(game.state().mutants[0].position, 89);
    EXPECT_EQ(game.state().mutants[1].position, 89);

    tickTo(game, 3);
    const Mutant& blob = game.state().mutants[0];
    const Mutant& runner = game.state().mutants[1];
    ASSERT_EQ(blob.type, MutantType::Blob);
    EXPECT_EQ(blob.health, 60);
    EXPECT_EQ(blob.stunTicks, 49);
    EXPECT_TRUE(blob.ambushed);
    EXPECT_EQ(runner.position, 88);
    EXPECT_EQ(runner.health, 60);
    EXPECT_FALSE(runner.ambushed);
}

// ---- Hopper ---------------------------------------------------------------------

TEST(BoxerHopper, AmbushedHopperKeepsItsJump) {
    Game game(quietConfig(), {SpawnEvent{0, 0, MutantType::Hopper}, kNever});
    placeOk(game, CatType::Boxer, 0, 8);
    placeOk(game, CatType::Sleepy, 0, 5);

    tickTo(game, 3);
    EXPECT_EQ(onlyMutant(game).position, 89);  // not 79
    EXPECT_EQ(onlyMutant(game).health, 40);
    EXPECT_FALSE(onlyMutant(game).hasJumped);
    EXPECT_TRUE(onlyMutant(game).ambushed);

    tickTo(game, 111);
    EXPECT_EQ(onlyMutant(game).position, 60);
    tickTo(game, 112);
    EXPECT_EQ(onlyMutant(game).position, 59);
    EXPECT_FALSE(onlyMutant(game).hasJumped);
    tickTo(game, 113);
    EXPECT_EQ(onlyMutant(game).position, 49);
    EXPECT_TRUE(onlyMutant(game).hasJumped);
    EXPECT_NE(game.catAt(0, 5), nullptr);
}

TEST(BoxerHopper, JumpedHopperIsStillEligible) {
    Game game(quietConfig(), {SpawnEvent{0, 0, MutantType::Hopper}, kNever});
    placeOk(game, CatType::Sleepy, 0, 8);
    placeOk(game, CatType::Boxer, 0, 7);

    tickTo(game, 3);
    EXPECT_EQ(onlyMutant(game).position, 79);
    EXPECT_TRUE(onlyMutant(game).hasJumped);
    EXPECT_FALSE(onlyMutant(game).ambushed);
    EXPECT_NE(game.catAt(0, 7), nullptr);

    tickTo(game, 4);
    EXPECT_EQ(onlyMutant(game).position, 79);
    EXPECT_EQ(onlyMutant(game).health, 40);
    EXPECT_EQ(onlyMutant(game).stunTicks, 49);
    EXPECT_TRUE(onlyMutant(game).ambushed);
    EXPECT_EQ(game.catAt(0, 7), nullptr);
}

TEST(BoxerHopper, StunnedHopperDoesNotJump) {
    Game game = boxerAt8(quietConfig(), MutantType::Hopper);
    tickTo(game, 3);
    ASSERT_TRUE(onlyMutant(game).ambushed);
    placeOk(game, CatType::Sleepy, 0, 8);

    tickTo(game, 52);  // last stunned tick
    EXPECT_EQ(onlyMutant(game).position, 89);
    EXPECT_FALSE(onlyMutant(game).hasJumped);
    tickTo(game, 53);
    EXPECT_EQ(onlyMutant(game).position, 79);
    EXPECT_TRUE(onlyMutant(game).hasJumped);
}

// ---- Boundaries -----------------------------------------------------------------

TEST(BoxerBoundary, ColumnZero) {
    Game game(quietConfig(), {SpawnEvent{0, 0, MutantType::Runner}, kNever});
    placeOk(game, CatType::Boxer, 0, 0);

    tickTo(game, 81);
    EXPECT_EQ(onlyMutant(game).position, 9);
    EXPECT_NE(game.catAt(0, 0), nullptr);
    tickTo(game, 82);
    EXPECT_EQ(onlyMutant(game).position, 9);
    EXPECT_EQ(onlyMutant(game).health, 20);
    EXPECT_EQ(onlyMutant(game).stunTicks, 49);
    EXPECT_EQ(game.catAt(0, 0), nullptr);

    tickTo(game, 131);  // last stunned tick
    EXPECT_EQ(onlyMutant(game).position, 9);
    EXPECT_EQ(game.state().lives, 3);
    tickTo(game, 132);
    EXPECT_EQ(onlyMutant(game).position, 8);
    tickTo(game, 140);
    EXPECT_EQ(onlyMutant(game).position, 0);
    EXPECT_EQ(game.state().lives, 3);
    tickTo(game, 141);
    EXPECT_TRUE(game.state().mutants.empty());
    EXPECT_EQ(game.state().lives, 2);
}

TEST(BoxerBoundary, GameOverFreezesStun) {
    Config config = quietConfig();
    config.startingLives = 1;
    config.stunDuration = 100;
    Game game(config, {SpawnEvent{0, 0, MutantType::Runner},
                       SpawnEvent{0, 1, MutantType::Runner}, kNever});
    placeOk(game, CatType::Boxer, 0, 8);

    tickTo(game, 90);
    ASSERT_EQ(game.status(), Status::Playing);
    tickTo(game, 91);  // lane-1 Runner reaches home
    ASSERT_EQ(game.status(), Status::Lost);
    ASSERT_EQ(game.state().tick, 91);
    const Mutant& stunned = onlyMutant(game);
    EXPECT_EQ(stunned.lane, 0);
    EXPECT_EQ(stunned.stunTicks, 10);

    const GameState snapshot = game.state();
    tickN(game, 20);
    EXPECT_EQ(game.state(), snapshot);
    EXPECT_EQ(onlyMutant(game).stunTicks, 10);
}

}  // namespace cvm::test
