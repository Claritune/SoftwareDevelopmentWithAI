#include "waves.hpp"

namespace cvm {

// At 10 ticks per second each wave lasts roughly 30 seconds (300 ticks).
std::vector<SpawnEvent> defaultWaves() {
    using M = MutantType;
    return {
        // Wave 1: a few slow Blobs to learn the ropes.
        {150, 2, M::Blob, 1},
        {200, 0, M::Blob, 1},
        {240, 4, M::Blob, 1},
        {270, 1, M::Blob, 1},
        {300, 3, M::Blob, 1},
        {320, 2, M::Blob, 1},

        // Wave 2: Runners join in.
        {460, 1, M::Blob, 2},
        {490, 3, M::Runner, 2},
        {520, 0, M::Blob, 2},
        {550, 4, M::Runner, 2},
        {570, 2, M::Blob, 2},
        {600, 2, M::Runner, 2},
        {630, 0, M::Runner, 2},
        {650, 3, M::Blob, 2},
        {670, 1, M::Runner, 2},
        {690, 4, M::Blob, 2},

        // Wave 3: Brutes, Hoppers, and one mutant no test can kill.
        {790, 2, M::Brute, 3},
        {810, 0, M::Hopper, 3},
        {835, 4, M::Blob, 3},
        {850, 3, M::Runner, 3},
        {870, 1, M::Equivalent, 3},
        {890, 4, M::Hopper, 3},
        {910, 1, M::Blob, 3},
        {930, 3, M::Brute, 3},
        {950, 0, M::Runner, 3},
        {970, 2, M::Hopper, 3},
        {990, 4, M::Runner, 3},
        {1010, 1, M::Brute, 3},
        {1030, 0, M::Blob, 3},
        {1050, 3, M::Hopper, 3},
    };
}

}  // namespace cvm
