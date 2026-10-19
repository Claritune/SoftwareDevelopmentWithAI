#pragma once

#include <gtest/gtest.h>

#include <vector>

#include "game.hpp"

namespace cvm::test {

// A spawn far in the future: keeps the game from being won while a test runs.
inline constexpr SpawnEvent kNever{1'000'000, 4, MutantType::Blob, 1};

// Plenty of treats and no passive income, so rules can be tested in isolation.
inline Config quietConfig() {
    Config c;
    c.startingTreats = 1000;
    c.passiveIncomeInterval = 1'000'000;
    return c;
}

inline void tickN(Game& game, int n) {
    for (int i = 0; i < n; ++i) game.tick();
}

// Ticks until the tick counter reads `tick`.
inline void tickTo(Game& game, int tick) {
    while (game.state().tick < tick && game.status() == Status::Playing) game.tick();
}

inline const Mutant& onlyMutant(const Game& game) {
    EXPECT_EQ(game.state().mutants.size(), 1u);
    return game.state().mutants.front();
}

}  // namespace cvm::test
