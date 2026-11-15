#include "gamer/games/registry.h"

#include "gamer/games/othello/othello.h"

namespace gamer {

Registry default_registry() { return {make_game(othello::Othello{})}; }

}  // namespace gamer
