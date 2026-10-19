#include <gtest/gtest.h>

#include "game.hpp"
#include "waves.hpp"

using namespace cvm;

TEST(Smoke, PlaceCatAndRunTicks) {
    Game game(Config{}, defaultWaves());

    ASSERT_EQ(game.place(CatType::Rich, 0, 0), PlaceResult::Ok);
    EXPECT_EQ(game.state().treats, 100);
    ASSERT_EQ(game.state().cats.size(), 1u);

    for (int i = 0; i < 5; ++i) game.tick();

    EXPECT_EQ(game.state().tick, 5);
    EXPECT_EQ(game.status(), Status::Playing);
}
