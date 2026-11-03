# Cats vs Mutants: Architecture

This document splits the game into modules that separate developers can own. For each module it
lists what the module does, the files it owns, its public interface, what it depends on and the
invariants it keeps. It also sets the rules for changing a module's public interface.

`docs/SPEC.md` describes **what** the game does. This document describes **where** each part
lives and **who** may change it. Feature designs in `docs/design/` must name the module each
change belongs to.

## Overview

There are three build targets (`CMakeLists.txt`, `tests/CMakeLists.txt`):

| Target | Kind | Sources | Links |
|---|---|---|---|
| `cvm_core` | static library | `src/core/*.cpp` | nothing |
| `cats` | executable | `src/ui/*.cpp` | `cvm_core`, ncurses |
| `cvm_tests` | executable | `tests/*.cpp` | `cvm_core`, GoogleTest (never ncurses) |

These split into six code modules, three in each target:

| Module | Target | Files | Developer agent | One line |
|---|---|---|---|---|
| **model** | `cvm_core` | `src/core/config.hpp`, `src/core/entities.hpp` | `dev-model` | The data contract: enums, `Config`, entity structs and `GameState` |
| **rules** | `cvm_core` | `src/core/game.hpp`, `src/core/game.cpp` | `dev-rules` | `Game`: placement, removal and the ten-step `tick()` |
| **waves** | `cvm_core` | `src/core/waves.hpp`, `src/core/waves.cpp` | `dev-waves` | Spawn schedules as plain data (`defaultWaves()`) |
| **view** | `cats` | `src/ui/renderer.hpp`, `src/ui/renderer.cpp` | `dev-view` | Text presentation of the state, plus the ncurses `Renderer` |
| **headless** | `cats` | `src/ui/headless.hpp`, `src/ui/headless.cpp`, `scripts/` | `dev-headless` | Script runner and plain-text state dump |
| **app** | `cats` | `src/ui/main.cpp` | `dev-app` | Entry point, command line, interactive input loop and clock |

Areas that are not code modules:

| Area | Owner |
|---|---|
| `tests/` (all files, including `tests/CMakeLists.txt`) | `qa` |
| `docs/features/` | `product` |
| `docs/design/`, `docs/ARCHITECTURE.md` | `architect` |
| `docs/qa/` | `qa` |
| Top-level `CMakeLists.txt` | Shared; see "Shared files" |
| `docs/SPEC.md` | Shared by section; see "Shared files" |

## Dependency diagram

An arrow means "includes and uses". Nothing points upwards, and there are no cycles.

```
                         +------------------+
                         |       app        |  src/ui/main.cpp
                         +------------------+
                            |            |
                            v            v
         +------------------+            +------------------+
         |     headless     |----------->|       view       |   cats (executable)
         +------------------+            +------------------+
  - - - - - - - | - - - - - - - - - - - - - - - - | - - - - - - - - - - - - - - - -
                v                                 v               cvm_core (library)
         +------------------+            +------------------+
         |      waves       |            |      rules       |<------ cvm_tests (qa)
         +------------------+            +------------------+
                         \                  /
                          v                v
                         +------------------+
                         |      model       |  config.hpp, entities.hpp
                         +------------------+
```

To keep the picture readable it leaves out some edges: app uses rules and waves, headless uses
rules, the tests use waves and model, and every module uses model. The table lists all of them.

The same edges as a list (every module above model also uses model types directly):

| Module | Depends on |
|---|---|
| model | C++ standard library only (`<cstdint>`, `<cstddef>`, `<vector>`) |
| rules | model |
| waves | model |
| view | rules (`const Game&`), model, ncurses (in `renderer.cpp` only) |
| headless | view (text helpers), rules, waves, model, standard I/O |
| app | view (`Renderer`, `UiState`, `placeResultMessage`), headless (`runHeadless`), rules, waves, model, ncurses, `<chrono>`, `<csignal>` |
| tests (qa) | rules, waves, model |

Two points about the shape:

- **rules does not depend on waves.** `Game` takes its spawn list as a constructor argument. The
  two composition roots, app and headless, wire `defaultWaves()` into `Game`. Keep it that way:
  tests rely on passing their own wave lists.
- **headless depends on view**, because the board and header in `printState` come from
  `cellText` and `headerText`. A change to a sprite or the header format in view changes the
  headless output. That output is a checked contract (see "Cross-module contracts").

## Modules

### model

**Responsibilities.** Defines every type that crosses a module boundary, and every tunable
number. Holds no game logic beyond trivial lookups.

**Owns.** `src/core/config.hpp`, `src/core/entities.hpp`.

**Public interface.** All of it. Every declaration in these two headers is used by at least one
other module or by the tests:

- `config.hpp`: `CatType`, `MutantType`, `CatStats`, `MutantStats`, `Config` (all fields, plus
  `cat(CatType)`, `mutant(MutantType)` and `spawnPosition()`).
- `entities.hpp`: `Status`, `PlaceResult`, `Cat`, `Mutant`, `Hairball`, `SpawnEvent`,
  `GameState`.

**Depends on.** The standard library only.

**Invariants.**

1. Header-only. No `.cpp` file, no I/O, no ncurses, no globals, no randomness.
2. **Every tunable number of the rules is a `Config` field** with a default. The defaults
   reproduce the shipped game: the demo ends `STATUS: Won` at tick 1648 with 3 lives.
3. A feature that would change the default game gets a `Config` switch that defaults to off.
4. **New fields go last** in `Config`, `Cat`, `Mutant`, `Hairball`, `SpawnEvent` and
   `GameState`, with a default member initialiser, so existing aggregate initialisation keeps
   compiling.
5. **New enumerators are appended**, never inserted or reordered.
6. `Config::cat()` and `Config::mutant()` handle every enumerator in their `switch`.
7. Every entity struct and `GameState` keep a defaulted `operator==`. Tests compare whole states.
8. `GameState` holds the whole observable state of a game. If a rule needs state, it lives here,
   not in a hidden member of `Game`.

### rules

**Responsibilities.** Owns the `Game` class: applies placement and removal, runs one simulation
step per `tick()`, and answers read-only queries about the state.

**Owns.** `src/core/game.hpp`, `src/core/game.cpp`.

**Public interface** (the `public:` section of `Game` in `game.hpp`):

```cpp
Game(Config config, std::vector<SpawnEvent> waves);
PlaceResult place(CatType type, int lane, int col);
bool remove(int lane, int col);
void tick();
const GameState& state() const;
const Config& config() const;
Status status() const;
int currentWave() const;
int totalWaves() const;
const Cat* catAt(int lane, int col) const;
int cellOf(int position) const;
```

The `private:` section (tick steps such as `moveMutants()` and `wearOffStuns()`, helpers such
as `damage()` and `ambush()`, and the members) is internal to rules. It may change without an
interface request, as long as the feature design allows it.

**Depends on.** model.

**Invariants.**

1. **Pure and deterministic.** No I/O, no clock, no ncurses, no globals. Randomness only through
   a `std::mt19937` seeded from `Config::seed`. Same config, waves and inputs give the same
   `GameState`.
2. **No numbers in `game.cpp`.** Every value comes from `config_`.
3. **`tick()` runs the ten steps in the documented order.** New behaviour goes into an existing
   step or a named private step. The comment beside each call in `tick()` stays accurate, and so
   does "Tick order" in `docs/SPEC.md`.
4. `state_` changes only through `place`, `remove` and `tick`. `tick`, `place` and `remove` do
   nothing once `status != Playing`.
5. `waves_` is stable-sorted by tick in the constructor, and `state_.nextSpawn` indexes it.
6. Every aggregate that rules builds (for example `Mutant` in `spawnMutants()`) lists every
   field explicitly, so `-Wmissing-field-initializers` stays quiet on all compilers.
7. Every `switch` on a model enum handles every enumerator.

### waves

**Responsibilities.** Produces spawn schedules as plain data. Today that is the three shipped
waves. A generated-wave function for Endless mode would also live here (`NEW_FEATURES.md`,
Feature 5).

**Owns.** `src/core/waves.hpp`, `src/core/waves.cpp`.

**Public interface.** `std::vector<SpawnEvent> defaultWaves();`

**Depends on.** model (`SpawnEvent`, `MutantType`, and `Config` for any future generator).
**Never rules.**

**Invariants.**

1. Pure functions of their arguments. No state, no I/O. Any randomness uses a `std::mt19937`
   seeded from `Config::seed`, without `std::uniform_int_distribution` (its output differs
   between standard libraries).
2. Returned events are sorted by `tick`. Every `lane` is inside `[0, Config{}.lanes)`. `wave`
   numbers start at 1 and have no gaps.
3. **The content of `defaultWaves()` is frozen.** The demo result, `tests/full_game_test.cpp`,
   `tests/waves_config_test.cpp` and the `WAVE n/3` header all depend on it. Changing it needs a
   spec from the product manager and a design.

### view

**Responsibilities.** Turns game state into text. It has two parts in one module:

- **Text helpers**, with no ncurses calls: sprites, names, messages, the 5-character cell text
  and the header line. Both the ncurses screen and the headless dump use them.
- **The ncurses `Renderer`**: screen setup and teardown, colours, board, help line, end screen.

**Owns.** `src/ui/renderer.hpp`, `src/ui/renderer.cpp`.

**Public interface** (`namespace cvm::ui`, `renderer.hpp`):

```cpp
const char* catSprite(CatType);       const char* catName(CatType);
const char* mutantSprite(MutantType); const char* mutantName(MutantType);
const char* statusName(Status);       const char* placeResultMessage(PlaceResult);
std::string cellText(const Game&, int lane, int col, int row);
std::string headerText(const Game&);
struct UiState { int cursorLane; int cursorCol; CatType selected; bool paused; std::string message; };
class Renderer { Renderer(); ~Renderer(); void draw(const Game&, const UiState&); };
```

Anonymous-namespace helpers in `renderer.cpp` (`frontMutant`, the colour pairs) are internal.

**Depends on.** rules (const access only), model, ncurses.

**Invariants.**

1. **Read-only.** It takes `const Game&` and never calls `place`, `remove` or `tick`. No rules
   live here. A colour or symbol may reflect state, such as stunned mutants drawn yellow, but
   must not decide it.
2. **Text helpers never call ncurses.** Headless output goes through them and must work without
   a terminal.
3. Every sprite is exactly 5 characters and never starts with a space. `drawBoard` uses the
   first character to tell sprites from hairball rows. `cellText` always returns 5 characters:
   `"  .  "` for an empty cat row, and blanks plus `o` for hairballs on a mutant row.
4. Every `switch` on a model enum handles every enumerator. Adding a `CatType` or `MutantType`
   always needs a view change.
5. `Renderer` is RAII: `initscr` in the constructor, `endwin` in the destructor, one instance at
   a time.
6. `headerText`'s format (`TREATS: n   WAVE a/b   LIVES: n   TICK: n`) is part of the headless
   output contract. Change it only through an interface request.

### headless

**Responsibilities.** Runs a command script against a game without ncurses and prints the state
as plain text. This is how the demo regression check and script-based acceptance checks run.
Also holds the demo scripts.

**Owns.** `src/ui/headless.hpp`, `src/ui/headless.cpp`, `scripts/` (custodian of
`scripts/demo.txt`; see invariant 4).

**Public interface.**

- C++ (`namespace cvm::ui`): `void printState(const Game&, std::ostream&);` and
  `int runHeadless(const std::string& path);` (returns a process exit code).
- **The script language**: `place <cat> <lane> <col>`, `remove <lane> <col>`, `tick <n>`,
  `print`, `#` comments. The cat names are `rich`, `hissing`, `sleepy`, `laser` and `boxer`.
- **The output format**: the failed-placement line, the board, the `cat` / `mutant` /
  `hairball` entity lines (including the optional ` stun <n>` suffix) and the
  `=== FINAL STATE ===` marker. QA, the demo check and acceptance criteria grep this output.

**Depends on.** view (`headerText`, `cellText`, `statusName`, `catSprite`, `mutantSprite`,
`placeResultMessage`), rules, waves (`defaultWaves`), model, standard I/O.

**Invariants.**

1. **No ncurses**, directly or by constructing a `Renderer`.
2. Starts from `Config{}` and `defaultWaves()`, unless a script command defined by a design
   says otherwise.
3. **The output format only grows.** Existing lines keep their exact text. New information is
   added as a new line type, or as a suffix printed only when it differs from the default (the
   ` stun <n>` pattern), so a game without the feature prints exactly what it printed before.
4. **`scripts/demo.txt` is frozen.** It must keep ending `STATUS: Won` at tick 1648 with 3 lives.
   Changing the script needs the product manager and the architect. New scripts may be added.
5. Exit codes: 0 when the script ran, 1 for a bad script or an unreadable file.

### app

**Responsibilities.** The process entry point. Parses the command line, runs either headless
mode or the interactive game, turns key presses into UI state changes or core API calls, and
owns the real-time clock (100 ms per tick) and SIGINT handling.

**Owns.** `src/ui/main.cpp`.

**Public interface.** Not C++. It is the user-facing surface:

- Command line: `cats` and `cats --headless <script>` (exit code 2 on bad usage).
- Key bindings: arrows, `1`-`4` and `6` to select cats (`5` is reserved for the Frosty Cat),
  Space/Enter, `x`, `p`, `q`.

**Depends on.** view, headless, rules, waves, model, ncurses (input only), `<chrono>`,
`<csignal>`.

**Invariants.**

1. Calls only `Game::place`, `Game::remove`, `Game::tick` and const accessors. No rules here.
2. The only module with a clock or signals. Pausing stops `tick()` calls, and nothing else.
3. Builds the interactive game from `Config{}` and `defaultWaves()`, plus any switch a design
   explicitly turns on for interactive play.
4. Stays a thin composition root. Drawing belongs to view and script handling to headless.

## Cross-module contracts

These couplings are not visible in a single header. Designs must call them out.

| Contract | Provider | Consumers | What breaks |
|---|---|---|---|
| Demo result: Won at tick 1648, 3 lives | model defaults, rules, waves | headless (`scripts/demo.txt`), QA | The regression check every change must keep |
| Headless output text | headless and view (`headerText`, `cellText`, sprites) | QA, acceptance criteria, demo check | Greps on `TICK: 1648`, `cat     [^.^] lane 0 col 8 hp 20`, ` stun 48` |
| Enum completeness | model | rules, view, headless (`parseCat`), app (keys) | `-Wswitch` warnings, unplaceable cats |
| Full aggregate initialisers | model (`Mutant` fields) | rules (`spawnMutants`) | `-Wmissing-field-initializers` on GCC |
| Observable state | model (`GameState`), rules (const accessors) | QA | Untestable rules |

## Ownership of tests

Tests stay with `qa`. Module developers never edit `tests/`.

- Tests cut across modules. `full_game_test.cpp` runs waves and rules together, and
  `test_helpers.hpp` is shared by every test file. Splitting tests by module would leave most of
  them with no single owner.
- Independent verification is the point of QA. A developer who could edit the test for their
  module could also weaken it.
- Every developer **runs** the whole suite and reports failures with their output.

One gap to know about: view, headless and app live in the `cats` executable, which `cvm_tests`
does not link. They have no unit tests. They are checked through headless scripts and by hand.
See question P2 at the end.

## Shared files

| File | Rule |
|---|---|
| Top-level `CMakeLists.txt` | A module developer may add or remove **its own** source files in its target's source list (`cvm_core` for rules and waves, `cats` for view, headless and app). Anything else (flags, targets, link libraries, options) needs a design from the architect, and the design names who makes the edit. |
| `tests/CMakeLists.txt` | `qa` only. |
| `docs/SPEC.md` | Split by section, and edited only where the feature design says player-visible behaviour changes. "Board, time and economy", "Cast", "Tick order" and "Rule details": `dev-rules`, which also writes the sprite into the Cast table from the design. "Waves": `dev-waves`. "Controls": `dev-app`. "Headless mode": `dev-headless`. "Build and run", "Code layout" and "Engineering ground rules": only as a design directs. |
| `src/core/game.hpp` | Owned by rules. Only the `public:` section is interface. |
| `src/ui/renderer.hpp` | Owned by view. It exposes the text helpers to headless and `Renderer`/`UiState` to app. |

## Changing a public interface

### What counts as an interface change

| Kind | Examples | Who must agree |
|---|---|---|
| **Internal** | Function bodies, `private:` members of `Game`, anonymous-namespace helpers, comments | The owning developer, following the design. No request needed. |
| **Additive** | New enumerator, new field (last, with a default), new `Config` entry, new free function or public member, new headless line type or default-silent suffix, new key binding or script command | The architect (it goes in the design). The product manager too if it is player-visible. |
| **Breaking** | Renaming, removing or re-typing anything public. Changing the meaning of an existing function or field. Changing existing output text, `headerText`, a sprite, a key, a script command or `defaultWaves()` content. Reordering fields or enumerators. | The architect, every consuming module's owner (consulted through the architect), the product manager if it is player-visible, and `qa` if any test or `test_helpers.hpp` uses it. Breaking changes that would require editing existing tests are refused unless the product manager explicitly accepts the change in behaviour. |

### How a developer asks

A module developer who needs another module's interface to change **does not edit that module**.
It stops and puts an interface request in its report:

```
Interface request
- Module: <owner module>        - Symbol: <type / function / field>
- Change: <exact new declaration or behaviour>
- Kind: additive | breaking
- Why: <the design step it blocks>
- Consumers affected: <modules, tests>
```

The architect rules on it. It amends `docs/design/<slug>.md`, and this document if a module
boundary or interface changes. The orchestrator then schedules the owning developer.

### In what order changes land

1. **The design comes first.** Every interface change is written into the feature design, with
   exact declarations, before any developer starts. Implementation steps in the design are
   tagged with their module.
2. **Providers before consumers**, in dependency order:
   **model → rules and waves (in parallel) → view → headless and app (in parallel) → qa.**
3. **Breaking changes are expand, migrate, contract.** Add the new form next to the old, move
   every consumer over, then remove the old form in a final step by the provider.
4. **Change sets for enum and aggregate growth.** Adding an enumerator makes every `switch` on
   that enum warn until its owner adds the case. Adding a `Mutant` field affects
   `spawnMutants()`. The design groups these into one change set: model's change plus the
   minimal case or initialiser edits in rules, view, headless and app. The orchestrator runs
   those developers back to back, and judges the zero-warning rule at the end of the set, not
   between its steps.
5. **Integration gate after every change set.** A clean build of all targets with zero warnings,
   the full test suite passing, and the demo ending `STATUS: Won` at tick 1648 with 3 lives.
   The orchestrator or `qa` runs it, not a module developer.

### Working at the same time

Several developers may run at once in one working tree.

- Each developer builds in its **own build directory outside the source tree**, for example
  `${TMPDIR:-/tmp}/cvm-build-<agent-name>`. A shared `build/` breaks when two `cmake` processes
  run in it at once.
- Core developers can build just their part: `--target cvm_core cvm_tests`. UI developers need
  the `cats` target, so they depend on core having landed.
- If a build fails in a file you don't own, it is probably another developer mid-change. Report
  it, don't fix it.

## Example: adding a cat type (Boxer Cat)

The Boxer Cat (`docs/design/boxer-cat.md`) shows the usual spread of a new cat:

| Module | Change |
|---|---|
| model | `CatType::Boxer`. `Config::boxer`, `ambushDamage` and `stunDuration` after `seed`. `Config::cat()` case. `Mutant::stunTicks` and `Mutant::ambushed` last. |
| rules | Explicit initialisers in `spawnMutants()`. Ambush in `moveMutants()`. Stun skip in `resolveBites()`. New step `wearOffStuns()`. `tick()` comments. SPEC "Cast", "Tick order", "Rule details". |
| view | `catSprite` and `catName` cases (change set with model), help-line entry, `kStunnedColor` and `frontMutant`. |
| headless | `parseCat("boxer")`, ` stun <n>` suffix. SPEC "Headless mode". |
| app | Key `6`. SPEC "Controls". |
| qa | `tests/boxer_test.cpp` and its entry in `tests/CMakeLists.txt`. |

Five developers and QA for one cat. The design's step 1 already pairs model with view because of
`-Wswitch`, and step 2 pairs model with rules because of the `Mutant` initialiser. Those are the
change sets from rule 4 above.

## Open questions

- **P1. One catalogue for each cat type.** A cat's display name, sprite, script name and key now
  sit in three modules (`catName`/`catSprite` in view, `parseCat` in headless, `handleKey` in
  app). One table in view (`catInfo(CatType)` returning sprite, name, script name and key), read
  by headless and app, would shrink a new cat's UI work to one module. It would change no
  behaviour. Recommendation: do it only when the next cat is designed, not before.
- **P2. Testable text helpers.** Moving the ncurses-free text helpers out of `renderer.cpp` into
  their own file in a small library would let `cvm_tests` cover them, and would make the
  view/headless boundary explicit. Recommendation: not now. Headless scripts cover the output.
  Revisit if presentation bugs appear.
- **P3. Architect's write scope.** The architect agent's boundaries say "write only under
  `docs/design/`". This document lives at `docs/ARCHITECTURE.md` by exception. Recommendation:
  extend the architect's boundaries to include `docs/ARCHITECTURE.md` permanently, because the
  interface rules above need someone to keep it current.
