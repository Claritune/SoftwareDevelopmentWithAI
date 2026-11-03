# QA: Boxer Cat (ambush trap)

Spec: `docs/features/boxer-cat.md`. Design: `docs/design/boxer-cat.md`.
Tests: `tests/boxer_test.cpp`. Headless script: `docs/qa/boxer-cat-headless.txt`.

## Conventions

- Every test starts from `quietConfig()` (1000 treats, no passive income, 5 lanes) and changes
  only the fields the rule needs. Lane 0 is the test lane.
- "after tick N" means `tickTo(game, N)`. Spawn timing: an event at tick 0 or 1 spawns on tick 1;
  an event at tick N >= 1 spawns on tick N, at position 90.
- `kNever` (lane 4) is added wherever the game must keep running after the last real mutant
  dies. It is left out of tests that check `Won`.
- Reference timings with the defaults (`stunDuration` 50), derived from the tick order and checked
  in the tests:

  | Mutant @0, Boxer at (0, 8) | At 89 after | Ambush tick T | Last stunned tick | First step |
  |---|---|---|---|---|
  | Runner (interval 1) | 1 | 2 | 51 | 52 |
  | Blob, Hopper (interval 2) | 2 | 3 | 52 | 54 |
  | Brute (interval 3) | 3 | 4 | 53 | 56 |

  A mutant is ambushed on the tick **after** it enters the Boxer Cat's cell, because step 6 checks
  the cell the mutant is in when it is processed, before it moves.

## Interpretations (flag for the product manager, none blocking)

- **I1.** Rule 4.3 ("move cooldown is set to its type's `moveInterval`") is only observable for
  a mutant whose cooldown is not already at `moveInterval` at the moment of the ambush. With an
  interval-1 Runner, or a Blob that stepped on the tick before the ambush, the reset makes no
  difference. The test (`AmbushResetsMoveCooldown`) uses a Blob that is ambushed mid-cooldown
  (Boxer placed on it at an odd tick).
- **I2.** With `stunDuration = 1` and `stunDuration = 0` the visible behaviour is the same (first
  step on T + moveInterval, stun counter 0 after tick T). Both are tested so that each formula in
  rules 12 and 13 is pinned at its edge.
- **I3.** Rule 3 ("never a source of laser or hairball damage") is tested by checking that a
  mutant walking through the Boxer Cat's lane is not damaged before it reaches the Boxer Cat's
  cell, that no hairballs appear, and that the Boxer Cat's `cooldown` field stays 0 (no step
  decrements it).
- **I4.** AC18 (headless print) lives in `src/ui`, which the test executable does not link.
  It is checked by running `docs/qa/boxer-cat-headless.txt` through `./build/cats --headless`,
  not by GoogleTest. Automating it as a CTest would need an `add_test` entry beyond the
  `cvm_tests` source list. I did not add one, because that is outside what QA may edit.

## Test plan

Suite names: `BoxerStats`, `BoxerAmbush`, `BoxerStun`, `BoxerOrder`, `BoxerHopper`,
`BoxerBoundary`.

| Test | Setup | Expect | Guards against |
|---|---|---|---|
| `BoxerStats.DefaultConfig` (AC16) | `Config{}` | `cat(Boxer)` = 25 / 20 / 0, `ambushDamage` 40, `stunDuration` 50 | Missing `switch` case returning `rich`; wrong defaults |
| `BoxerStats.PlacingCostsExactlyAllTreatsAndDoesNothing` (AC14, rule 3) | `startingTreats` 25, `passiveIncome` 0, Blob @1000 lane 1; Boxer (0,0); 200 ticks | `Ok`, treats 0 after placing and after 200 ticks, cat hp 20, cooldown 0, no hairballs | `cost > treats` changed to `>=` (exactly-enough rejected); Boxer treated as Rich or Hissing |
| `BoxerStats.OneTreatShortIsRejected` (AC15) | `startingTreats` 24 | `NotEnoughTreats`, treats 24, no cat | Cost not checked or deducted on failure |
| `BoxerStats.OneTreatOverLeavesOne` (AC14 boundary) | `startingTreats` 26 | `Ok`, treats 1 | Cost read from another cat's stats |
| `BoxerStats.SameCellRulesAsOtherCats` (rule 2) | Boxer (0,3); then Sleepy (0,3), Boxer (0,3), Boxer (5,0), Boxer (0,9) | `CellOccupied` x2, `OutOfBounds` x2 | Boxer bypassing the occupancy or bounds checks |
| `BoxerStats.RemoveGivesNoRefund` (rule 2) | Boxer (0,3), `remove(0,3)` | returns true, cat gone, treats 975 | Refund on remove |
| `BoxerStats.DoesNotHurtMutantsOutsideItsCell` (rule 3) | Boxer (0,0); Runner @0 | after 81: Runner pos 9, hp 60, no hairballs | Boxer acting as a ranged cat |
| `BoxerAmbush.RunnerIsAmbushedAndStunned` (AC1) | Boxer (0,8); Runner @0 | after 1: box present, pos 89, hp 60, stun 0; after 2: box gone, pos 89, hp 20, stun 49, ambushed | Ambush on the entry tick instead of the next; damage or stun not applied; box not removed |
| `BoxerAmbush.AmbushCanKillAndWinsOnThatTick` (AC8) | `ambushDamage` 60; Boxer (0,8); Runner @0 only | after 2: no mutants, `Won`, tick 2 | Ambush damage not checked by `removeDead`; win delayed a tick |
| `BoxerAmbush.AmbushOneShortOfLethalLeavesOneHealth` (AC8 boundary) | `ambushDamage` 59; as above | after 2: hp 1, `Playing` | `health <= 0` changed to `health < 1`-style off-by-one in the other direction |
| `BoxerAmbush.CustomAmbushDamageIsUsed` (rule 4.1) | `ambushDamage` 15 | after 2: hp 45 | Hard-coded 40 |
| `BoxerAmbush.MutantKilledByHairballEarlierInTickDoesNotSpringIt` (AC9, rule 8) | `hissing {100,60,2}`, `hairballSpeed` 79, `hairballDamage` 60; Hissing (0,0), Boxer (0,8); Runner @0 | after 2: no mutants, box present with hp 20 | Dead mutants (health 0) still ambushing in step 6 |
| `BoxerAmbush.MutantSurvivingTheHairballStillSpringsIt` (rule 8 boundary) | as AC9 but `hairballDamage` 59, plus `kNever` | after 2: Runner dead, box gone | `health <= 0` skip changed to `health <= 1` |
| `BoxerAmbush.EquivalentNeverTriggersIt` (AC4, rule 6) | Boxer (0,8); Equivalent @0 | after 2: pos 89; after 10 box hp 20; after 11 hp 10; after 20 hp 10; after 21 gone; Equivalent 89 after 22, 88 after 23; hp 1, stun 0, not ambushed throughout | Equivalent eligible; bite timer off by one |
| `BoxerAmbush.PlacedOnAWalkingMutant` (AC12) | Runner @0; `tickTo(5)` (pos 85); place Boxer (0,8); 1 tick | after 6: pos 85, hp 20, stun 49, box gone | Ambush only on cell entry, not on "is in the cell" |
| `BoxerAmbush.AmbushResetsMoveCooldown` (rule 4.3, I1) | Blob @0; `tickTo(5)` (pos 88, cooldown 1); place Boxer (0,8) | after 6: moveCooldown 2; after 56: pos 88; after 57: pos 87 | Cooldown not reset on ambush (would step on 56) |
| `BoxerAmbush.RemovingTheBoxWithAMutantInItsCellNeverAmbushes` (rule 17) | Boxer (0,8); Runner @0; after 1 `remove(0,8)` | after 2: pos 88, hp 60, not ambushed, stun 0 | `remove` springing the trap |
| `BoxerAmbush.RemovedBeforeArrivalDoesNothing` (rule 17) | Boxer removed before tick 1 | after 2: pos 88, hp 60 | Stale ambush state left behind |
| `BoxerAmbush.OnlyItsOwnLane` (rule 4, lanes) | Boxers (0,8), (1,8); Runner @0 lane 0 and Runner @0 lane 2 | after 2: (0,8) gone, (1,8) present hp 20; lane-2 Runner pos 88, hp 60, not ambushed | Erase by column only; ambush checked in the wrong lane |
| `BoxerAmbush.AlreadyAmbushedMutantTreatsNextBoxAsAWall` (AC7, rule 6) | Boxers (0,8), (0,7); Runner @0 | after 2: (0,7) present; after 60: pos 80; after 61: pos 79, box (0,7) hp 20; **after 69: hp 20**; after 70: hp 10, Runner hp 20; after 79: hp 10; after 80: gone, Runner 79; after 81: 78; Runner stun 0 and hp 20 throughout | `ambushed` flag never checked (second ambush); flag reset; bite timer off by one |
| `BoxerAmbush.StunnedMutantIgnoresBoxPlacedOnItsCell` (rule 6, third bullet) | as AC1; after 2 place Boxer (0,8) | after 51: box hp 20; after 60: 20; after 61: 10; after 71: gone, Runner 89; after 72: 88; Runner hp 20, never re-stunned | Second ambush after the stun ends |
| `BoxerAmbush.SameInputsSameState` (rule 18) | two games with AC7 setup, 100 ticks | `state() ==` | Hidden nondeterminism |
| `BoxerStun.RunnerStunLength` (AC2, rule 12) | as AC1 | after 50: stun 1, pos 89; after 51: stun 0, pos 89; after 52: 88 | Stun ending one tick early or late (`>` vs `>=`) |
| `BoxerStun.BlobStunLength` (AC3) | Boxer (0,8); Blob @0 | after 2: hp 100, box present; after 3: hp 60, stun 49, moveCooldown 2; after 52: cooldown still 2; after 53: 89; after 54: 88 | Cooldown decremented while stunned |
| `BoxerStun.BruteStunLength` (rule 12) | Boxer (0,8); Brute @0 | after 3: hp 300; after 4: hp 260, stun 49; after 55: 89; after 56: 88 | Formula broken for interval 3 |
| `BoxerStun.CustomStunDuration` (rule 12) | `stunDuration` 5; Runner | after 2: stun 4; after 6: 89, stun 0; after 7: 88 | Hard-coded 50 |
| `BoxerStun.StunDurationOneMovesOnTheNextTick` (rule 12 edge, I2) | `stunDuration` 1; Runner | after 2: stun 0, pos 89; after 3: 88 | Off by one at the smallest stun |
| `BoxerStun.ZeroStunStillSkipsTheAmbushTick` (AC11, rule 13) | `stunDuration` 0; Runner | after 2: pos 89, hp 20, stun 0, ambushed, box gone; after 3: 88, stun 0; after 4: 87, stun 0 | Missing `continue` after ambush (would move on T); unguarded decrement making the counter negative |
| `BoxerStun.ZeroStunBlobFirstStepsAtTPlusInterval` (rule 13) | `stunDuration` 0; Blob | after 3: ambushed; after 4: 89; after 5: 88 | Formula broken for interval 2 |
| `BoxerStun.StunnedMutantDoesNotBiteAndTimerRestarts` (AC10, rule 14) | as AC1; after 2 place Sleepy (0,8) | after 2: biteCooldown 10; after 51: 10; after 60: Sleepy 300; after 61: 290; Runner at 89 at both | Biting while stunned; bite timer not reset during stun (entered cell on tick 1 with timer 9, would bite on 60) |
| `BoxerStun.StunnedMutantStillTakesHairballs` (rule 10) | as AC1 + `kNever`; after 2 place Hissing (0,0) with `{100,60,10}`, `hairballSpeed` 79 | after 11: hp 20, stun 40; after 12: Runner gone | Stunned mutants skipped as targets / not triggering cats |
| `BoxerStun.StunnedMutantStillTakesLaser` (rule 10) | as AC1 + `kNever`; after 2 place Laser (0,4) | after 31: hp 20; after 32: gone | Stunned mutants skipped by the laser |
| `BoxerStun.StunnedMutantCountsForWinCheck` (rule 10) | as AC1, no `kNever` | after 51: `Playing`, 1 mutant | Stunned mutants ignored by the win check |
| `BoxerOrder.SecondRunnerInCellWalksOn` (AC6, rule 5) | Boxer (0,8); Runner @0 x2 | after 2: [0] 89 / hp 20 / stun 49; [1] 88 / hp 60 / stun 0 / not ambushed | Box removed only after the loop; both ambushed; second blocked a tick |
| `BoxerOrder.ThreeInCellOnlyFirstIsAmbushed` (rule 5) | Boxer (0,8); Runner @0 x3 | after 2: [0] ambushed; [1], [2] at 88, hp 60 | Same, with more than two |
| `BoxerOrder.EarlierEquivalentDoesNotUseUpTheBox` (AC13) | Boxer (0,8); Equivalent @0, Runner @2 | after 2: both 89, box present; after 3: box gone, Runner 89 / hp 20 / stun 49, Equivalent 89 / stun 0 / not ambushed; after 4: Equivalent 89; after 5: 88 | Equivalent consuming the box; box survives the Runner |
| `BoxerOrder.EarlierSpawnedMutantIsAmbushedFirst` (rule 4, vector order) | Boxer (0,8); Blob @0, Runner @2 | after 2: both 89; after 3: Blob hp 60 / stun 49, Runner 88 / hp 60 | Ambush picking the leftmost or last mutant instead of the first in vector order |
| `BoxerHopper.AmbushedHopperKeepsItsJump` (AC5, rule 7) | Boxer (0,8), Sleepy (0,5); Hopper @0 | after 3: 89 (not 79), hp 40, not jumped; after 111: 60; after 112: 59; after 113: 49, jumped | Jump checked before ambush; ambush setting `hasJumped` |
| `BoxerHopper.JumpedHopperIsStillEligible` (rule 7) | Sleepy (0,8), Boxer (0,7); Hopper @0 | after 3: 79, jumped, box present; after 4: hp 40, stun 49, box gone | `hasJumped` wrongly making a Hopper ineligible |
| `BoxerHopper.StunnedHopperDoesNotJump` (rule 10) | Boxer (0,8); Hopper @0; after 3 place Sleepy (0,8) | after 52: 89, not jumped; after 53: 79, jumped | Hopper jumping while stunned |
| `BoxerBoundary.ColumnZero` (rule 15) | Boxer (0,0); Runner @0 | after 81: pos 9, box present; after 82: hp 20, stun 49, box gone; after 131: 9, lives 3; after 132: 8; after 140: 0, lives 3; after 141: gone, lives 2 | Column 0 skipped; stunned mutant leaking home |
| `BoxerBoundary.GameOverFreezesStun` (rule 16) | `startingLives` 1, `stunDuration` 100; Boxer (0,8); Runner @0 lane 0, Runner @0 lane 1 | after 91: `Lost`, lane-0 Runner stun 10; 20 more `tick()`s: `state() ==` the snapshot, stun still 10 | Stun counters ticking after game over |

### Acceptance criteria to tests

| AC | Tests |
|---|---|
| 1 | `BoxerAmbush.RunnerIsAmbushedAndStunned` |
| 2 | `BoxerStun.RunnerStunLength` |
| 3 | `BoxerStun.BlobStunLength` |
| 4 | `BoxerAmbush.EquivalentNeverTriggersIt` |
| 5 | `BoxerHopper.AmbushedHopperKeepsItsJump` |
| 6 | `BoxerOrder.SecondRunnerInCellWalksOn`, `BoxerOrder.ThreeInCellOnlyFirstIsAmbushed` |
| 7 | `BoxerAmbush.AlreadyAmbushedMutantTreatsNextBoxAsAWall` (includes "health 20 after tick 69") |
| 8 | `BoxerAmbush.AmbushCanKillAndWinsOnThatTick`, `BoxerAmbush.AmbushOneShortOfLethalLeavesOneHealth` |
| 9 | `BoxerAmbush.MutantKilledByHairballEarlierInTickDoesNotSpringIt`, `BoxerAmbush.MutantSurvivingTheHairballStillSpringsIt` |
| 10 | `BoxerStun.StunnedMutantDoesNotBiteAndTimerRestarts` |
| 11 | `BoxerStun.ZeroStunStillSkipsTheAmbushTick` |
| 12 | `BoxerAmbush.PlacedOnAWalkingMutant` |
| 13 | `BoxerOrder.EarlierEquivalentDoesNotUseUpTheBox` |
| 14 | `BoxerStats.PlacingCostsExactlyAllTreatsAndDoesNothing`, `BoxerStats.OneTreatOverLeavesOne` |
| 15 | `BoxerStats.OneTreatShortIsRejected` |
| 16 | `BoxerStats.DefaultConfig` |
| 17 | Full `ctest` run (121 existing tests unedited) and `./build/cats --headless scripts/demo.txt` |
| 18 | Manual CLI check: `./build/cats --headless docs/qa/boxer-cat-headless.txt` (see I4) |

Spec rules 19 to 22 apply only once Features 1 to 4 ship. None has shipped, so they are not
tested now.

### Manual checks (interactive UI, cannot be unit tested)

| Check | How | Expect |
|---|---|---|
| Stunned mutant colour | `./build/cats`, place a Boxer Cat in the path of the first Blob (key `6`) | The ambushed Blob is drawn in yellow for 50 ticks (5 s), then green again |
| No colour terminal | `TERM=vt100 ./build/cats` | Stunned mutants look like any other mutant |
| Key `6` | Press `6` | "Selected: Boxer Cat [^.^]" |
| Key `5` | Press `5` | Selection unchanged |
| Help line | Look at the line under the board | Ends `4 Laser 175  6 Boxer 25` |

---

## Verification report (2026-10-19)

Tested against the uncommitted working tree (`src/core/config.hpp`, `entities.hpp`, `game.hpp`,
`game.cpp`, `src/ui/headless.cpp`, `main.cpp`, `renderer.cpp`).

### Build

- `cmake -S . -B build && cmake --build build --clean-first`: succeeds, **0 warnings** with
  `-Wall -Wextra -Wpedantic` (core, `cats`, `cvm_tests`).

### Tests

- `ctest --test-dir build --output-on-failure`: **163 / 163 pass** (121 existing + 42 new in
  `tests/boxer_test.cpp`).
- No existing test file was edited. The only change outside the new file is one line in
  `tests/CMakeLists.txt` that adds `boxer_test.cpp` to `cvm_tests`.

### Demo

- `./build/cats --headless scripts/demo.txt` ends
  `TREATS: 0   WAVE 3/3   LIVES: 3   TICK: 1648   STATUS: Won` (unchanged).

### Headless (AC18)

`./build/cats --headless docs/qa/boxer-cat-headless.txt` (relevant lines):

```
TICK: 0     cat     [^.^] lane 0 col 8 hp 20         (board row shows [^.^] in col 8)
TICK: 201   cat     [^.^] lane 0 col 8 hp 20
            mutant  (x_x) lane 0 pos 89 hp 100
TICK: 203   mutant  (x_x) lane 0 pos 89 hp 60 stun 48
            mutant  (x_x) lane 2 pos 63 hp 100        (no suffix: not stunned)
TICK: 250   mutant  (x_x) lane 0 pos 89 hp 60 stun 1
TICK: 251   mutant  (x_x) lane 0 pos 89 hp 60         (counter 0: suffix gone)
```

### Acceptance criteria

| AC | Result | Proven by |
|---|---|---|
| 1 | Pass | `BoxerAmbush.RunnerIsAmbushedAndStunned` |
| 2 | Pass | `BoxerStun.RunnerStunLength` |
| 3 | Pass | `BoxerStun.BlobStunLength` |
| 4 | Pass | `BoxerAmbush.EquivalentNeverTriggersIt` |
| 5 | Pass | `BoxerHopper.AmbushedHopperKeepsItsJump` |
| 6 | Pass | `BoxerOrder.SecondRunnerInCellWalksOn`, `BoxerOrder.ThreeInCellOnlyFirstIsAmbushed` |
| 7 | Pass | `BoxerAmbush.AlreadyAmbushedMutantTreatsNextBoxAsAWall`. The PM's new clause "Boxer Cat health 20 after tick 69" is **correct**: the Runner enters cell 7 on tick 61, its bite timer reads 9 after 61 and 1 after 69, and the first bite lands on tick 70. Also checked: hp 20 after 62 (blocked, not re-ambushed), 10 after 79, gone after 80. |
| 8 | Pass | `BoxerAmbush.AmbushCanKillAndWinsOnThatTick`, `BoxerAmbush.AmbushOneShortOfLethalLeavesOneHealth` |
| 9 | Pass | `BoxerAmbush.MutantKilledByHairballEarlierInTickDoesNotSpringIt`, `BoxerAmbush.MutantSurvivingTheHairballStillSpringsIt` |
| 10 | Pass | `BoxerStun.StunnedMutantDoesNotBiteAndTimerRestarts` |
| 11 | Pass | `BoxerStun.ZeroStunStillSkipsTheAmbushTick` (plus `ZeroStunBlobFirstStepsAtTPlusInterval`, `StunDurationOneMovesOnTheNextTick`) |
| 12 | Pass | `BoxerAmbush.PlacedOnAWalkingMutant` (plus `AmbushResetsMoveCooldown`) |
| 13 | Pass | `BoxerOrder.EarlierEquivalentDoesNotUseUpTheBox` |
| 14 | Pass | `BoxerStats.PlacingCostsExactlyAllTreatsAndDoesNothing`, `BoxerStats.OneTreatOverLeavesOne` |
| 15 | Pass | `BoxerStats.OneTreatShortIsRejected` |
| 16 | Pass | `BoxerStats.DefaultConfig` |
| 17 | Pass | 121 existing tests pass unedited; demo ends `STATUS: Won` at tick 1648, 3 lives |
| 18 | Pass | Manual CLI run of `docs/qa/boxer-cat-headless.txt` (output above). Not automated (see I4). |

The developer's focus areas are all covered: vector order (`BoxerOrder.*`), jumped and ambushed
Hoppers (`BoxerHopper.*`), `stunDuration = 0` (`BoxerStun.ZeroStun*`), placing on a walking
mutant (`PlacedOnAWalkingMutant`, `AmbushResetsMoveCooldown`), column 0
(`BoxerBoundary.ColumnZero`), stun frozen at game over (`BoxerBoundary.GameOverFreezesStun`),
and the headless ` stun <n>` suffix (AC18 run, including its disappearance at counter 0).

### Mutation check

To confirm the tests detect real bugs, I applied 20 single-line mutations to `game.cpp` in a
scratch copy outside the repo and ran the full suite on each. **All 20 were caught** by at
least one Boxer test. None of them broke a pre-existing test, which also shows the old suite
alone would not have noticed them.

| Mutation | Caught by (examples) |
|---|---|
| No `continue` after `ambush()` | `AmbushedHopperKeepsItsJump`, `StunnedHopperDoesNotJump` |
| Bite timer not reset while stunned | `StunnedMutantDoesNotBiteAndTimerRestarts` |
| Stunned mutants still bite | `StunnedMutantDoesNotBiteAndTimerRestarts`, `StunnedMutantIgnoresBoxPlacedOnItsCell` |
| `wearOffStuns()` run before `resolveBites()` | same two |
| Unguarded `--stunTicks` (goes negative) | `RunnerIsAmbushedAndStunned`, `ZeroStunStillSkipsTheAmbushTick`, 7 more |
| `ambushed` flag ignored | `AlreadyAmbushedMutantTreatsNextBoxAsAWall` |
| Equivalent eligible | `EquivalentNeverTriggersIt`, `EarlierEquivalentDoesNotUseUpTheBox` |
| Move cooldown not reset on ambush | `AmbushResetsMoveCooldown` |
| Box erased by column only (any lane) | `OnlyItsOwnLane` |
| Box not erased | 24 tests |
| Stun skip removed from step 6 / `> 0` changed to `> 1` | `RunnerStunLength`, `BlobStunLength`, 7 more |
| Dead mutants can spring the trap | `MutantKilledByHairballEarlierInTickDoesNotSpringIt` |
| Hopper jump checked before ambush | `AmbushedHopperKeepsItsJump` |
| Jumped Hopper ineligible | `JumpedHopperIsStillEligible` |
| Ambush sets `hasJumped` | `AmbushedHopperKeepsItsJump` |
| Damage hard-coded to 40 | `CustomAmbushDamageIsUsed`, AC8 pair |
| Stun hard-coded to 50 / `stunDuration + 1` | `CustomStunDuration`, `ZeroStun*`, many timing tests |
| Stun counters decrement after game over | `GameOverFreezesStun` |

### Defects

None found in `src/`. Every acceptance criterion and every extra case in the design's
Testability section holds with the values written.

### Observations (not defects)

- **O1. Step 6 ambush and the `blocker` pointer.** `Game::moveMutants`
  (`src/core/game.cpp:140-147`) keeps `blocker`, a pointer into `state_.cats`, and calls
  `ambush(m)`, which erases from `state_.cats`. This is safe only because the `continue` on
  line 146 runs straight after it, so `blocker` is never read again. If someone later removes
  that `continue`, `blocker` dangles. The mutation run showed this: without the `continue`, the
  stale non-null pointer still "blocked" the Runner, so only the Hopper tests noticed. The tests
  catch it, but a one-line comment at line 146 would make the hazard obvious. This is for the
  architect to decide; no change needed for this feature.
- **O2.** AC18 is verified by hand, not by CTest (I4). If the team wants it automated, an
  `add_test` that runs `cats --headless docs/qa/boxer-cat-headless.txt` with a
  `PASS_REGULAR_EXPRESSION` would do it. That needs someone allowed to edit CMake test
  registration beyond the `cvm_tests` source list.

### Manual checks still open

Not run by QA (they need an interactive terminal): yellow stunned mutants, no-colour fallback,
key `6` selects the Boxer Cat, key `5` does nothing, help line ends `6 Boxer 25`. See "Manual
checks" above. By code reading: `renderer.cpp` adds `kStunnedColor` (yellow) for a front mutant
with `stunTicks > 0`, and the help line is `... 4 Laser %d  6 Boxer %d` from `cfg.boxer.cost`.
`main.cpp` binds only `'6'`.

### Verdict

**Pass.** 0 warnings, 163/163 tests, demo unchanged, all 18 acceptance criteria pass
(AC18 by manual CLI check). The interactive UI items are left for a manual check.
