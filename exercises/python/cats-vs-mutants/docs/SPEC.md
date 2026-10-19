# Cats vs Mutants: Game Specification

A small lane defense game in Python with ASCII graphics for the terminal.
Cats defend the left side of the board against mutants walking in from the right.

This is a Python port of the C++20 version in `exercises/cpp/cats-vs-mutants`. The rules are the
same, and the headless output is byte-identical to the C++ build. This document describes the
game as it is implemented today. Feature specs written by the `product` agent
(`docs/features/`) describe changes relative to it.

## Build and run

```
uv sync
uv run cats-vs-mutants                                  # interactive game
uv run cats-vs-mutants --headless scripts/demo.txt      # scripted game, prints the final state
uv run pytest                                           # unit tests
uv run ruff check . && uv run ruff format --check .     # lint and formatting
uv run --with mypy mypy --strict src/cats_vs_mutants/core
```

`python -m cats_vs_mutants` works too. Requirements: Python 3.11+ and `uv`. No runtime
dependencies; `curses` ships with Python on macOS and Linux.

## Board, time and economy

| Setting | Default | `Config` field |
|---|---|---|
| Lanes | 5 | `lanes` |
| Columns (cells per lane) | 9 | `cols` |
| Steps per cell | 10 | `cell_size` |
| Starting treats | 150 | `starting_treats` |
| Passive income | +25 treats every 100 ticks | `passive_income`, `passive_income_interval` |
| Starting lives | 3 | `starting_lives` |

- The game advances in **ticks**. The interactive game runs 10 ticks per second.
- Mutants spawn at the right edge (position `cols * cell_size` = 90 steps) and walk toward
  home (position below 0). A mutant's cell is `position / cell_size`, truncated toward zero
  as in C++ (`Game.cell_of`), so step -1 is still cell 0.
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

- Hairballs move 5 steps per tick (`hairball_speed`).
- A mutant blocked by a cat bites it for 10 damage every 10 ticks (`bite_damage`, `bite_interval`).
- Every number above lives in `Config` (`src/cats_vs_mutants/core/config.py`).

## Waves

Three fixed waves (`default_waves()` in `src/cats_vs_mutants/core/waves.py`), each roughly
300 ticks:

1. Six slow Blobs.
2. Blobs and Runners.
3. Brutes, Hoppers, Blobs, Runners and one Equivalent Mutant.

## Tick order

`Game.tick()` (`src/cats_vs_mutants/core/game.py`) runs these steps in order:

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
  fires on tick 15. Mutant move timers work the same way from their spawn tick. Every timer
  is decremented first and then compared with 0.
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
- `Config.seed` exists, but the shipped rules use no randomness.
- `Game` keeps its own deep copy of the `Config` and waves it is given, so changing a config
  after creating a game has no effect on that game.

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

`cats-vs-mutants --headless <script>` runs the game without curses and prints the final
state. One command per line; `#` starts a comment.

```
place <cat> <lane> <col>     # cat = rich | hissing | sleepy | laser
remove <lane> <col>
tick <n>
print
```

Numbers are read like C++ `istringstream >>`: `2abc` reads as 2, and values outside the 32-bit
range are errors. Errors print `<script>:<line>: ...` to stderr and exit with 1; usage errors
exit with 2.

`scripts/demo.txt` plays a full winning game with checkpoints after each wave. It ends
`STATUS: Won` at tick 1648 with 3 lives; this is the regression check every change must keep.

## Code layout

```
src/cats_vs_mutants/core/   config, entities, game rules, wave data
                            Pure and deterministic: no curses, no I/O, no clock, no global state.
src/cats_vs_mutants/ui/     text.py         sprites, names, messages, cell and header text
                            renderer.py     UiState and the curses renderer
                            interactive.py  key handling and the 10 ticks/second game loop
                            headless.py     script runner and plain-text state dump
                            main.py         command line entry point (`cats-vs-mutants`)
tests/                      pytest suite (229 tests)
tests/golden/               reference output captured from the C++ build (capture.sh)
scripts/                    headless demo scripts
```

The tests:

| File | What it covers |
|---|---|
| `test_placement.py`, `test_economy.py`, `test_combat.py`, `test_mutant.py`, `test_end_conditions.py`, `test_waves_config.py`, `test_full_game.py`, `test_smoke.py` | The 121 rule tests, one per C++ GoogleTest test, plus a few Python-only porting checks |
| `test_headless.py` | stdout, stderr and exit code of the headless runner against `tests/golden/` |
| `test_cpp_parity.py` | Random scripts run through both builds. Skipped when the C++ binary is missing; set `CVM_CPP_BIN` to point at it |
| `test_interactive.py` | Key handling, and drawing against a fake curses screen |
| `test_core_purity.py` | The core imports no UI, I/O or clock modules, and uses only seeded `random.Random` instances |
| `test_golden_data.py` | The captured reference output is complete |

Shared helpers live in `tests/helpers.py`: `NEVER`, `quiet_config()`, `tick_n`, `tick_to`,
`only_mutant`.

## Engineering ground rules

Every change to the game keeps these:

1. **Core stays pure.** All rules go in `cats_vs_mutants.core`. No I/O, no clock, no global
   state. `tests/test_core_purity.py` checks the imports.
2. **Existing tests pass unchanged**, and `scripts/demo.txt` still ends `STATUS: Won` at tick
   1648 with 3 lives. A feature that would change the current game sits behind a `Config`
   switch that defaults to off. In particular, the headless output of existing scripts must
   not change: `tests/golden/` and the C++ parity tests pin it byte for byte.
   One narrow exception: a test in `tests/test_interactive.py` that pins interactive screen
   text (the help line, for example) may be updated when a feature spec explicitly changes
   that text. The spec lists each such change, and QA reports it.
3. **Every number lives in `Config`**, so tests can build exact scenarios.
4. **Deterministic.** Same config, waves and inputs give the same `GameState`. Randomness only
   through a `random.Random` seeded from `Config.seed`, and only through its `random()`
   method: Python guarantees that `random()` gives the same sequence for a seed across
   versions, but not `randint`, `randrange` or `choice`.
5. **Clean tooling.** `ruff check` and `ruff format --check` pass, and `mypy --strict` passes
   on `src/cats_vs_mutants/core`.
