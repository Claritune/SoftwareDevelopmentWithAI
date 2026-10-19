#pragma once

#include <vector>

#include "config.hpp"
#include "entities.hpp"

namespace cvm {

class Game {
public:
    Game(Config config, std::vector<SpawnEvent> waves);

    PlaceResult place(CatType type, int lane, int col);
    bool remove(int lane, int col);
    void tick();

    const GameState& state() const { return state_; }
    const Config& config() const { return config_; }
    Status status() const { return state_.status; }

    // Wave of the most recently spawned mutant (1 before any spawn).
    int currentWave() const;
    int totalWaves() const;

    const Cat* catAt(int lane, int col) const;
    int cellOf(int position) const { return position / config_.cellSize; }

private:
    // Tick steps, in the order tick() runs them.
    void produceResources();
    void spawnMutants();
    void fireCats();
    void moveHairballs();
    void resolveHits();
    void moveMutants();
    void resolveBites();
    void removeDead();
    void handleMutantsAtHome();
    void checkEndConditions();

    bool inBounds(int lane, int col) const;
    Cat* mutableCatAt(int lane, int col);
    bool anyMutantInRange(int lane, int fromCol, int toCol) const;
    void damage(Mutant& mutant, int amount) const;

    Config config_;
    std::vector<SpawnEvent> waves_;
    GameState state_;
};

}  // namespace cvm
