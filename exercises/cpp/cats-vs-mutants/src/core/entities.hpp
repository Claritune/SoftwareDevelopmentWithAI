#pragma once

#include <cstddef>
#include <vector>

#include "config.hpp"

namespace cvm {

enum class Status { Playing, Won, Lost };
enum class PlaceResult { Ok, CellOccupied, NotEnoughTreats, OutOfBounds, GameOver };

struct Cat {
    CatType type;
    int lane;
    int col;
    int health;
    int cooldown;  // ticks until the next action (Rich, Hissing, Laser)

    bool operator==(const Cat&) const = default;
};

struct Mutant {
    MutantType type;
    int lane;
    int position;      // steps from home; cell is position / cellSize
    int health;
    int moveCooldown;  // ticks until the next step
    int biteCooldown;  // ticks until the next bite while blocked
    bool hasJumped;    // Hopper only: true once it has used its jump

    bool operator==(const Mutant&) const = default;
};

struct Hairball {
    int lane;
    int position;
    int originCol;  // cell of the cat that spat it; mutants left of it are never hit

    bool operator==(const Hairball&) const = default;
};

struct SpawnEvent {
    int tick;
    int lane;
    MutantType type;
    int wave = 1;

    bool operator==(const SpawnEvent&) const = default;
};

struct GameState {
    int tick = 0;
    int treats = 0;
    int lives = 0;
    Status status = Status::Playing;
    std::vector<Cat> cats;
    std::vector<Mutant> mutants;
    std::vector<Hairball> hairballs;
    std::size_t nextSpawn = 0;  // index of the next unspawned wave event

    bool operator==(const GameState&) const = default;
};

}  // namespace cvm
