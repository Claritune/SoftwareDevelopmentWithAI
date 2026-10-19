#pragma once

#include <vector>

#include "entities.hpp"

namespace cvm {

// The three shipped waves, as plain spawn data sorted by tick.
std::vector<SpawnEvent> defaultWaves();

}  // namespace cvm
