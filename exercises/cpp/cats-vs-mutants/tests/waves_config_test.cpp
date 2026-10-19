#include <gtest/gtest.h>

#include <algorithm>

#include "test_helpers.hpp"
#include "waves.hpp"

using namespace cvm;
using namespace cvm::test;

namespace {

int firstWaveOf(const std::vector<SpawnEvent>& waves, MutantType type) {
    for (const SpawnEvent& e : waves) {
        if (e.type == type) return e.wave;
    }
    return 0;
}

}  // namespace

// ---- Shipped wave data ------------------------------------------------------

TEST(DefaultWaves, AreSortedByTick) {
    const auto waves = defaultWaves();
    ASSERT_FALSE(waves.empty());
    EXPECT_TRUE(std::is_sorted(waves.begin(), waves.end(),
                               [](const SpawnEvent& a, const SpawnEvent& b) { return a.tick < b.tick; }));
}

TEST(DefaultWaves, ThreeWavesInOrder) {
    const auto waves = defaultWaves();
    EXPECT_EQ(waves.front().wave, 1);
    EXPECT_EQ(waves.back().wave, 3);
    EXPECT_TRUE(std::is_sorted(waves.begin(), waves.end(),
                               [](const SpawnEvent& a, const SpawnEvent& b) { return a.wave < b.wave; }));
}

TEST(DefaultWaves, SpawnInValidLanesAfterTickZero) {
    const Config config;
    for (const SpawnEvent& e : defaultWaves()) {
        EXPECT_GE(e.lane, 0);
        EXPECT_LT(e.lane, config.lanes);
        EXPECT_GT(e.tick, 0);
    }
}

TEST(DefaultWaves, EachWaveLastsRoughlyThirtySeconds) {
    const auto waves = defaultWaves();
    for (int wave = 1; wave <= 3; ++wave) {
        int first = -1;
        int last = -1;
        for (const SpawnEvent& e : waves) {
            if (e.wave != wave) continue;
            if (first < 0) first = e.tick;
            last = e.tick;
        }
        ASSERT_GE(first, 0) << "wave " << wave << " is empty";
        EXPECT_LE(last - first, 300) << "wave " << wave;
    }
}

TEST(DefaultWaves, IntroduceMutantsInTheRightWave) {
    const auto waves = defaultWaves();
    EXPECT_EQ(firstWaveOf(waves, MutantType::Blob), 1);
    EXPECT_EQ(firstWaveOf(waves, MutantType::Runner), 2);
    EXPECT_EQ(firstWaveOf(waves, MutantType::Brute), 3);
    EXPECT_EQ(firstWaveOf(waves, MutantType::Hopper), 3);
}

TEST(DefaultWaves, ContainExactlyOneEquivalentMutant) {
    const auto waves = defaultWaves();
    EXPECT_EQ(std::count_if(waves.begin(), waves.end(),
                            [](const SpawnEvent& e) { return e.type == MutantType::Equivalent; }),
              1);
}

TEST(DefaultWaves, GetHarder) {
    const auto waves = defaultWaves();
    auto count = [&](int wave) {
        return std::count_if(waves.begin(), waves.end(),
                             [wave](const SpawnEvent& e) { return e.wave == wave; });
    };
    EXPECT_LT(count(1), count(2));
    EXPECT_LT(count(2), count(3));
}

// ---- Wave progress ----------------------------------------------------------

TEST(WaveProgress, CurrentWaveFollowsSpawns) {
    Game game(quietConfig(), {SpawnEvent{5, 0, MutantType::Brute, 1},
                              SpawnEvent{10, 1, MutantType::Brute, 2},
                              SpawnEvent{1'000'000, 2, MutantType::Brute, 3}});
    EXPECT_EQ(game.totalWaves(), 3);
    EXPECT_EQ(game.currentWave(), 1);
    tickTo(game, 9);
    EXPECT_EQ(game.currentWave(), 1);
    tickTo(game, 10);
    EXPECT_EQ(game.currentWave(), 2);
}

TEST(WaveProgress, CurrentWaveBeforeAnySpawnIsTheFirstEventsWave) {
    Game game(quietConfig(), {SpawnEvent{5, 0, MutantType::Brute, 2}});
    EXPECT_EQ(game.currentWave(), 2);
}

TEST(WaveProgress, NoWaves) {
    Game game(quietConfig(), {});
    EXPECT_EQ(game.currentWave(), 0);
    EXPECT_EQ(game.totalWaves(), 0);
}

TEST(WaveProgress, DefaultGameHasThreeWaves) {
    Game game(Config{}, defaultWaves());
    EXPECT_EQ(game.totalWaves(), 3);
    EXPECT_EQ(game.currentWave(), 1);
}

// ---- Config -----------------------------------------------------------------

TEST(ConfigLookup, CatStatsByType) {
    const Config c;
    EXPECT_EQ(c.cat(CatType::Rich).cost, 50);
    EXPECT_EQ(c.cat(CatType::Hissing).cost, 100);
    EXPECT_EQ(c.cat(CatType::Sleepy).cost, 50);
    EXPECT_EQ(c.cat(CatType::Laser).cost, 175);
    EXPECT_EQ(c.cat(CatType::Rich).interval, 80);
    EXPECT_EQ(c.cat(CatType::Hissing).interval, 15);
    EXPECT_EQ(c.cat(CatType::Laser).interval, 30);
    EXPECT_EQ(c.cat(CatType::Sleepy).health, 300);
}

TEST(ConfigLookup, MutantStatsByType) {
    const Config c;
    EXPECT_EQ(c.mutant(MutantType::Blob).moveInterval, 2);
    EXPECT_EQ(c.mutant(MutantType::Runner).moveInterval, 1);
    EXPECT_EQ(c.mutant(MutantType::Brute).moveInterval, 3);
    EXPECT_EQ(c.mutant(MutantType::Hopper).health, 80);
    EXPECT_EQ(c.mutant(MutantType::Equivalent).health, 1);
}

TEST(ConfigLookup, SpawnPositionIsBoardWidthInSteps) {
    Config c;
    EXPECT_EQ(c.spawnPosition(), 90);
    c.cols = 4;
    c.cellSize = 3;
    EXPECT_EQ(c.spawnPosition(), 12);
}

TEST(ConfigLookup, CellOfUsesIntegerDivision) {
    Game game(Config{}, {kNever});
    EXPECT_EQ(game.cellOf(0), 0);
    EXPECT_EQ(game.cellOf(9), 0);
    EXPECT_EQ(game.cellOf(10), 1);
    EXPECT_EQ(game.cellOf(89), 8);
    EXPECT_EQ(game.cellOf(90), 9);
}
