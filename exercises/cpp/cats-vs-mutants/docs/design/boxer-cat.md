# Design: Boxer Cat (ambush trap)
Spec: docs/features/boxer-cat.md

## Summary
A new `CatType::Boxer` with no timed action. Each `Mutant` gets two new trailing fields: a stun
counter (`stunTicks`) and a one-shot `ambushed` flag. The ambush happens inside the
per-mutant loop of `Game::moveMutants()` (step 6). Stunned mutants skip step 6 and the bite logic
in step 7. A new private step `wearOffStuns()` runs right after `resolveBites()` and decrements
the counters. Nothing changes unless a Boxer Cat is placed.

I prototyped this design in a scratch copy outside the repo (the repo itself was not edited). It
builds with zero warnings on Apple Clang, all 121 existing tests pass, the demo still
ends `STATUS: Won` at tick 1648 with 3 lives, and every acceptance criterion holds except three
with wrong expected numbers in the spec (AC4, AC7, AC13; see Decisions Q1 to Q3).

## Data changes

### `src/core/config.hpp`
- `enum class CatType { Rich, Hissing, Sleepy, Laser, Boxer };` (Boxer appended).
- New `Config` members, appended **after `seed`** (last, per the aggregate rule):
  ```cpp
  // Boxer Cat
  CatStats boxer{25, 20, 0};
  int ambushDamage = 40;
  int stunDuration = 50;  // stun counter value set on ambush (ticks stunned, counting tick T)
  ```
- `Config::cat()`: add `case CatType::Boxer: return boxer;`.

### `src/core/entities.hpp`
`Mutant` gets two new fields, added **after `hasJumped`** (last, before `operator==`):
```cpp
int stunTicks = 0;      // > 0 while stunned; set by a Boxer Cat ambush
bool ambushed = false;  // true once a Boxer Cat has ambushed this mutant (at most once)
```
The defaulted `operator==` picks them up automatically. No test builds a `Mutant` by aggregate
initialisation (checked with grep), and `spawnMutants` is the only place that does.

### `src/core/game.hpp`
New private members:
```cpp
void wearOffStuns();          // end of step 7
void ambush(Mutant& mutant);  // helper used by moveMutants
```
`wearOffStuns()` goes in the "Tick steps" block right after `resolveBites()`. `ambush()` goes
with the helpers (`damage`, etc.).

No new public API. QA reads everything through `state()`, `catAt()` and `config()`.

## Behaviour changes

### `Game::place` / `Game::remove`
No change. Boxer Cats go through the same code, so they get the same `PlaceResult` outcomes, can
be placed on a cell with a mutant in it, and give no refund. `place` pushes
`Cat{Boxer, lane, col, 20, 0}`. The cooldown of 0 is never read, because no step acts on Boxer
Cats.

### Step 2 `produceResources`, step 4 `fireCats`
No change. Both already filter by cat type (Rich, or Hissing/Laser), so a Boxer Cat never
produces, fires or deals laser damage (rule 3).

### Step 3 `spawnMutants`
Pass the new fields explicitly so the aggregate is fully initialised. This also rules out
`-Wmissing-field-initializers` on any compiler:
```cpp
Mutant{e.type, e.lane, config_.spawnPosition(), stats.health, stats.moveInterval,
       config_.biteInterval, false, 0, false}
```

### Step 5 `resolveHits`
No change. Stunned mutants are still valid targets (rule 10).

### Step 6 `moveMutants` (the ambush and the stun)
New per-mutant order inside the existing loop. Mutants are still processed in vector order:
```cpp
for (Mutant& m : state_.mutants) {
    if (m.health <= 0 || m.stunTicks > 0) continue;        // dead, or stunned: no move, no
                                                            // jump, cooldown frozen (rule 10)
    const Cat* blocker = catAt(m.lane, cellOf(m.position));
    if (blocker != nullptr && blocker->type == CatType::Boxer && !m.ambushed &&
        m.type != MutantType::Equivalent) {
        ambush(m);                                          // rule 4; no move on tick T (4.6)
        continue;
    }
    if (blocker != nullptr) { ...existing Hopper jump / blocked code, unchanged... }
    ...existing cooldown and step code, unchanged...
}
```
- The ambush check runs **before** the Hopper jump check, so an ambushed Hopper keeps
  `hasJumped == false` (rule 7). A Hopper that has already jumped is still eligible.
- "Eligible" from the spec maps to `health > 0 && stunTicks == 0 && !ambushed && type !=
  Equivalent`. The first two checks are the early `continue`. The `stunTicks == 0` part is
  technically redundant, since only an ambush can stun and an ambush sets `ambushed`, but the
  early `continue` is needed anyway for the stun rules.
- An ineligible mutant (Equivalent, already ambushed) falls through to the existing blocker code
  and treats the Boxer Cat like any other cat (rule 6).
- Rule 8 is covered by the existing `health <= 0` skip.
- Rule 5: the Boxer Cat is erased inside `ambush()`, so when the loop reaches the next mutant,
  `catAt` no longer finds it and that mutant moves normally in the same step.

`Game::ambush(Mutant& mutant)`:
```cpp
void Game::ambush(Mutant& mutant) {
    const int lane = mutant.lane;
    const int col = cellOf(mutant.position);
    damage(mutant, config_.ambushDamage);                              // 4.1
    mutant.stunTicks = config_.stunDuration;                           // 4.2
    mutant.moveCooldown = config_.mutant(mutant.type).moveInterval;    // 4.3
    mutant.ambushed = true;                                            // 4.4
    std::erase_if(state_.cats,                                         // 4.5
                  [&](const Cat& c) { return c.lane == lane && c.col == col; });
}
```
Pitfall: do **not** pass the `const Cat&` from `catAt` into `ambush` and capture it in the
`erase_if` predicate. `erase_if` moves elements while it runs, so that reference becomes invalid
partway through. Erase by lane and column, which are copied before anything changes.

`damage()` already ignores the Equivalent Mutant. That doesn't matter here because Equivalent is
never eligible. If Feature 1 (Knight) ships later, this call becomes `piercing = true` (spec
rule 19).

### Step 7 `resolveBites`
At the top of the loop body, after the existing `health <= 0` skip:
```cpp
if (m.stunTicks > 0) {
    m.biteCooldown = config_.biteInterval;   // rule 10: no bite, timer reset every stunned tick
    continue;
}
```
The rest is unchanged.

### Step 7, continued: new `Game::wearOffStuns()`
```cpp
void Game::wearOffStuns() {
    for (Mutant& m : state_.mutants) {
        if (m.stunTicks > 0) --m.stunTicks;
    }
}
```
This gives the timings in rules 12 and 13. Stunned on ticks T to T+S-1, then the cooldown resumes
from `moveInterval` on T+S, so the first step is on T+S+moveInterval-1. With S = 0 the counter is
never positive, and the first step is on T+moveInterval because of the cooldown reset in 4.3.

### Steps 8 to 10
No change. A mutant killed by ambush damage is removed in `removeDead()`, and the win is detected
in `checkEndConditions()` on the same tick (rule 9). Stunned mutants count as on the board.
`tick()` returns early once the game is over, so stun counters freeze (rule 16).

### Updated `tick()` (comment text the developer should use)
```cpp
state_.tick++;          // 1. Increment tick counter
produceResources();     // 2. Passive income and Rich Cat production
spawnMutants();         // 3. Spawn mutants scheduled for this tick
fireCats();             // 4. Cats fire (hairballs created, laser damage applied)
moveHairballs();        // 5. Move hairballs...
resolveHits();          //    ...and resolve hits
moveMutants();          // 6. Move mutants (stuns, Boxer ambushes, blocking, Hopper jumps)
resolveBites();         // 7. Resolve bites (stunned mutants don't bite)...
wearOffStuns();         //    ...then stun counters tick down
removeDead();           // 8. Remove dead cats and dead mutants
handleMutantsAtHome();  // 9. Handle mutants reaching home
checkEndConditions();   // 10. Check win and lose conditions
```
The order of the ten steps is unchanged.

## UI and headless

### `src/ui/renderer.cpp`
- `catSprite`: `case CatType::Boxer: return "[^.^]";`
- `catName`: `case CatType::Boxer: return "Boxer Cat";`
- Stunned mutants drawn in yellow:
  - Add `kStunnedColor = 4` to `ColorPair`, and `init_pair(kStunnedColor, COLOR_YELLOW, -1)` in
    the constructor's `has_colors()` block.
  - Pull the "frontmost mutant in this cell" loop out of `cellText` into an anonymous-namespace
    helper, `const Mutant* frontMutant(const Game&, int lane, int col)`. `cellText` uses it
    with the same behaviour as now.
  - In `drawBoard`, for `row == 1` when the text is a mutant sprite (`text[0] != ' '`): if
    `frontMutant(...)` is non-null and has `stunTicks > 0`, use `kStunnedColor` instead of
    `kMutantColor`. Without colours nothing changes.
- `Renderer::draw` help line: append `6 Boxer %d` with `cfg.boxer.cost`. See Decisions Q4 on the
  format.
- `headerText` is unchanged (spec: no new header text).

### `src/ui/main.cpp`
`handleKey`: `case '6': ui.selected = CatType::Boxer; break;`. Key `5` stays unbound (reserved for
Frosty).

### `src/ui/headless.cpp`
- `parseCat`: `if (name == "boxer") return CatType::Boxer;`
- `printState` mutant line: after `" hp " << m.health`, write `" stun " << m.stunTicks` only
  when `m.stunTicks > 0`, then `'\n'`. Mutants that aren't stunned print exactly as today.

## Compatibility
- The feature has no switch and is on by default (spec, "Config"). Nothing changes unless a
  Boxer Cat is in `state_.cats`. With no Boxer Cat, the new ambush branch never fires,
  `stunTicks` stays 0 on every mutant, so the stun `continue`s never fire and `wearOffStuns` does
  nothing. That reproduces the current behaviour exactly.
- `scripts/demo.txt` and the existing tests never place a Boxer Cat. In the prototype, all 121
  tests passed and the demo ended `TICK: 1648 ... LIVES: 3 ... STATUS: Won`.
- Source compatibility: new `Mutant` fields are last and have defaults, new `Config` fields are
  last, and the new `CatType` value is appended. Tests compare whole `GameState`s with `==`. That
  still works, and the comparison now also covers the new fields, which are deterministic.
- `-Wswitch` will flag `Config::cat`, `catSprite` and `catName` until they handle `Boxer`. Those
  are the only `switch`es on `CatType`.

## Testability
New file `tests/boxer_test.cpp`, added to `cvm_tests` in `tests/CMakeLists.txt`. No hooks were
added just for tests. `stunTicks` and `ambushed` are required by the rules and are part of
`GameState`.

Common setup (spec preamble): `Config c = quietConfig(); c.lanes = 1;` (quietConfig already gives
1000 treats and no passive income; `lanes = 1` is optional). Place cats before the first tick.
Waves are `std::vector<SpawnEvent>`, for example `{{0, 0, MutantType::Runner}}`. Add `kNever` from
`test_helpers.hpp` only if the test must keep running after the last mutant dies. `kNever` is in
lane 4, so it needs `lanes = 5`, and it must **not** be added to AC8. Use `tickTo(game, n)` for
"after tick n". Read state like this:
- Mutant: `game.state().mutants[i]` / `onlyMutant(game)`, fields `.position`, `.health`,
  `.stunTicks`, `.ambushed`, `.hasJumped`.
- Cat: `game.catAt(0, col)` (nullptr when gone), `->health`.
- `game.status()`, `game.state().tick`, `.treats`, `.hairballs`.

Spawn timing: an event at tick 0 **or** tick 1 spawns on tick 1, and an event at tick N >= 1
spawns on tick N, always at position 90. Mutants spawn with `moveCooldown = moveInterval`, so a
Runner at tick 0 is at 89 after tick 1. A Blob, Hopper or Equivalent reaches 89 after tick 2.

The values below were all checked against the prototype.

| AC | Setup | Assert |
|---|---|---|
| 1 | Boxer (0,8); Runner @0 | after 2: `catAt(0,8)==nullptr`, pos 89, hp 20, stunTicks 49, ambushed true |
| 2 | as 1 | after 51: pos 89, stunTicks 0; after 52: pos 88 |
| 3 | Boxer (0,8); Blob @0 | after 2: hp 100 and Boxer present; after 3: hp 60, stunTicks 49; after 53: pos 89; after 54: pos 88 |
| 4 | Boxer (0,8); Equivalent @0 | after 3: Boxer hp 20, Equivalent stunTicks 0, ambushed false; bites land on ticks **11 and 21** (Boxer hp 20 after 10, 10 after 11, gone after 21); Equivalent pos 89 after **22**, 88 after **23**; hp 1 throughout. See Q1. |
| 5 | Boxer (0,8), Sleepy (0,5); Hopper @0 | after 3: pos 89, hp 40, hasJumped false; after 112: pos 59; after 113: pos 49, hasJumped true |
| 6 | Boxer (0,8); Runner @0, Runner @0 | after 2: mutants[0] pos 89, hp 20, stun 49; mutants[1] pos 88, hp 60, stun 0, ambushed false |
| 7 | Boxers (0,8),(0,7); Runner @0 | after 61: pos 79, Boxer (0,7) hp 20; bites on **70 and 80** (hp 10 after 70 and after 71); Boxer gone after **80**; Runner pos 79 after 80, 78 after **81**, hp 20 throughout. See Q2. |
| 8 | `ambushDamage = 60`; Boxer (0,8); Runner @0 only (no `kNever`) | after 2: mutants empty, status `Won`, tick 2 |
| 9 | `hissing = {100, 60, 2}`, `hairballSpeed = 79`, `hairballDamage = 60`; Hissing (0,0), Boxer (0,8); Runner @0 | after 2: mutants empty, `catAt(0,8)` present with hp 20 |
| 10 | as 1; after tick 2 place Sleepy (0,8) | Sleepy hp 300 after 60, 290 after 61; Runner pos 89 at both |
| 11 | `stunDuration = 0`; Boxer (0,8); Runner @0 | after 2: pos 89, hp 20, stunTicks 0, ambushed true, Boxer gone; after 3: pos 88 |
| 12 | Runner @0, no cats; `tickTo(5)` (pos 85); place Boxer (0,8); `tick()` | after 6: pos 85, hp 20, stunTicks 49, `catAt(0,8)==nullptr` |
| 13 | Boxer (0,8); Equivalent @0, Runner **@2** | after 2: both at 89, Boxer present (Runner hasn't been processed in cell 8 yet); after 3: Boxer gone, Runner pos 89, hp 20, stun 49; Equivalent pos 89, stun 0, ambushed false; after 4: Equivalent 89; after 5: Equivalent 88. See Q3. |
| 14 | `startingTreats = 25` on quietConfig; waves `{{1000, 1, MutantType::Blob}}` (needs `lanes >= 2`) | `place(Boxer,0,0) == Ok`, treats 0; `tickN(200)`: treats 0, `catAt(0,0)->health == 20`, hairballs empty |
| 15 | `startingTreats = 24`, `{kNever}` | `place(Boxer, 0, 0) == NotEnoughTreats`, treats 24 |
| 16 | `Config{}` | `cat(Boxer).cost == 25`, `.health == 20`, `.interval == 0` (`CatStats` has no `==`; compare fields), `ambushDamage == 40`, `stunDuration == 50` |
| 17 | existing suite + `./build/cats --headless scripts/demo.txt` | 121 old tests pass unedited; last line contains `TICK: 1648`, `LIVES: 3`, `STATUS: Won` |
| 18 | script: `place boxer 0 8` / `print` / `tick 203` / `print` | first print has `cat     [^.^] lane 0 col 8 hp 20`; second print has `mutant  (x_x) lane 0 pos 89 hp 60 stun 48` (shipped Blob @200 in lane 0 is ambushed on tick 202), and no line for the lane-2 Blob contains `stun` |

Extra cases worth covering (the spec rules imply them; values verified):
- **Brute timing** (rule 12): Boxer (0,8), Brute @0. Ambushed on tick 4 (hp 260). Pos 89 after
  55, 88 after 56 (= T + 52).
- **Column 0** (rule 15): Boxer (0,0), Runner @0. Ambushed on tick 82 at pos 9. Still at pos 9
  after 131, pos 8 after 132. Lives unchanged.
- **Already-jumped Hopper is eligible** (rule 7): Sleepy (0,8), Boxer (0,7), Hopper @0. After 3:
  pos 79, hasJumped true, Boxer present. After 4: hp 40, stun 49, Boxer gone.
- **Stunned mutant still takes hits** (rule 10): as AC1, then after tick 2 place a Hissing Cat at
  (0,0) with `hissing = {100, 60, 10}` and `hairballSpeed = 79`. The Runner (hp 20) is killed on
  tick 12 while stunned (stun 40 after 11).
- **Removing a Boxer Cat** (rule 17): Boxer (0,8), `remove(0,8)` before tick 1, Runner @0. After
  2: pos 88, hp 60, ambushed false.
- **Game over freezes the stun** (rule 16): Boxer (0,8) plus a Runner that is ambushed, with
  `startingLives = 1` and another Runner in a second lane that reaches home. After `Lost`, extra
  `tick()` calls leave `state()` equal (`==`) to the snapshot.

## Implementation steps
Build (`cmake --build build`, zero warnings) and run `ctest --test-dir build` after each step. The
121 existing tests must pass after every step.

1. **Config and enum.** `config.hpp`: append `Boxer` to `CatType`, add `boxer`, `ambushDamage`,
   `stunDuration` after `seed`, and add the `cat()` case. `renderer.cpp`: add the `catSprite` /
   `catName` cases (needed to keep `-Wswitch` quiet). Build.
2. **Mutant fields.** `entities.hpp`: add `stunTicks` and `ambushed` after `hasJumped`.
   `game.cpp` `spawnMutants`: pass `0, false` explicitly. Build and run the tests.
3. **Ambush.** `game.hpp`: declare `ambush(Mutant&)`. `game.cpp`: implement it and add the stun
   skip and the ambush branch to `moveMutants`. Update the step 6 comment in `tick()`. Build and
   run the tests.
4. **Stun in step 7.** `game.hpp`: declare `wearOffStuns()`. `game.cpp`: add the stunned branch
   in `resolveBites`, implement `wearOffStuns`, and call it from `tick()` with the comments shown
   above. Build and run the tests.
5. **Headless.** `headless.cpp`: `boxer` in `parseCat`, ` stun <n>` suffix in `printState`. Run
   `./build/cats --headless scripts/demo.txt` and confirm `TICK: 1648`, `LIVES: 3`,
   `STATUS: Won`. Run the AC18 script from Testability and confirm the two lines.
6. **Interactive UI.** `main.cpp`: key `6`. `renderer.cpp`: help-line entry, `kStunnedColor`,
   `frontMutant` helper, yellow stunned mutants. Build, then check by hand in `./build/cats`.
7. **Docs.** `docs/SPEC.md`: Boxer Cat row in the Cast table, the stun/ambush notes in Rule
   details, the updated step 6/7 wording in Tick order, key `6` in Controls, and `boxer` in the
   Headless `place` comment.

## Decisions

### D1. Where the per-mutant ambush/stun state lives
- Options: (a) two trailing fields on `Mutant`; (b) parallel vectors or a map in `GameState`
  keyed by mutant index; (c) a generic `status effects` list on `Mutant`.
- **Choice: (a)** `int stunTicks = 0; bool ambushed = false;` appended after `hasJumped`.
- Why: index-keyed side tables break when `removeDead` / `handleMutantsAtHome` erase mutants.
  A generic effects list is speculative. (a) follows the existing precedent (`hasJumped`) and the
  Frosty design's `slowTicks`. It stays inside `GameState` and is compared by the defaulted `==`.
  Existing code compiles unchanged.

### D2. Where the ambush runs
- Options: a separate step before `moveMutants`, or inside the `moveMutants` loop.
- **Choice: inside the loop**, before the Hopper jump check.
- Why: rule 5 requires mutants to be processed one at a time. A later mutant in the same cell
  must see the box already gone and move in the same step. A separate pass would either block
  that mutant for a tick or need a second movement pass.

### D3. Where the stun counter decrements
- Options: inline at the end of each `resolveBites` iteration, a loop at the end of
  `resolveBites`, or a new private step.
- **Choice: new private step `wearOffStuns()`** called right after `resolveBites()` in `tick()`,
  shown as the second half of step 7 (the same pattern as `moveHairballs`/`resolveHits` in
  step 5).
- Why: it makes "end of step 7" (rule 11) visible in `tick()` itself and keeps `resolveBites`
  about bites.

### D4. Config field placement
- **Choice:** the new `Config` fields go after `seed`, not next to the other cat stats.
- Why: the architecture rule says new aggregate fields go last. Nothing positionally initialises
  `Config`, so this only costs some grouping.

### D5. Explicit initialisers in `spawnMutants`
- **Choice:** pass `0, false` explicitly even though the fields have defaults.
- Why: Apple Clang raises no warning either way (verified), but some GCC versions warn under
  `-Wmissing-field-initializers` (part of `-Wextra`) for an incomplete initialiser list. Being
  explicit guarantees zero warnings on any compiler.

### Questions for the product manager
**Q1. AC4 expected ticks are off by one (spec error).** The Equivalent reaches 89 (cell 8) on
tick 2, and the bite timer starts counting down on that same tick, exactly as it does today for
any blocking cat. So the bites land on ticks 11 and 21, not 12 and 22. The Boxer Cat is gone
after tick 21, and the Equivalent is at 88 after tick 23. The spec's "at 89 after tick 23" is
false. "Health 10 after tick 12" and "gone after tick 22" are still true.
*Recommendation:* change AC4 to "after tick 10 the Boxer Cat has health 20, after tick 11 it has
10; after tick 21 it is gone; the Equivalent is at 89 after tick 22 and at 88 after tick 23."

**Q2. AC7 final assertion is off by one (spec error).** The Runner enters cell 7 on tick 61, and
its bite timer starts that tick. Bites land on 70 and 80, the Boxer Cat dies on tick 80, and the
Runner steps to 78 on tick 81. I confirmed this matches today's rules by running the same
scenario with a 20-health Sleepy Cat. The spec's "after tick 82 the Runner is at 78" is false (it
is at 77).
*Recommendation:* "after tick 61 the Runner is at 79; after tick 70 the Boxer Cat at (0, 7) has
health 10 and the Runner still has health 20; after tick 80 that Boxer Cat is gone and the Runner
is at 79; after tick 81 the Runner is at 78."

**Q3. AC13 schedules the Runner at the wrong tick (spec error).** Events at tick 0 and tick 1
both spawn on tick 1, so the Runner spawns alongside the Equivalent. It is ambushed on tick 2
(stun 48 after tick 3, not 49), and the Equivalent is still in cell 9 at that point, so the
scenario never tests "Equivalent processed first, box survives for the Runner".
*Recommendation:* schedule the Runner at **tick 2**. Then every value in AC13 holds as written
(verified). Also amend the preamble: "an event scheduled at tick 0 or 1 spawns on tick 1; an
event at tick N >= 1 spawns on tick N".

**Q4. Help-line format.** The spec says the help line lists `6 Boxer (25)`, but the existing
line reads `1 Rich 50  2 Hissing 100 ...` with no parentheses.
*Recommendation:* follow the existing format, `6 Boxer 25`. Nothing tests the ncurses help line.

**Q5. (Confirm only)** Rule 6's third bullet ("stunned when a Boxer Cat is placed on its cell")
can only apply to a mutant that has already been ambushed, because ambush is the only source of
stun. The design covers it with the `ambushed` flag plus the stunned skip in step 6, so no extra
rule is needed. No spec change required.
