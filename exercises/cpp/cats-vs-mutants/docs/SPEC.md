# Cats vs Mutants: Game Specification

A small lane defense game in C++20 with ASCII graphics for the macOS terminal.
Cats defend the left side of the board against mutants walking in from the right.

This document describes the game as it is implemented today. Feature specs written by the
`product` agent (`docs/features/`) describe changes relative to it.

## Build and run

```
cmake -S . -B build
cmake --build build
./build/cats                                  # interactive game
./build/cats --headless scripts/demo.txt      # scripted game, prints the final state
ctest --test-dir build                        # unit tests
```

Requirements: CMake 3.20+, Apple Clang (or any C++20 compiler), ncurses (ships with
macOS). GoogleTest is fetched automatically on the first configure.

## Board, time and economy

| Setting | Default | `Config` field |
|---|---|---|
| Lanes | 5 | `lanes` |
| Columns (cells per lane) | 9 | `cols` |
| Steps per cell | 10 | `cellSize` |
| Starting treats | 150 | `startingTreats` |
| Passive income | +25 treats every 100 ticks | `passiveIncome`, `passiveIncomeInterval` |
| Starting lives | 3 | `startingLives` |

- The game advances in **ticks**. The interactive game runs 10 ticks per second.
- Mutants spawn at the right edge (position `cols * cellSize` = 90 steps) and walk toward
  home (position below 0). A mutant's cell is `position / cellSize`.
- Cats are placed on cells. Placing costs treats; removing a cat gives no refund.
- A mutant that reaches home costs one life (the Equivalent Mutant costs nothing).
- **Won**: every scheduled mutant has spawned and the board is clear of mutants.
- **Lost**: lives reach 0. Lives are clamped to 0.

## Cast

| Cat | Sprite | Cost | Health | Behavior |
|---|---|---|---|---|
| Rich Cat | `=$.$=` | 50 | 40 | +25 treats every 80 ticks |
| Hissing Cat | `=^o^=` | 100 | 60 | Spits a hairball (20 dmg) every 15 ticks if a mutant is in its lane |
| Sleepy Cat | `=-.-=` | 50 | 300 | Blocks mutants |
| Laser Cat | `=O.O=` | 175 | 60 | Every 30 ticks, 30 dmg to all mutants within 4 cells |

| Mutant | Sprite | Health | Speed | Special |
|---|---|---|---|---|
| Blob | `(x_x)` | 100 | 1 step / 2 ticks | |
| Runner | `{@_@}` | 60 | 1 step / tick | |
| Brute | `<O_O>` | 300 | 1 step / 3 ticks | |
| Hopper | `(o_O)` | 80 | 1 step / 2 ticks | Jumps over the first cat that blocks it |
| Equivalent Mutant | `( _ )` | 1 | 1 step / 2 ticks | Cannot be killed, and reaching home costs nothing |

- Hairballs move 5 steps per tick (`hairballSpeed`).
- A mutant blocked by a cat bites it for 10 damage every 10 ticks (`biteDamage`, `biteInterval`).
- Every number above lives in `Config` (`src/core/config.hpp`).

## Waves

Three fixed waves (`defaultWaves()` in `src/core/waves.cpp`), each roughly 300 ticks:

1. Six slow Blobs.
2. Blobs and Runners.
3. Brutes, Hoppers, Blobs, Runners and one Equivalent Mutant.

## Tick order

`Game::tick()` (`src/core/game.cpp`) runs these steps in order:

1. Increment tick counter
2. Passive income and Rich Cat production
3. Spawn mutants scheduled for this tick
4. Cats fire (hairballs created, laser damage applied)
5. Move hairballs and resolve hits
6. Move mutants (respecting blocking and Hopper jumps)
7. Resolve bites
8. Remove dead cats and dead mutants
9. Handle mutants reaching home
10. Check win and lose conditions

## Rule details

The original spec left a few points open. This is how the code decides them:

- **Timers** count down from the cat's interval when it is placed. A cat placed when the
  counter reads T first acts on tick T + interval, so a Hissing Cat placed at tick 0 first
  fires on tick 15. Mutant move timers work the same way from their spawn tick.
- A Hissing or Laser Cat's timer resets whether or not it had a target.
- **"To its right"** includes the cat's own cell, so cats can hit a mutant that is biting them.
- **Hairballs** hit the closest live, damageable mutant in their lane whose position is between
  the cat's cell start and the hairball's position. They are removed once past step 90.
- **The Equivalent Mutant** triggers Hissing and Laser Cats but takes no damage. It can still
  be blocked and can bite.
- **Hopper jump**: when first blocked by a cat in column `c`, it moves to step `c * 10 - 1`.
  If `c` is 0, that is home.
- **Bite timer** resets to 10 whenever the mutant is not blocked.
- **Lives** are clamped to 0 when the game is lost.
- `SpawnEvent` has an extra `wave` field, used for the `WAVE n/3` header.
- `Config::seed` exists, but the shipped rules use no randomness.

## Controls

| Key | Action |
|---|---|
| Arrow keys | Move cursor |
| `1` to `4` | Select Rich (50), Hissing (100), Sleepy (50), Laser (175) |
| Space / Enter | Place selected cat at cursor |
| `x` | Remove cat at cursor (no refund) |
| `p` | Pause |
| `q` | Quit |

Each lane is drawn as two rows: cats on top, mutants and hairballs below.

## Headless mode

`./build/cats --headless <script>` runs the game without ncurses and prints the final
state. One command per line; `#` starts a comment.

```
place <cat> <lane> <col>     # cat = rich | hissing | sleepy | laser
remove <lane> <col>
tick <n>
print
```

`scripts/demo.txt` plays a full winning game with checkpoints after each wave. It ends
`STATUS: Won` at tick 1648 with 3 lives; this is the regression check every change must keep.

## Code layout

```
src/core/   cvm_core static library: config, entities, game rules, wave data
            Pure and deterministic: no ncurses, no I/O, no clock, no global state.
src/ui/     ncurses renderer, input loop, headless runner (the `cats` executable)
tests/      GoogleTest executable linking only cvm_core (121 tests)
scripts/    headless demo scripts
```

## Engineering ground rules

Every change to the game keeps these:

1. **Core stays pure.** All rules go in `cvm_core`. No I/O, no clock, no global state.
2. **Existing tests pass unchanged**, and `scripts/demo.txt` still ends `STATUS: Won` at tick
   1648 with 3 lives. A feature that would change the current game sits behind a `Config`
   switch that defaults to off.
3. **Every number lives in `Config`**, so tests can build exact scenarios.
4. **Deterministic.** Same config, waves and inputs give the same `GameState`. Randomness only
   through a `std::mt19937` seeded from `Config::seed`.
5. **Zero warnings** with `-Wall -Wextra -Wpedantic`.
