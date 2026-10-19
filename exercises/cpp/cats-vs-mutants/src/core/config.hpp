#pragma once

#include <cstdint>

namespace cvm {

enum class CatType { Rich, Hissing, Sleepy, Laser };
enum class MutantType { Blob, Runner, Brute, Hopper, Equivalent };

struct CatStats {
    int cost;
    int health;
    int interval;  // ticks between actions; 0 means the cat never acts
};

struct MutantStats {
    int health;
    int moveInterval;  // ticks per step moved
};

// Every tunable number in the game. Tests can build custom configs.
struct Config {
    // Board
    int lanes = 5;
    int cols = 9;
    int cellSize = 10;  // steps per cell; mutants spawn at cols * cellSize

    // Economy and lives
    int startingTreats = 150;
    int passiveIncome = 25;
    int passiveIncomeInterval = 100;
    int startingLives = 3;

    // Cats
    CatStats rich{50, 40, 80};
    CatStats hissing{100, 60, 15};
    CatStats sleepy{50, 300, 0};
    CatStats laser{175, 60, 30};
    int richProduction = 25;
    int laserRange = 4;  // cells to the right of the cat's own cell
    int laserDamage = 30;

    // Hairballs
    int hairballSpeed = 5;
    int hairballDamage = 20;

    // Mutants
    MutantStats blob{100, 2};
    MutantStats runner{60, 1};
    MutantStats brute{300, 3};
    MutantStats hopper{80, 2};
    MutantStats equivalent{1, 2};
    int biteDamage = 10;
    int biteInterval = 10;

    // Reserved for any future randomness; core never uses std::random_device.
    std::uint32_t seed = 42;

    const CatStats& cat(CatType type) const {
        switch (type) {
            case CatType::Rich: return rich;
            case CatType::Hissing: return hissing;
            case CatType::Sleepy: return sleepy;
            case CatType::Laser: return laser;
        }
        return rich;
    }

    const MutantStats& mutant(MutantType type) const {
        switch (type) {
            case MutantType::Blob: return blob;
            case MutantType::Runner: return runner;
            case MutantType::Brute: return brute;
            case MutantType::Hopper: return hopper;
            case MutantType::Equivalent: return equivalent;
        }
        return blob;
    }

    int spawnPosition() const { return cols * cellSize; }
};

}  // namespace cvm
