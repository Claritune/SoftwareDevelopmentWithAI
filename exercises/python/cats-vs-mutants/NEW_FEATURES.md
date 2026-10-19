# New Features

Five features for Cats vs Mutants, with an implementation plan and a unit test plan for each.

They were chosen because each one adds a different kind of logic that tests often get wrong:
arithmetic with a floor, timed status effects, one-shot flags, windows and caps, and seeded
randomness. Each is small enough to build and test in one sitting.

| # | Feature | What it adds | Testing angle |
|---|---|---|---|
| 1 | Knight mutant | An armored mutant; hairballs do less damage, lasers pierce | Subtraction with a floor at zero: the "negative damage heals" bug |
| 2 | Frosty Cat | A cat whose snowballs slow mutants | Timed effect: off-by-one at expiry, refresh vs stack |
| 3 | Roomba | One-shot lane guard that clears a lane instead of losing a life | Boolean flag consumed once, lane isolation |
| 4 | Bounties and combos | Treats for kills, bonus for quick chains | Window boundary (`<=` vs `<`), cap with `min` |
| 5 | Endless mode | Seeded procedural waves after the last wave | Testing random code: determinism, budgets, unlocks |

All paths below are relative to the project root; `core/` means `src/cats_vs_mutants/core/`
and `ui/` means `src/cats_vs_mutants/ui/`.

---

## Ground rules

These apply to every feature and are part of the definition of done. They are the
"Engineering ground rules" from `docs/SPEC.md`.

1. **Core stays pure.** All rules go in `cats_vs_mutants.core`. No I/O, no clock, no global
   state.
2. **Existing tests pass unchanged.** The 229 current tests must still pass with no edits,
   `scripts/demo.txt` must still end `STATUS: Won` at tick 1648 with 3 lives, and the headless
   output of every existing script stays byte-identical (`tests/golden/`). Any feature that
   would change the current game is behind a `Config` switch that defaults to **off**. The
   only allowed test edit is an assertion in `tests/test_interactive.py` on screen text that
   the feature's spec explicitly changes (Feature 2 is the one case here).
3. **Every number lives in `Config`**, so tests can build exact scenarios.
4. **Deterministic.** Same config, waves and inputs give the same `GameState`. Randomness only
   through a `random.Random` seeded from `Config.seed`, and only through its `random()` method.
5. **Clean tooling.** `ruff check`, `ruff format --check`, and `mypy --strict` on the core.

Python details that every feature runs into:

- **New dataclass fields go last, with a default.** Tests and the core build entities
  positionally (`Mutant(type, lane, position, ...)`, `SpawnEvent(1, 0, MutantType.BLOB)`), so a
  field added in the middle or without a default breaks them.
- **Enum-keyed dicts must stay complete.** A new `CatType` or `MutantType` member needs an entry
  in `Config.cat()` / `Config.mutant()` and in `ui/text.py` (`CAT_SPRITES`, `CAT_NAMES`,
  `MUTANT_SPRITES`, `MUTANT_NAMES`). A missing entry is a `KeyError` only when that member is
  looked up or drawn; neither ruff nor mypy catches it.
- **Headless cat names come from `CatType` values**, so a new member named `"frosty"` is
  accepted by `place frosty ...` without touching the parser.

---

## Feature 1: Knight mutant (armor)

### Rules
- New `MutantType.KNIGHT`, sprite `[>_<]`, health 120, 1 step every 2 ticks, **armor 10**.
- Armor reduces the damage of each hairball and snowball hit: `max(0, damage - armor)`.
  It never goes negative, so a hit can never heal.
- **Laser damage pierces armor** (full damage).
- Every other mutant has armor 0, so nothing about them changes.
- The Equivalent Mutant stays immune to everything, as today.
- Knights appear only in Endless mode (Feature 5), so the shipped waves stay unchanged.

### Config and entities
- `MutantStats` gains `armor: int = 0` as its last field. Add
  `knight: MutantStats = field(default_factory=lambda: MutantStats(120, 2, 10))`.
- `Config.mutant()` gains `MutantType.KNIGHT: self.knight`.

### Core changes (`core/game.py`)
- Change `_damage(mutant, amount)` to `_damage(mutant, amount, piercing)`:
  ```python
  if mutant.type == MutantType.EQUIVALENT:
      return
  armor = 0 if piercing else self._config.mutant(mutant.type).armor
  mutant.health -= max(0, amount - armor)
  ```
- Hairball and snowball hits call it with `piercing=False`; the laser with `piercing=True`.

### UI
- `ui/text.py`: add the Knight to `MUTANT_SPRITES` and `MUTANT_NAMES`. No input changes.

### Unit tests (`tests/test_armor.py`)

| Test | Setup | Expect | Guards against |
|---|---|---|---|
| `test_hairball_damage_is_reduced_by_armor` | Knight blocked in a Hissing Cat's own cell (col 8) | After tick 15: health 110 | `amount - armor` changed to `amount + armor`, armor ignored |
| `test_laser_pierces_armor` | Knight held at step 89 by a Sleepy Cat (col 8), Laser Cat at col 4 | After tick 30: health 90 | `piercing` flag ignored or inverted |
| `test_armor_greater_than_damage_never_heals` | `knight.armor = 25`, otherwise as the first test | Health stays exactly 120 | `max(0, ...)` removed (health would become 125) |
| `test_armor_equal_to_damage_deals_zero` | `knight.armor = 20` | Health stays 120 | `max(0, ...)` changed to `max(1, ...)` |
| `test_armor_one_below_damage_deals_one` | `knight.armor = 19` | Health 119 | Floor applied too early |
| `test_unarmored_mutants_take_full_damage` | Blob in the first test's setup | Health 80 | Armor read from the wrong mutant type |
| `test_knight_stats_come_from_config` | `Config()` | `mutant(MutantType.KNIGHT) == MutantStats(120, 2, 10)` | Wrong dict entry |
| `test_knight_can_be_killed` | Laser and Sleepy, run to tick 120 | Knight removed | `health <= 0` check skipped for Knights |

---

## Feature 2: Frosty Cat (slow)

### Rules
- New `CatType.FROSTY`, sprite `=*.*=`, cost 125, health 60, interval 20.
- Every 20 ticks, if a mutant is in its lane at or right of its cell, it spits a **snowball** (`*`).
  A snowball spawns and moves exactly like a hairball, uses the same hit rule, and deals 10 damage
  (reduced by armor).
- A snowball hit sets `slow_ticks = 60` on the mutant. A second hit **refreshes** it to 60;
  it never stacks to 120.
- **Slowed movement:** while `slow_ticks > 0`, the mutant's move cooldown resets to
  `move_interval * 2` instead of `move_interval`.
- **Expiry:** at the end of step 6, every mutant with `slow_ticks > 0` decrements it by 1.
  A hit on tick T affects the cooldown resets on ticks T to T+59; from tick T+60 the
  mutant is back to normal speed.
- The slow applies even when armor reduces the damage to 0 (a Knight is still slowed).
- The Equivalent Mutant is not hit, so it is never slowed (snowballs pass through it).

### Config and entities
- `frosty: CatStats = field(default_factory=lambda: CatStats(125, 60, 20))`,
  `snowball_damage: int = 10`, `slow_duration: int = 60`, `slow_factor: int = 2`.
  `Config.cat()` gains `CatType.FROSTY: self.frosty`.
- `class ProjectileKind(Enum)` with `HAIRBALL` and `SNOWBALL`.
- `Hairball` gains `kind: ProjectileKind = ProjectileKind.HAIRBALL` as its last field. The class
  and the `GameState.hairballs` list keep their names, so all existing tests run unchanged.
  A rename to `Projectile` can come later.
- `Mutant` gains `slow_ticks: int = 0` as its **last** field, after `has_jumped`.

### Core changes
- `_fire_cats`: treat Frosty like Hissing, but append a projectile with
  `kind=ProjectileKind.SNOWBALL`. Extract `_spit_projectile(cat, kind)` so the two cats share
  one code path.
- `_resolve_hits`: damage depends on `kind`; on a snowball hit, set
  `target.slow_ticks = cfg.slow_duration`.
- `_move_mutants`: on cooldown reset, use
  `interval * (cfg.slow_factor if m.slow_ticks > 0 else 1)`. After the block/move logic,
  `if m.slow_ticks > 0: m.slow_ticks -= 1`. Do this for blocked mutants too, so the slow keeps
  ticking down while a mutant stands still.

### UI and headless
- `ui/interactive.py`: key `5` selects the Frosty Cat (`SELECT_KEYS`).
- `ui/renderer.py`: the help line becomes
  `1 Rich 50  2 Hissing 100  3 Sleepy 50  4 Laser 175  5 Frosty 125`. This is pinned by
  `test_draw_shows_header_board_and_help` in `tests/test_interactive.py`; updating that one
  assertion is the allowed exception under ground rule 2, and the spec must list it.
- Snowballs are drawn as `*` in white (`ui/text.py`, `cell_text`); slowed mutants are drawn in
  cyan if colours are available (a new color pair in `ui/renderer.py`).
- Headless: `place frosty <lane> <col>` works as soon as `CatType.FROSTY = "frosty"` exists.
  Existing scripts never fire snowballs, so their output is unchanged.

### Unit tests (`tests/test_frosty.py`)
Most tests use `hairball_speed = 79` (with a Frosty Cat at col 0, the snowball reaches step 89 on
the tick it is fired), so the hit tick is known exactly.

| Test | Setup | Expect | Guards against |
|---|---|---|---|
| `test_spits_snowball_every_20_ticks` | Frosty col 0, Brute in lane | No projectile at tick 19; one `SNOWBALL` projectile at tick 20 | Wrong interval, wrong `kind` |
| `test_snowball_deals_ten_damage` | Runner held at 89 by a Sleepy Cat | Health 50 after the hit | Hairball damage used for snowballs |
| `test_hit_sets_slow_ticks` | As above | `slow_ticks == 59` right after the hit tick (set to 60, then one decrement) | Wrong duration, decrement skipped on hit tick |
| `test_slowed_mutant_moves_half_as_often` | Free-moving Runner hit on tick 20; remove the Frosty Cat right after, so it can't refresh the slow | Between ticks 21 and 79 it moves exactly 1 step per 2 ticks | `slow_factor` ignored, `*` changed to `+` |
| `test_slow_expires_after_duration` | Same (Frosty Cat removed after the first hit) | From tick 81 on it moves 1 step every tick | `slow_ticks > 0` changed to `>= 0` (never expires) |
| `test_second_hit_refreshes_not_stacks` | Two hits 20 ticks apart | `slow_ticks` after the second hit is 59 again, not 99 (40 left + 60, minus one) | `=` changed to `+=` |
| `test_slow_keeps_ticking_while_blocked` | Slowed Runner blocked by a Sleepy Cat for 60 ticks | `slow_ticks == 0` after 60 ticks | Decrement only on moving mutants |
| `test_armored_knight_is_slowed_but_unhurt` | Knight hit by a snowball | Health 120, `slow_ticks > 0` | Slow only applied when damage > 0 |
| `test_equivalent_is_never_slowed` | Equivalent hit by a snowball | `slow_ticks == 0`, health 1 | Equivalent check skipped for snowballs |
| `test_frosty_cost_and_health` | Place with exactly 125 treats | `PlaceResult.OK`, treats 0, health 60 | Wrong stats lookup |
| `test_hissing_still_spits_hairballs` | Hissing Cat as today | Projectile kind is `HAIRBALL` | Shared code path always using `SNOWBALL` |
| `test_key_5_selects_frosty` | `handle_key(ord("5"), ...)` | `ui.selected == CatType.FROSTY` | Key not wired |

---

## Feature 3: Roomba (lane guard)

### Rules
- Enabled by `Config.roombas` (default **False**, so the current game and tests are unchanged).
  The interactive UI turns it on.
- Each lane starts with one Roomba, drawn as `@` just left of column 0.
- In step 9, if a non-Equivalent mutant reaches home in a lane that still has its Roomba:
  - The Roomba sweeps the whole lane: **every** mutant in that lane except the Equivalent
    Mutant is removed, including ones far to the right.
  - **No life is lost** for that event.
  - The Roomba is used up (`roomba_ready[lane] = False`).
  - Mutants removed by a sweep give **no bounty** (Feature 4).
- If two mutants reach home in the same lane on the same tick, one sweep handles both and no
  life is lost.
- An Equivalent Mutant reaching home costs nothing and does **not** trigger the Roomba.
- Once a lane's Roomba is used, leaks in that lane cost lives as today.

### Config and entities
- `roombas: bool = False`
- `GameState` gains `roomba_ready: list[bool] = field(default_factory=list)` as its last field,
  sized to `lanes` in `Game.__init__`: all `True` if `roombas` is on, all `False` otherwise.

### Core changes
- Split `_handle_mutants_at_home` into:
  1. `_lanes_reached_home() -> list[int]` (non-Equivalent only),
  2. `_sweep_lane(lane: int)` for lanes with a ready Roomba,
  3. the existing life-loss and removal for everything else.
- Keep the step 9 comment in `tick()` up to date.

### UI
- `ui/renderer.py`: draw `@` (bold) left of the board for each lane with a ready Roomba.
  Nothing is drawn when `roomba_ready` is all `False`, so the pinned screens don't change.
- `ui/interactive.py` sets `config.roombas = True` for interactive play. Headless stays off, so
  `demo.txt` and the golden output are unchanged.

### Unit tests (`tests/test_roomba.py`)

| Test | Setup | Expect | Guards against |
|---|---|---|---|
| `test_first_leak_is_swept_without_losing_a_life` | `roombas = True`, Runner lane 0 | After tick 91: lives 3, board empty, `roomba_ready[0] is False` | Life still subtracted, flag not consumed |
| `test_second_leak_costs_a_life` | Second Runner spawned at tick 100 | After tick 190: lives 2 | Roomba reusable |
| `test_sweep_clears_the_whole_lane` | Runner + Blob in lane 0 (Blob at step 45 when the Runner leaks) | Both removed | Only the leaking mutant removed |
| `test_sweep_leaves_other_lanes_alone` | Plus a Blob in lane 1 | Lane 1 Blob untouched, `roomba_ready[1]` still `True` | Sweeping by index instead of lane |
| `test_equivalent_does_not_trigger_roomba` | Equivalent leaks | Lives 3, `roomba_ready[0]` still `True` | Equivalent check dropped |
| `test_sweep_spares_the_equivalent_mutant` | Runner leaks while an Equivalent is in the same lane | The Equivalent is still on the board | Sweep ignoring the Equivalent rule |
| `test_two_leaks_same_tick_one_sweep` | Two Runners spawned the same tick in lane 0 | Lives 3 | Sweep handled per mutant, not per lane |
| `test_disabled_by_default` | `Config()` | `roomba_ready` all `False`; a leak costs a life | Default flipped to on |
| `test_swept_mutants_give_no_bounty` | Bounties on (Feature 4) | Treats unchanged after the sweep | Sweep routed through the kill path |

---

## Feature 4: Bounties and combos

### Rules
- Enabled by `Config.bounties` (default **False**; see "Why default off" below). The
  interactive UI turns it on.
- When a mutant is removed in step 8 because its health is 0 or below, the player earns its
  **bounty**: Blob 10, Runner 10, Hopper 15, Knight 20, Brute 30. (The Equivalent Mutant
  can't die.)
- **Combo:** if the kill happens within `combo_window` (30) ticks of the previous kill
  (`tick - last_kill_tick <= combo_window`), `combo_level = min(combo_level + 1, max_combo)`,
  with `max_combo = 3`. Otherwise `combo_level = 0`.
- Each kill pays `bounty + combo_level * combo_bonus`, with `combo_bonus = 5`.
- Several kills on the same tick are processed in mutant list order. Each counts as within
  the window (delta 0), so the combo climbs during the tick.
- The first kill of the game never gets a combo.
- Removals by Roomba sweep or by reaching home are not kills.

### Config and entities
- `MutantStats` gains `bounty: int = 10` as its last field (after `armor`): Knight 20,
  Brute 30, Hopper 15, Equivalent 0, the others keep the default 10.
- `bounties: bool = False`, `combo_window: int = 30`, `max_combo: int = 3`, `combo_bonus: int = 5`.
- `GameState` gains, last, `combo_level: int = 0`, `last_kill_tick: int | None = None`,
  `kills: int = 0`, `bounty_earned: int = 0`.

**Why default off:** the C++ version defaults bounties to on, because no C++ test checks
treats after a kill. This port's golden tests compare the headless output, `TREATS:` included,
with the C++ build, so bounties on would change `tests/golden/demo.stdout` and the parity
tests. Off by default keeps them green; interactive play turns bounties on.

### Core changes
- Replace the mutant half of `_remove_dead` with `_collect_kills()`. When bounties are on, call
  `_award_bounty(mutant)` for each dead mutant, in list order, before removing it.
- `_award_bounty` updates the combo and adds to `treats`, `kills` and `bounty_earned`.

### UI
- `ui/text.py`, `header_text`: when bounties are on, the header gains `KILLS: n` and, while
  `combo_level > 0`, `COMBO x{level+1}`. With bounties off the header is exactly as today,
  which keeps the golden output and `test_interactive.py` unchanged.
- `ui/interactive.py` sets `config.bounties = True` for interactive play.

### Unit tests (`tests/test_bounty.py`)
Every test sets `bounties = True` unless it says otherwise. Kills come from a Laser Cat with
`laser_damage = 100`, with each Blob held at step 89 by a Sleepy Cat, so kills land on ticks
30, 60, 90, …

| Test | Setup | Expect | Guards against |
|---|---|---|---|
| `test_kill_pays_bounty` | One Blob | Treats +10 at tick 30, `kills == 1` | Bounty not added, added twice |
| `test_each_type_has_its_bounty` | One kill per type (parametrized) | 10 / 10 / 15 / 20 / 30 | Wrong lookup |
| `test_kill_inside_window_starts_combo` | Blobs killed at ticks 30 and 60, `combo_window = 30` | Total bounty 25 (10 + 15) | `<=` changed to `<` |
| `test_kill_outside_window_resets_combo` | Same, `combo_window = 29` | Total bounty 20 | Window check removed |
| `test_combo_is_capped` | Five kills, 30 ticks apart | Total 50 + (0 + 5 + 10 + 15 + 15) = 95 | `min` removed (would be 100) |
| `test_same_tick_kills_chain` | Two Blobs killed on the same tick | 10 + 15 = 25 | Combo only once per tick |
| `test_combo_resets_after_gap` | Kill, wait 100 ticks, kill | Second kill pays 10 | `combo_level` not reset |
| `test_first_kill_never_combos` | One kill with `combo_window = 1000` | Pays 10 | Missing `last_kill_tick` treated as tick 0 |
| `test_reaching_home_is_not_a_kill` | Runner leaks | Treats unchanged, `kills == 0` | Home removal routed through kills |
| `test_bounties_are_off_by_default` | `Config()`, one kill | Treats unchanged, `kills == 0` | Default flipped to on |
| `test_header_unchanged_when_bounties_off` | `Config()` | `header_text` has no `KILLS` | Header always extended |

---

## Feature 5: Endless mode (seeded waves)

### Rules
- Enabled by `Config.endless` (default **False**).
- When the normal waves are done and the board is clear, the game does **not** win. It
  generates the next wave, starting `endless_break` (100) ticks later, and keeps going until
  the player loses.
- `generate_wave(wave_number: int, start_tick: int, config: Config) -> list[SpawnEvent]` is a
  pure function in `core/waves.py`:
  - RNG: `rng = random.Random(config.seed + wave_number)`.
  - Do **not** use `randint`, `randrange` or `choice`. Python only guarantees that `random()`
    produces the same sequence for a seed across versions; the other methods may change, which
    would silently change every generated wave. Use a small helper
    `roll(rng: random.Random, lo: int, hi: int) -> int` returning
    `lo + int(rng.random() * (hi - lo + 1))`.
  - Budget: `40 + 20 * wave_number` points.
  - Mutant costs: Blob 10, Runner 10, Hopper 15, Knight 25, Brute 30.
  - Unlocks: Blob from wave 1, Runner from wave 2, Hopper and Brute from wave 3, Knight from wave 4.
  - Keep picking a random **unlocked type you can afford** until the remaining budget is below
    the cheapest unlocked cost.
  - Spawn spacing: `max(10, 40 - 3 * wave_number)` ticks; event *i* spawns at
    `start_tick + i * spacing`, in a random lane.
  - Every event's `wave` field is `wave_number`.
- `total_waves()` returns 0 in endless mode; the UI shows `WAVE n/∞`.

### Core changes
- `Game` keeps an `_endless_wave` counter. In `_check_end_conditions`, if endless is on and the
  win condition is met, call `_append_wave()` instead of setting `Status.WON`.
- `_append_wave` extends `self._waves` with the generated events. They are already in tick
  order and all later than the current tick, so the sort order still holds.
- `tests/test_core_purity.py` allows `random.Random` in the core but no module-level
  `random` functions, so an accidental `random.randint` fails the suite.

### UI and headless
- `cats-vs-mutants --endless` starts endless mode (`ui/main.py`). Keep the existing usage
  messages unchanged: `tests/test_headless.py` pins them.
- `ui/text.py`, `header_text`: `WAVE n/∞` when `total_waves()` is 0 in endless mode.
- Headless: a first script line `endless on` enables it (`ui/headless.py`).

### Unit tests (`tests/test_endless.py`)

| Test | Setup | Expect | Guards against |
|---|---|---|---|
| `test_same_seed_same_wave` | `generate_wave(3, 0, cfg)` twice | Equal lists | Hidden state, module-level `random` |
| `test_different_seed_different_wave` | Seeds 42 and 43 | Not equal | Seed ignored |
| `test_wave_number_changes_the_wave` | Waves 3 and 4, same seed | Not equal | `seed + wave_number` lost |
| `test_golden_wave` | Seed 42, wave 3 | Equals a pinned list (record it on first run) | Any change to the RNG or algorithm |
| `test_budget_is_spent_but_not_exceeded` | Waves 1 to 20 | Total cost ≤ budget, and leftover < cheapest unlocked cost | `<` vs `<=` in the loop, budget formula |
| `test_wave_one_is_only_blobs` | Wave 1 | All Blob | Unlock check |
| `test_knights_only_from_wave_four` | Waves 1–3 vs a Knight-heavy budget in wave 4 | No Knight before wave 4 | Off-by-one in the unlock |
| `test_spacing_shrinks_then_floors` | Waves 1, 10, 20 | Spacing 37, 10, 10 | `max` removed, wrong formula |
| `test_lanes_in_range_and_ticks_sorted` | Waves 1–20 | Every lane in `range(lanes)`, ticks strictly increasing | `roll` upper bound too high |
| `test_all_lanes_get_used` | Waves 1–20 combined | Every lane 0–4 appears at least once | `roll` upper bound too low (last lane never picked, yet always in range) |
| `test_endless_does_not_win` | `endless = True`, one Blob killed | Status still `PLAYING`, new events scheduled from tick + 100 | `WON` set before the endless check |
| `test_endless_can_still_be_lost` | No cats | Eventually `LOST` | Loss check skipped in endless |
| `test_endless_is_off_by_default` | `Config()` and no waves | Won on tick 1, as today | Default flipped |

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
phase: run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` and
`uv run --with mypy mypy --strict src/cats_vs_mutants/core`, check the demo, and commit.

### Phase 0: Prep
1. Run `uv sync` and `uv run pytest`, and confirm all 229 tests pass (45 of them need the C++
   build and are skipped without it).
2. Run `uv run cats-vs-mutants --headless scripts/demo.txt` and confirm `STATUS: Won` at tick
   1648 with 3 lives.

### Phase 1: Knight and armor
1. `core/config.py`: add `armor` to `MutantStats` (default 0), add `knight`, extend `mutant()`.
2. `core/config.py`: add `MutantType.KNIGHT`. Search for every dict keyed by `MutantType`
   (`grep -rn "MutantType\." src`) and add the Knight; `ui/text.py` has two.
3. `core/game.py`: give `_damage()` a `piercing` argument; update the hairball and laser call
   sites.
4. Write `tests/test_armor.py`.

### Phase 2: Frosty Cat
1. `core/config.py`: `CatType.FROSTY`, `frosty`, `snowball_damage`, `slow_duration`,
   `slow_factor`; extend `cat()`.
2. `core/entities.py`: `ProjectileKind`, `Hairball.kind`, `Mutant.slow_ticks` (both last).
3. `core/game.py`: `_spit_projectile`; Frosty in `_fire_cats`; snowball damage and slow in
   `_resolve_hits`; slowed cooldown and decrement in `_move_mutants`.
4. UI: key `5` (`interactive.py`), `*` and the Frosty sprite and name (`text.py`), help line
   and cyan for slowed mutants (`renderer.py`). Update the one pinned help-line assertion in
   `tests/test_interactive.py`.
5. Write `tests/test_frosty.py`.

### Phase 3: Bounties and combos
1. `core/config.py`: `bounty` in `MutantStats`, plus `bounties`, `combo_window`, `max_combo`,
   `combo_bonus`.
2. `core/entities.py`: combo fields on `GameState`.
3. `core/game.py`: `_collect_kills` and `_award_bounty`; `_remove_dead` keeps the cat half.
4. UI: `KILLS` and `COMBO` in the header when bounties are on; `interactive.py` turns them on.
5. Write `tests/test_bounty.py`.

### Phase 4: Roomba
1. `core/config.py`: `roombas`. `core/entities.py`: `roomba_ready`.
2. `core/game.py`: `__init__` sizes `roomba_ready`; split `_handle_mutants_at_home` as described.
3. UI: `@` markers (`renderer.py`); `interactive.py` enables Roombas for interactive play.
4. Write `tests/test_roomba.py` (including the no-bounty test).

### Phase 5: Endless mode
1. `core/waves.py`: `roll()` and `generate_wave()`.
2. `core/config.py`: `endless`, `endless_break`. `core/game.py`: `_endless_wave`,
   `_append_wave()`, endless branch in `_check_end_conditions`, `total_waves()` returns 0.
3. UI: `--endless` flag (`main.py`), `WAVE n/∞` (`text.py`); headless `endless on`.
4. Write `tests/test_endless.py`. Record the golden wave on first run, review it by eye, then
   pin it.

### Phase 6: Wrap-up
1. `docs/SPEC.md`: new cats, mutants, keys and rules (including the decisions above).
2. Optionally add a second demo script for Frosty Cats or endless mode. Leave
   `scripts/demo.txt` as it is: the golden output pins it.

---

## Definition of done
- All ground rules hold, including the unchanged existing tests, golden output and demo result.
- Each feature's tests exist, pass, and run in well under a second.
- Every row in the feature's test table is a test, and each one fails if its "Guards against"
  bug is planted by hand.
