#pragma once

#include <iosfwd>
#include <string>

#include "../core/game.hpp"

namespace cvm::ui {

// Plain text dump of the whole game state (header, board, entity list).
void printState(const Game& game, std::ostream& out);

// Runs the command script at `path` without ncurses and prints the final state.
// Returns a process exit code.
int runHeadless(const std::string& path);

}  // namespace cvm::ui
