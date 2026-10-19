# Cats vs Mutants: Python port plan

Port of the C++20 game *Cats vs Mutants* in `/Users/bigromanov/Code/ai/corecpp/cvm` to Python, in this folder.
The Python project is named **cats-vs-mutants** (distribution `cats-vs-mutants`, import package
`cats_vs_mutants`, console command `cats-vs-mutants`). Game content (mutant types, sprites,
texts) stays as in the C++ version so the output stays identical.
Goal: same rules, same output, same tests. A headless run of `scripts/demo.txt` must print
**byte-identical** output to the C++ binary and end `STATUS: Won` at tick 1648 with 3 lives.

---

## 1. Research: what the C++ project contains

About 750 lines of source and 1,400 lines of tests.

| C++ file | Lines | Contents | Python target |
|---|---|---|---|
| `src/core/config.hpp` | 83 | `CatType`, `MutantType`, `CatStats`, `MutantStats`, `Config` (every tunable number, `cat()`/`mutant()` lookups, `spawnPosition()`) | `cats_vs_mutants/core/config.py` |
| `src/core/entities.hpp` | 65 | `Status`, `PlaceResult`, `Cat`, `Mutant`, `Hairball`, `SpawnEvent`, `GameState` (all value types with `==`) | `cats_vs_mutants/core/entities.py` |
| `src/core/game.hpp/.cpp` | 270 | `Game`: `place`, `remove`, `tick` (10 ordered steps), `currentWave`, `totalWaves`, `catAt`, `cellOf` | `cats_vs_mutants/core/game.py` |
| `src/core/waves.hpp/.cpp` | 60 | `defaultWaves()`: 30 spawn events in 3 waves | `cats_vs_mutants/core/waves.py` |
| `src/ui/renderer.hpp/.cpp` | 260 | Sprites, names, messages, `cellText`, `headerText`, ncurses `Renderer` | `cats_vs_mutants/ui/renderer.py` (curses) |
| `src/ui/headless.hpp/.cpp` | 130 | `printState`, `runHeadless` script runner | `cats_vs_mutants/ui/headless.py` |
| `src/ui/main.cpp` | 95 | Arg parsing, key handling, 100 ms fixed-tick loop | `cats_vs_mutants/ui/main.py` |
| `tests/*.cpp` (9 files) | 1,440 | 121 GoogleTest tests + `test_helpers.hpp` | `tests/test_*.py` + `tests/conftest.py`/`helpers.py` |
| `scripts/demo.txt` | 84 | Headless script of a full winning game | copied as is |

Not ported: `.mutants/`, `.claude/` (MutantX tooling, C++-specific), `.cache/`, `CMakeLists.txt`,
`DEMO.md` (mutation-testing talk notes). `NEW_FEATURES.md` is copied into this folder as
reference only; its features are **not** implemented.

### Architecture to keep
- **Pure core.** `cats_vs_mutants.core` has no I/O, no clock, no randomness, no curses. The UI only reads
  game state and calls `place` / `remove` / `tick`.
- **Tick order is a game rule** (from `Game::tick`): 1 tick++, 2 income + Rich production,
  3 spawn, 4 cats fire, 5 move hairballs + resolve hits, 6 move mutants (blocking, Hopper jump),
  7 bites, 8 remove dead, 9 mutants at home, 10 win/lose check. No-op once the game is over.
- **Config is data.** Tests build custom configs (`quietConfig()`, tweak `hairballSpeed`, etc.).

### Porting pitfalls found in the code

| # | C++ behaviour | Python trap | Decision |
|---|---|---|---|
| 1 | `position / cellSize` truncates toward zero, so `cellOf(-1) == 0` | `-1 // 10 == -1` | `cell_of` uses `int(position / cell_size)` semantics (truncate). Matters for a Hopper that jumps a column-0 cat to step -1: it still "stands" in cell 0 during the bite step. Add a test for `cell_of(-1) == 0`. |
| 2 | `Game` takes `Config` and waves **by value** | Python shares references; a test mutating its config after construction would change the game | `Game.__init__` does `copy.deepcopy(config)` and `sorted(waves, key=tick)` (stable, like `std::stable_sort`). |
| 3 | `--cat.cooldown == 0` pre-decrement-then-compare | Easy to write `cooldown -= 1` after the check | Decrement first, then compare, in all four timers (Rich, fire, move, bite). |
| 4 | `resolveHits` keeps a `Mutant*` target and damages it in place | Fine with object refs, but must not copy dataclasses | Iterate over the real objects; never `dataclasses.replace` mutants inside a tick. |
| 5 | `std::erase_if` with a side effect (lives--) in `handleMutantsAtHome` | List comprehension with side effects is unclear | Explicit loop building a `remaining` list and counting lost lives. |
| 6 | `GameState::operator== = default` (determinism tests) | Need value equality across nested lists | `@dataclass` (with `eq=True`) for all entities and `GameState`. |
| 7 | Nested stats structs are mutated in tests (`config.hissing.interval = 30`) | Shared mutable defaults between `Config` instances | `@dataclass` with `field(default_factory=lambda: CatStats(50, 40, 80))`. |
| 8 | `Config::cat()` / `mutant()` switch | — | Plain `if` chain or `dict` built per call, so it reflects edited fields. |
| 9 | Headless parser uses `istringstream >>` (whitespace tokens, trailing tokens ignored, `#` comments) | `int("2x")` raises, while `>>` would read `2` | Match normal scripts exactly; strict `int()` for malformed tokens (reports "bad ... command", same exit code 1). Note the edge-case difference in the README. |
| 10 | Output via `printf("%d")` and fixed 5-char cells | — | f-strings; golden-file test guarantees parity. |
| 11 | `const GameState& state()` is read-only | Python can't enforce it | Expose `game.state` as a property; document "do not mutate". Not worth frozen dataclasses (the core mutates them every tick). |
| 12 | ncurses: `nodelay`, `keypad`, `use_default_colors`, `A_REVERSE` cursor, `napms(10)` | — | Stdlib `curses` (ships with macOS Python) via `curses.wrapper`; `time.monotonic()` for the 100 ms tick; `KeyboardInterrupt` replaces the SIGINT handler. |

---

## 2. Target layout

```
cats-vs-mutants/
  pyproject.toml          # name "cats-vs-mutants", Python >= 3.11, no runtime deps; dev: pytest, ruff
  README.md
  NEW_FEATURES.md         # copied for reference, not implemented
  scripts/demo.txt        # copied from C++ repo
  src/cats_vs_mutants/
    __init__.py
    __main__.py           # python -m cats_vs_mutants  [--headless script]
    core/
      config.py  entities.py  game.py  waves.py
    ui/
      text.py             # sprites, names, messages, cell_text, header_text (no curses)
      renderer.py         # UiState, curses Renderer
      interactive.py      # handle_key, fixed-rate game loop (imported only for interactive play)
      headless.py         # print_state, run_headless
      main.py             # arg parsing
  tests/
    helpers.py            # NEVER, quiet_config, tick_n, tick_to, only_mutant
    golden/                 # reference output captured from the C++ build (capture.sh)
      scripts/*.txt         # edge-case scripts: parse errors, place failures, comments
      <name>.stdout/.stderr/.exitcode
    test_smoke.py  test_placement.py  test_economy.py  test_combat.py
    test_mutant.py  test_end_conditions.py  test_waves_config.py  test_full_game.py
    test_headless.py      # golden output + script error handling + exit codes
    test_cpp_parity.py    # random scripts vs the C++ binary (skipped if it is missing)
    test_interactive.py   # handle_key + drawing on a fake curses screen
    test_core_purity.py   # core imports no UI, I/O, clock or randomness
```

Naming: snake_case for functions/fields (`cell_of`, `move_cooldown`, `has_jumped`), `Enum`
classes for the C++ enums (`CatType.RICH`). Test names map 1:1, e.g.
`TEST(Hissing, SpitsEvery15TicksWhenMutantInLane)` → `test_hissing_spits_every_15_ticks_when_mutant_in_lane`.
Tooling: `uv` (already installed) + `pytest`.

---

## 3. Implementation phases

Each phase ends with all its tests green before the next starts.

### Phase 0 (done): Scaffold and golden data
- `pyproject.toml` (with `[project.scripts] cats-vs-mutants = "cats_vs_mutants.ui.main:main"`),
  `src/cats_vs_mutants` package skeleton, `uv sync`, empty `pytest` run.
- Copy `scripts/demo.txt`.
- Capture golden output from the existing C++ build with `sh tests/golden/capture.sh`
  (defaults to `/Users/bigromanov/Code/ai/corecpp/cvm/build/cats`): `scripts/demo.txt` plus
  edge-case scripts in `tests/golden/scripts/` (unknown command, bad place/remove/tick, every
  place failure, comment and whitespace parsing) and a missing script file.
- `tests/test_golden_data.py` sanity-checks the captured reference.

### Phase 1 (done): Data model
- `config.py`, `entities.py`, `waves.py` (30 events copied verbatim).
- `Game.__init__`, `place`, `remove`, `cat_at`, `cell_of`, `current_wave`, `total_waves`;
  `tick` stub.
- Port: `test_smoke.py`, `test_placement.py`, `test_waves_config.py` (except tick-dependent
  wave-progress cases, which may wait for Phase 2).

### Phase 2 (done): Tick rules
- The ten private steps in exact order, each as its own method mirroring the C++ names.
- Port: `test_economy.py`, `test_combat.py`, `test_mutant.py`, `test_end_conditions.py`,
  rest of `test_waves_config.py`. Plus the extra `cell_of(-1) == 0` test (pitfall 1).

### Phase 3 (done): Full game and determinism
- Port `test_full_game.py` (`kWinningGame` move list, win at tick 1648 with 3 lives,
  no-cats loss at tick 421, determinism via `GameState` equality).
- At this point all 121 ported tests pass.

### Phase 4 (done): Headless runner
- `renderer.py` text helpers (`cat_sprite`, `mutant_sprite`, `status_name`,
  `place_result_message`, `cell_text`, `header_text`) and `headless.py`.
- `cats-vs-mutants --headless scripts/demo.txt` (and `python -m cats_vs_mutants ...`); usage errors exit 2, script errors exit 1.
- `test_headless.py`: stdout, stderr and exit code equal `tests/golden/<name>.*` byte for byte for every script; error cases.

### Phase 5 (done): Interactive curses UI
- `Renderer` class (board with 3 rows per lane, colors yellow/green/white, reverse-video cursor,
  end screen), `handle_key`, fixed 100 ms tick loop with stall protection, pause, quit.
- Unit-test `handle_key` against a real `Game` (cursor clamping, selection, place/remove
  messages); verify drawing manually in a terminal side by side with `./build/cats`.

### Phase 6 (done): Docs and polish
- README (build/run/test, controls, cast tables, rule details, ported from the C++ README).
- `ruff` clean; optional `mypy --strict` on `cats_vs_mutants.core`.
- Mutation testing is out of scope.

---

## 4. Definition of done
1. All 121 tests ported and passing, plus the new headless, key-handling and `cell_of(-1)` tests.
2. `cats-vs-mutants --headless scripts/demo.txt` output is identical to the C++ binary's.
3. `cats-vs-mutants` plays interactively in the macOS terminal with the same controls.
4. `cats_vs_mutants.core` imports nothing from `cats_vs_mutants.ui`, `curses`, `time`, `random` or I/O modules.

## 5. Decisions
1. Scope: the shipped game only. `NEW_FEATURES.md` is copied as reference, not implemented.
2. Mutation testing is not part of this exercise.
3. Project name: `cats-vs-mutants` (import package `cats_vs_mutants`, since Python package
   names cannot contain hyphens).

## 6. Result

All phases done. 223 tests pass; `ruff` is clean; `mypy --strict` passes on the core and plain
`mypy` on the whole package.

| Phase | Verification |
|---|---|
| 1 | 39 tick-free tests passed; the 5 tick-dependent ones failed only with `NotImplementedError` |
| 2 | 133 tests passed; per-file test counts match the C++ suite. Three planted bugs (floor division in `cell_of`, hairball edge `<=`→`<`, lose check `<=`→`<`) were each caught |
| 3 | All 121 ported tests pass; scripted game wins at tick 1648 with 3 lives, no-cats game is lost at tick 421 |
| 4 | 12 golden cases match the C++ binary byte for byte (stdout, stderr, exit code); 45 generated scripts (40 random, 5 demo replays with ~165 snapshots each) match too |
| 5 | Both games driven in a real pty with the same keys: every screen matches in text and attributes (colors, bold, reverse cursor), including the loss screen at tick 421 |
| 6 | README, core purity test, type checks |

Findings worth keeping:
- The original C++ tests would not catch a floor-division `cell_of` in a port; only the
  Python-only `cell_of(-1) == 0` test does.
- The text helpers moved out of `renderer.py` into `text.py`, and the game loop into
  `interactive.py`, so headless mode never imports `curses`.


### Later changes

- The project became an agent-orchestration exercise, adapted from `exercises/cpp/cats-vs-mutants`:
  `README.md` is now the exercise; the game description moved to `docs/SPEC.md`; the agents
  live in `.claude/agents/` and `docs/agents/`; `NEW_FEATURES.md` is adapted to Python.
- `tests/test_core_purity.py` now allows seeded `random.Random` instances in the core (needed by
  Endless mode) and rejects module-level `random` functions. The suite has 229 tests.
