#include "game.hpp"

#include <algorithm>
#include <utility>

namespace cvm {

Game::Game(Config config, std::vector<SpawnEvent> waves)
    : config_(std::move(config)), waves_(std::move(waves)) {
    std::stable_sort(waves_.begin(), waves_.end(),
                     [](const SpawnEvent& a, const SpawnEvent& b) { return a.tick < b.tick; });
    state_.treats = config_.startingTreats;
    state_.lives = config_.startingLives;
}

PlaceResult Game::place(CatType type, int lane, int col) {
    if (state_.status != Status::Playing) return PlaceResult::GameOver;
    if (!inBounds(lane, col)) return PlaceResult::OutOfBounds;
    if (catAt(lane, col) != nullptr) return PlaceResult::CellOccupied;
    const CatStats& stats = config_.cat(type);
    if (stats.cost > state_.treats) return PlaceResult::NotEnoughTreats;

    state_.treats -= stats.cost;
    state_.cats.push_back(Cat{type, lane, col, stats.health, stats.interval});
    return PlaceResult::Ok;
}

bool Game::remove(int lane, int col) {
    if (state_.status != Status::Playing) return false;
    auto it = std::find_if(state_.cats.begin(), state_.cats.end(),
                           [&](const Cat& c) { return c.lane == lane && c.col == col; });
    if (it == state_.cats.end()) return false;
    state_.cats.erase(it);
    return true;
}

// One simulation step. The order of these steps is part of the game rules.
void Game::tick() {
    if (state_.status != Status::Playing) return;

    state_.tick++;          // 1. Increment tick counter
    produceResources();     // 2. Passive income and Rich Cat production
    spawnMutants();         // 3. Spawn mutants scheduled for this tick
    fireCats();             // 4. Cats fire (hairballs created, laser damage applied)
    moveHairballs();        // 5. Move hairballs...
    resolveHits();          //    ...and resolve hits
    moveMutants();          // 6. Move mutants (respecting blocking and Hopper jumps)
    resolveBites();         // 7. Resolve bites
    removeDead();           // 8. Remove dead cats and dead mutants
    handleMutantsAtHome();  // 9. Handle mutants reaching home
    checkEndConditions();   // 10. Check win and lose conditions
}

int Game::currentWave() const {
    if (state_.nextSpawn == 0) return waves_.empty() ? 0 : waves_.front().wave;
    return waves_[state_.nextSpawn - 1].wave;
}

int Game::totalWaves() const {
    int total = 0;
    for (const SpawnEvent& e : waves_) total = std::max(total, e.wave);
    return total;
}

void Game::produceResources() {
    if (state_.tick % config_.passiveIncomeInterval == 0) {
        state_.treats += config_.passiveIncome;
    }
    for (Cat& cat : state_.cats) {
        if (cat.type != CatType::Rich) continue;
        if (--cat.cooldown == 0) {
            cat.cooldown = config_.rich.interval;
            state_.treats += config_.richProduction;
        }
    }
}

void Game::spawnMutants() {
    while (state_.nextSpawn < waves_.size() && waves_[state_.nextSpawn].tick <= state_.tick) {
        const SpawnEvent& e = waves_[state_.nextSpawn++];
        const MutantStats& stats = config_.mutant(e.type);
        state_.mutants.push_back(Mutant{e.type, e.lane, config_.spawnPosition(), stats.health,
                                        stats.moveInterval, config_.biteInterval, false});
    }
}

void Game::fireCats() {
    for (Cat& cat : state_.cats) {
        if (cat.type != CatType::Hissing && cat.type != CatType::Laser) continue;
        if (--cat.cooldown != 0) continue;
        cat.cooldown = config_.cat(cat.type).interval;

        if (cat.type == CatType::Hissing) {
            if (anyMutantInRange(cat.lane, cat.col, config_.cols)) {
                state_.hairballs.push_back(
                    Hairball{cat.lane, (cat.col + 1) * config_.cellSize, cat.col});
            }
        } else {
            const int last = cat.col + config_.laserRange;
            if (!anyMutantInRange(cat.lane, cat.col, last)) continue;
            for (Mutant& m : state_.mutants) {
                const int cell = cellOf(m.position);
                if (m.lane == cat.lane && cell >= cat.col && cell <= last) {
                    damage(m, config_.laserDamage);
                }
            }
        }
    }
}

void Game::moveHairballs() {
    for (Hairball& h : state_.hairballs) h.position += config_.hairballSpeed;
}

void Game::resolveHits() {
    std::vector<Hairball> remaining;
    for (const Hairball& h : state_.hairballs) {
        // The first mutant the hairball reaches is the one closest to its origin.
        Mutant* target = nullptr;
        for (Mutant& m : state_.mutants) {
            if (m.lane != h.lane || m.health <= 0 || m.type == MutantType::Equivalent) continue;
            if (m.position > h.position || cellOf(m.position) < h.originCol) continue;
            if (target == nullptr || m.position < target->position) target = &m;
        }
        if (target != nullptr) {
            damage(*target, config_.hairballDamage);
        } else if (h.position <= config_.spawnPosition()) {
            remaining.push_back(h);
        }
    }
    state_.hairballs = std::move(remaining);
}

void Game::moveMutants() {
    for (Mutant& m : state_.mutants) {
        if (m.health <= 0) continue;
        const Cat* blocker = catAt(m.lane, cellOf(m.position));
        if (blocker != nullptr) {
            if (m.type == MutantType::Hopper && !m.hasJumped) {
                m.hasJumped = true;
                m.position = blocker->col * config_.cellSize - 1;
                m.moveCooldown = config_.hopper.moveInterval;
            }
            continue;
        }
        if (--m.moveCooldown == 0) {
            m.moveCooldown = config_.mutant(m.type).moveInterval;
            m.position--;
        }
    }
}

void Game::resolveBites() {
    for (Mutant& m : state_.mutants) {
        if (m.health <= 0) continue;
        Cat* cat = mutableCatAt(m.lane, cellOf(m.position));
        if (cat == nullptr) {
            m.biteCooldown = config_.biteInterval;
            continue;
        }
        if (--m.biteCooldown == 0) {
            m.biteCooldown = config_.biteInterval;
            cat->health -= config_.biteDamage;
        }
    }
}

void Game::removeDead() {
    std::erase_if(state_.cats, [](const Cat& c) { return c.health <= 0; });
    std::erase_if(state_.mutants, [](const Mutant& m) { return m.health <= 0; });
}

void Game::handleMutantsAtHome() {
    std::erase_if(state_.mutants, [this](const Mutant& m) {
        if (m.position >= 0) return false;
        if (m.type != MutantType::Equivalent) state_.lives--;
        return true;
    });
}

void Game::checkEndConditions() {
    if (state_.lives <= 0) {
        state_.lives = 0;
        state_.status = Status::Lost;
    } else if (state_.nextSpawn == waves_.size() && state_.mutants.empty()) {
        state_.status = Status::Won;
    }
}

bool Game::inBounds(int lane, int col) const {
    return lane >= 0 && lane < config_.lanes && col >= 0 && col < config_.cols;
}

const Cat* Game::catAt(int lane, int col) const {
    for (const Cat& c : state_.cats) {
        if (c.lane == lane && c.col == col) return &c;
    }
    return nullptr;
}

Cat* Game::mutableCatAt(int lane, int col) {
    return const_cast<Cat*>(std::as_const(*this).catAt(lane, col));
}

bool Game::anyMutantInRange(int lane, int fromCol, int toCol) const {
    return std::any_of(state_.mutants.begin(), state_.mutants.end(), [&](const Mutant& m) {
        const int cell = cellOf(m.position);
        return m.lane == lane && m.health > 0 && cell >= fromCol && cell <= toCol;
    });
}

void Game::damage(Mutant& mutant, int amount) const {
    if (mutant.type == MutantType::Equivalent) return;
    mutant.health -= amount;
}

}  // namespace cvm
