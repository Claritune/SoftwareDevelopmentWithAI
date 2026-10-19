# New Features

Five features for Cats vs Mutants, with an implementation plan and a unit test plan for each.

They were chosen because each one adds a different kind of logic that tests often get wrong: arithmetic with a floor, timed status effects, one-shot flags, windows
and caps, and seeded randomness. Each is small enough to build and test in one sitting.

| # | Feature | What it adds | Testing angle |
|---|---|---|---|
| 1 | Knight mutant | An armored mutant; hairballs do less damage, lasers pierce | Subtraction with a floor at zero: the "negative damage heals" bug |
| 2 | Frosty Cat | A cat whose snowballs slow mutants | Timed effect: off-by-one at expiry, refresh vs stack |
| 3 | Roomba | One-shot lane guard that clears a lane instead of losing a life | Boolean flag consumed once, lane isolation |
| 4 | Bounties and combos | Treats for kills, bonus for quick chains | Window boundary (`<=` vs `<`), cap with `min` |
| 5 | Endless mode | Seeded procedural waves after the last wave | Testing random code: determinism, budgets, unlocks |

---

## Ground rules

These apply to every feature and are part of the definition of done.

1. **Core stays pure.** All rules go in `cvm_core`. No I/O, no clock, no global state.
2. **Existing tests pass unchanged.** The 121 current tests must still pass with no edits, and
   `scripts/demo.txt` must still end `STATUS: Won` at tick 1648 with 3 lives. Any feature that
   would change the current game is behind a `Config` switch that defaults to **off**.
3. **Every number lives in `Config`**, so tests can build exact scenarios.
4. **Deterministic.** Same config, waves and inputs give the same `GameState`. Randomness only
   through a `std::mt19937` seeded from `Config::seed`.
5. **Zero warnings** with `-Wall -Wextra -Wpedantic`.

---

## Feature 1: Knight mutant (armor)

### Rules
- New `MutantType::Knight`, sprite `[>_<]`, health 120, 1 step every 2 ticks, **armor 10**.
- Armor reduces the damage of each hairball and snowball hit: `max(0, damage - armor)`.
  It never goes negative, so a hit can never heal.
- **Laser damage pierces armor** (full damage).
- Every other mutant has armor 0, so nothing about them changes.
- The Equivalent Mutant stays immune to everything, as today.
- Knights appear only in Endless mode (Feature 5), so the shipped waves stay unchanged.

### Config and entities
- `MutantStats` gains `int armor = 0;`. Add `MutantStats knight{120, 2, 10};`.
- `Config::mutant()` gains `case MutantType::Knight: return knight;`.

### Core changes (`src/core/game.cpp`)
- Change `damage(Mutant&, int amount)` to `damage(Mutant&, int amount, bool piercing)`:
  ```cpp
  if (mutant.type == MutantType::Equivalent) return;
  const int armor = piercing ? 0 : config_.mutant(mutant.type).armor;
  mutant.health -= std::max(0, amount - armor);
  ```
- Hairball and snowball hits call it with `piercing = false`; the laser with `piercing = true`.

### UI
- `mutantSprite` / `mutantName`: add the Knight. No input changes.

### Unit tests (`tests/armor_test.cpp`)

| Test | Setup | Expect | Guards against |
|---|---|---|---|
| `HairballDamageIsReducedByArmor` | Knight blocked in a Hissing Cat's own cell (col 8) | After tick 15: health 110 | `amount - armor` changed to `amount + armor`, armor ignored |
| `LaserPiercesArmor` | Knight held at step 89 by a Sleepy Cat (col 8), Laser Cat at col 4 | After tick 30: health 90 | `piercing` flag ignored or inverted |
| `ArmorGreaterThanDamageNeverHeals` | `knight.armor = 25`, otherwise as the first test | Health stays exactly 120 | `max(0, ...)` removed (health would become 125) |
| `ArmorEqualToDamageDealsZero` | `knight.armor = 20` | Health stays 120 | `max(0, ...)` changed to `max(1, ...)` |
| `ArmorOneBelowDamageDealsOne` | `knight.armor = 19` | Health 119 | Floor applied too early |
| `UnarmoredMutantsTakeFullDamage` | Blob in the first test's setup | Health 80 | Armor read from the wrong mutant type |
| `KnightStatsComeFromConfig` | `Config{}` | `mutant(Knight)` is `{120, 2, 10}` | Wrong `switch` case |
| `KnightCanBeKilled` | Laser and Sleepy, run to tick 120 | Knight removed | `health <= 0` check skipped for Knights |

---

## Feature 2: Frosty Cat (slow)

### Rules
- New `CatType::Frosty`, sprite `=*.*=`, cost 125, health 60, interval 20.
- Every 20 ticks, if a mutant is in its lane at or right of its cell, it spits a **snowball** (`*`).
  A snowball spawns and moves exactly like a hairball, uses the same hit rule, and deals 10 damage
  (reduced by armor).
- A snowball hit sets `slowTicks = 60` on the mutant. A second hit **refreshes** it to 60;
  it never stacks to 120.
- **Slowed movement:** while `slowTicks > 0`, the mutant's move cooldown resets to
  `moveInterval * 2` instead of `moveInterval`.
- **Expiry:** at the end of step 6, every mutant with `slowTicks > 0` decrements it by 1.
  A hit on tick T affects the cooldown resets on ticks T to T+59; from tick T+60 the
  mutant is back to normal speed.
- The slow applies even when armor reduces the damage to 0 (a Knight is still slowed).
- The Equivalent Mutant is not hit, so it is never slowed (snowballs pass through it).

### Config and entities
- `CatStats frosty{125, 60, 20};`, `int snowballDamage = 10;`, `int slowDuration = 60;`,
  `int slowFactor = 2;`.
- `enum class ProjectileKind { Hairball, Snowball };`
- `Hairball` gains `ProjectileKind kind = ProjectileKind::Hairball;`. The struct and the
  `GameState::hairballs` vector keep their names, so all existing tests compile unchanged.
  A rename to `Projectile` can come later.
- `Mutant` gains `int slowTicks = 0;`. Add it **last**, so the existing aggregate
  initialisation in `spawnMutants` still works.

### Core changes
- `fireCats`: treat Frosty like Hissing, but push a projectile with `kind = Snowball`.
  Extract `spitProjectile(const Cat&, ProjectileKind)` so the two cats share one code path.
- `resolveHits`: damage depends on `kind`; on a snowball hit, set
  `target->slowTicks = config_.slowDuration`.
- `moveMutants`: on cooldown reset, use
  `interval * (m.slowTicks > 0 ? config_.slowFactor : 1)`. After the block/move logic,
  `if (m.slowTicks > 0) --m.slowTicks;`. Do this for blocked mutants too, so the slow keeps
  ticking down while a mutant stands still.

### UI and headless
- Key `5` selects the Frosty Cat. The help line lists it.
- Snowballs are drawn as `*` in white; slowed mutants are drawn in cyan if colours are available.
- Headless: `place frosty <lane> <col>`.

### Unit tests (`tests/frosty_test.cpp`)
Most tests use `hairballSpeed = 79` (with a Frosty Cat at col 0, the snowball reaches step 89 on
the tick it is fired), so the hit tick is known exactly.

| Test | Setup | Expect | Guards against |
|---|---|---|---|
| `SpitsSnowballEvery20Ticks` | Frosty col 0, Brute in lane | No projectile at tick 19; one Snowball-kind projectile at tick 20 | Wrong interval, wrong `kind` |
| `SnowballDealsTenDamage` | Runner held at 89 by a Sleepy Cat | Health 50 after the hit | Hairball damage used for snowballs |
| `HitSetsSlowTicks` | As above | `slowTicks == 59` right after the hit tick (set to 60, then one decrement) | Wrong duration, decrement skipped on hit tick |
| `SlowedMutantMovesHalfAsOften` | Free-moving Runner hit on tick 20; remove the Frosty Cat right after, so it can't refresh the slow | Between ticks 21 and 79 it moves exactly 1 step per 2 ticks | `slowFactor` ignored, `*` changed to `+` |
| `SlowExpiresAfterDuration` | Same (Frosty Cat removed after the first hit) | From tick 81 on it moves 1 step every tick | `slowTicks > 0` changed to `>= 0` (never expires) |
| `SecondHitRefreshesNotStacks` | Two hits 20 ticks apart | `slowTicks` after the second hit is 59 again, not 99 (40 left + 60, minus one) | `=` changed to `+=` |
| `SlowKeepsTickingWhileBlocked` | Slowed Runner blocked by a Sleepy Cat for 60 ticks | `slowTicks == 0` after 60 ticks | Decrement only on moving mutants |
| `ArmoredKnightIsSlowedButUnhurt` | Knight hit by a snowball | Health 120, `slowTicks > 0` | Slow only applied when damage > 0 |
| `EquivalentIsNeverSlowed` | Equivalent hit by a snowball | `slowTicks == 0`, health 1 | Equivalent check skipped for snowballs |
| `FrostyCostsAndHealth` | Place with exactly 125 treats | `Ok`, treats 0, health 60 | Wrong stats lookup |
| `HissingStillSpitsHairballs` | Hissing Cat as today | Projectile kind is `Hairball` | Shared code path always using Snowball |

---

## Feature 3: Roomba (lane guard)

### Rules
- Enabled by `Config::roombas` (default **false**, so the current game and tests are unchanged).
  The interactive UI turns it on.
- Each lane starts with one Roomba, drawn as `@` just left of column 0.
- In step 9, if a non-Equivalent mutant reaches home in a lane that still has its Roomba:
  - The Roomba sweeps the whole lane: **every** mutant in that lane except the Equivalent
    Mutant is removed, including ones far to the right.
  - **No life is lost** for that event.
  - The Roomba is used up (`roombaReady[lane] = false`).
  - Mutants removed by a sweep give **no bounty** (Feature 4).
- If two mutants reach home in the same lane on the same tick, one sweep handles both and no
  life is lost.
- An Equivalent Mutant reaching home costs nothing and does **not** trigger the Roomba.
- Once a lane's Roomba is used, leaks in that lane cost lives as today.

### Config and entities
- `bool roombas = false;`
- `GameState` gains `std::vector<bool> roombaReady;`, sized to `lanes` in the `Game`
  constructor. All `true` if `roombas` is on, all `false` otherwise.

### Core changes
- Split `handleMutantsAtHome` into:
  1. `std::vector<int> lanesReachedHome()` (non-Equivalent only),
  2. `sweepLane(int lane)` for lanes with a ready Roomba,
  3. the existing life-loss and removal for everything else.
- Keep the step 9 comment in `tick()` up to date.

### UI
- Draw `@` (bold) left of the board for each lane with a ready Roomba.
- `main.cpp` sets `config.roombas = true` for interactive play. Headless stays off, so
  `demo.txt` is unchanged.

### Unit tests (`tests/roomba_test.cpp`)

| Test | Setup | Expect | Guards against |
|---|---|---|---|
| `FirstLeakIsSweptWithoutLosingALife` | `roombas = true`, Runner lane 0 | After tick 91: lives 3, board empty, `roombaReady[0] == false` | Life still subtracted, flag not consumed |
| `SecondLeakCostsALife` | Second Runner spawned at tick 100 | After tick 190: lives 2 | Roomba reusable |
| `SweepClearsTheWholeLane` | Runner + Blob in lane 0 (Blob at step 45 when the Runner leaks) | Both removed | Only the leaking mutant removed |
| `SweepLeavesOtherLanesAlone` | Plus a Blob in lane 1 | Lane 1 Blob untouched, `roombaReady[1]` still true | Sweeping by index instead of lane |
| `EquivalentDoesNotTriggerRoomba` | Equivalent leaks | Lives 3, `roombaReady[0]` still true | Equivalent check dropped |
| `SweepSparesTheEquivalentMutant` | Runner leaks while an Equivalent is in the same lane | The Equivalent is still on the board | Sweep ignoring the Equivalent rule |
| `TwoLeaksSameTickOneSweep` | Two Runners spawned the same tick in lane 0 | Lives 3 | Sweep handled per mutant, not per lane |
| `DisabledByDefault` | `Config{}` | `roombaReady` all false; a leak costs a life | Default flipped to on |
| `SweptMutantsGiveNoBounty` | Bounties on (Feature 4) | Treats unchanged after the sweep | Sweep routed through the kill path |

---

## Feature 4: Bounties and combos

### Rules
- When a mutant is removed in step 8 because its health is 0 or below, the player earns its
  **bounty**: Blob 10, Runner 10, Hopper 15, Knight 20, Brute 30. (The Equivalent Mutant
  can't die.)
- **Combo:** if the kill happens within `comboWindow` (30) ticks of the previous kill
  (`tick - lastKillTick <= comboWindow`), `comboLevel = min(comboLevel + 1, maxCombo)`, with
  `maxCombo = 3`. Otherwise `comboLevel = 0`.
- Each kill pays `bounty + comboLevel * comboBonus`, with `comboBonus = 5`.
- Several kills on the same tick are processed in mutant vector order. Each counts as within
  the window (delta 0), so the combo climbs during the tick.
- The first kill of the game never gets a combo.
- Removals by Roomba sweep or by reaching home are not kills.

### Config and entities
- `int bounty` added to `MutantStats` (Knight 20, Brute 30, Hopper 15, the others 10,
  Equivalent 0).
- `bool bounties = true;`, `int comboWindow = 30;`, `int maxCombo = 3;`, `int comboBonus = 5;`
- `GameState` gains `int comboLevel = 0;`, `std::optional<int> lastKillTick;`,
  `int kills = 0;`, `int bountyEarned = 0;`.

**Why default on is safe:** no existing test checks treats after a kill, and placement in
`FullGame` happens at fixed ticks with enough treats either way. The first implementation step
is to run the existing suite with bounties on, to confirm that. If anything changes, default
to off instead and say so in the PR.

### Core changes
- Replace the mutant half of `removeDead` with `collectKills()`. For each dead mutant, in vector
  order, call `awardBounty(const Mutant&)`, then erase.
- `awardBounty` updates the combo, adds treats, `kills` and `bountyEarned`.

### UI
- Header gains `KILLS: n` and, while `comboLevel > 0`, `COMBO x{level+1}`.

### Unit tests (`tests/bounty_test.cpp`)
Kills come from a Laser Cat with `laserDamage = 100`, with each Blob held at step 89 by a
Sleepy Cat, so kills land on ticks 30, 60, 90, …

| Test | Setup | Expect | Guards against |
|---|---|---|---|
| `KillPaysBounty` | One Blob | Treats +10 at tick 30, `kills == 1` | Bounty not added, added twice |
| `EachTypeHasItsBounty` | One kill per type | 10 / 10 / 15 / 20 / 30 | Wrong lookup |
| `KillInsideWindowStartsCombo` | Blobs killed at ticks 30 and 60, `comboWindow = 30` | Total bounty 25 (10 + 15) | `<=` changed to `<` |
| `KillOutsideWindowResetsCombo` | Same, `comboWindow = 29` | Total bounty 20 | Window check removed |
| `ComboIsCapped` | Five kills, 30 ticks apart | Total 50 + (0 + 5 + 10 + 15 + 15) = 95 | `min` removed (would be 100) |
| `SameTickKillsChain` | Two Blobs killed on the same tick | 10 + 15 = 25 | Combo only once per tick |
| `ComboResetsAfterGap` | Kill, wait 100 ticks, kill | Second kill pays 10 | `comboLevel` not reset |
| `FirstKillNeverCombos` | One kill with `comboWindow = 1000` | Pays 10 | Missing `lastKillTick` treated as tick 0 |
| `ReachingHomeIsNotAKill` | Runner leaks | Treats unchanged, `kills == 0` | Home removal routed through kills |
| `BountiesCanBeDisabled` | `bounties = false` | Treats unchanged | Flag ignored |

---

## Feature 5: Endless mode (seeded waves)

### Rules
- Enabled by `Config::endless` (default **false**).
- When the normal waves are done and the board is clear, the game does **not** win. It
  generates the next wave, starting `endlessBreak` (100) ticks later, and keeps going until
  the player loses.
- `generateWave(int waveNumber, int startTick, const Config&)` is a pure function in
  `waves.cpp`:
  - RNG: `std::mt19937 rng(config.seed + waveNumber)`.
  - Do **not** use `std::uniform_int_distribution`. Its output isn't specified by the
    standard, so libc++ and libstdc++ give different waves from the same seed. Use a small helper
    `int roll(std::mt19937&, int lo, int hi)` built on `rng() % (hi - lo + 1)`.
  - Budget: `40 + 20 * waveNumber` points.
  - Mutant costs: Blob 10, Runner 10, Hopper 15, Knight 25, Brute 30.
  - Unlocks: Blob from wave 1, Runner from wave 2, Hopper and Brute from wave 3, Knight from wave 4.
  - Keep picking a random **unlocked type you can afford** until the remaining budget is below
    the cheapest unlocked cost.
  - Spawn spacing: `max(10, 40 - 3 * waveNumber)` ticks; event *i* spawns at
    `startTick + i * spacing`, in a random lane.
  - Every event's `wave` field is `waveNumber`.
- `totalWaves()` returns 0 in endless mode; the UI shows `WAVE n/∞`.

### Core changes
- `Game` keeps an `endlessWave_` counter. In `checkEndConditions`, if endless is on and the
  win condition is met, call `appendWave()` instead of setting `Won`.
- `appendWave` pushes the generated events onto `waves_`. They are already in tick order and
  all later than the current tick, so the sort order still holds.

### UI and headless
- `./cats --endless` starts endless mode.
- Headless: a first script line `endless on` enables it.

### Unit tests (`tests/endless_test.cpp`)

| Test | Setup | Expect | Guards against |
|---|---|---|---|
| `SameSeedSameWave` | `generateWave(3, 0, cfg)` twice | Equal vectors | Hidden state, `random_device` |
| `DifferentSeedDifferentWave` | Seeds 42 and 43 | Not equal | Seed ignored |
| `WaveNumberChangesTheWave` | Waves 3 and 4, same seed | Not equal | `seed + waveNumber` lost |
| `GoldenWave` | Seed 42, wave 3 | Equals a pinned list (record it on first run) | Any change to the RNG or algorithm |
| `BudgetIsSpentButNotExceeded` | Waves 1 to 20 | Total cost ≤ budget, and leftover < cheapest unlocked cost | `<` vs `<=` in the loop, budget formula |
| `WaveOneIsOnlyBlobs` | Wave 1 | All Blob | Unlock check |
| `KnightsOnlyFromWaveFour` | Waves 1–3 vs a Knight-heavy budget in wave 4 | No Knight before wave 4 | Off-by-one in the unlock |
| `SpacingShrinksThenFloors` | Waves 1, 10, 20 | Spacing 37, 10, 10 | `max` removed, wrong formula |
| `LanesInRangeAndTicksSorted` | Waves 1–20 | Every lane in `[0, lanes)`, ticks strictly increasing | `roll` upper bound too high |
| `AllLanesGetUsed` | Waves 1–20 combined | Every lane 0–4 appears at least once | `roll` upper bound too low (last lane never picked, yet always in range) |
| `EndlessDoesNotWin` | `endless = true`, one Blob killed | Status still Playing, new events scheduled from tick + 100 | `Won` set before the endless check |
| `EndlessCanStillBeLost` | No cats | Eventually Lost | Loss check skipped in endless |
| `EndlessIsOffByDefault` | `Config{}` and no waves | Won on tick 1, as today | Default flipped |

---

## Updated tick order

New work is shown in **bold**; the order of the existing steps doesn't change.

1. Increment tick counter
2. Passive income and Rich Cat production
3. Spawn mutants scheduled for this tick
4. Cats fire (hairballs, **snowballs**, laser damage)
5. Move projectiles and resolve hits (**armor**, **slow applied**)
6. Move mutants (blocking, Hopper jumps, **slowed cooldowns**, **slow decrement**)
7. Resolve bites
8. Remove dead cats and dead mutants (**bounties and combos**)
9. Handle mutants reaching home (**Roomba sweep**)
10. Check win and lose conditions (**endless: append next wave instead of winning**)

---

## Implementation plan

Build the features in this order. Each one depends only on those before it. After each
phase: build with zero warnings, run all tests, and commit.

### Phase 0: Prep
1. Add the five empty test files to `tests/CMakeLists.txt`, each with one placeholder
   `TEST` that's removed in its phase.
2. Run `cmake --build build && ctest --test-dir build` and confirm 121 tests pass.

### Phase 1: Knight and armor
1. `config.hpp`: add `armor` to `MutantStats` (default 0), add `knight`, extend `mutant()`.
2. `entities.hpp` / `config.hpp`: add `MutantType::Knight`. Check every `switch` on
   `MutantType` (`-Wswitch` will flag them).
3. `game.cpp`: change `damage()` to take `piercing`; update the hairball and laser call sites.
4. `renderer.cpp`: Knight sprite and name.
5. Write `armor_test.cpp`.

### Phase 2: Frosty Cat
1. `config.hpp`: `frosty`, `snowballDamage`, `slowDuration`, `slowFactor`; extend `cat()`.
2. `entities.hpp`: `ProjectileKind`, `Hairball::kind`, `Mutant::slowTicks` (added last).
3. `game.cpp`: `spitProjectile`; Frosty in `fireCats`; snowball damage and slow in `resolveHits`;
   slowed cooldown and decrement in `moveMutants`.
4. UI: key `5`, `*` sprite, cyan for slowed mutants; headless `frosty` name.
5. Write `frosty_test.cpp`.

### Phase 3: Bounties and combos
1. `config.hpp`: `bounty` in `MutantStats`, plus `bounties`, `comboWindow`, `maxCombo`, `comboBonus`.
2. `entities.hpp`: combo fields on `GameState` (`<optional>` include).
3. `game.cpp`: `collectKills` and `awardBounty`; `removeDead` keeps the cat half.
4. Run the **existing** suite before writing new tests (see "Why default on is safe").
5. UI: `KILLS` and `COMBO` in the header.
6. Write `bounty_test.cpp`.

### Phase 4: Roomba
1. `config.hpp`: `roombas`. `entities.hpp`: `roombaReady`.
2. `game.cpp`: constructor sizes `roombaReady`; split `handleMutantsAtHome` as described.
3. UI: `@` markers; `main.cpp` enables Roombas for interactive play.
4. Write `roomba_test.cpp` (including the no-bounty test).

### Phase 5: Endless mode
1. `waves.hpp/.cpp`: `roll()` and `generateWave()`.
2. `config.hpp`: `endless`, `endlessBreak`. `game.hpp/.cpp`: `endlessWave_`, `appendWave()`,
   endless branch in `checkEndConditions`, `totalWaves()` returns 0.
3. UI: `--endless` flag, `WAVE n/∞`; headless `endless on`.
4. Write `endless_test.cpp`. Record the golden wave on first run, review it by eye, then pin it.

### Phase 6: Wrap-up
1. README: new cats, mutants, keys and rules (including the decisions above).
2. Optionally extend `scripts/demo.txt` with a Frosty Cat, or add a second demo script for
   endless mode.

---

## Definition of done
- All ground rules hold, including the unchanged 121 tests and demo result.
- Each feature's tests exist, pass, and run in well under a second.
