# Boxer Cat (ambush trap)

## Why
Every cat today does one of three things: shoots, makes treats or soaks up bites. None of them
gives the player a cheap, clever move at the moment a lane is about to collapse. The Boxer Cat
hides in a cardboard box ("if it fits, it sits"). The first mutant that walks into its cell gets
punched and stunned, and the box is used up. It costs little, so the player has a real choice to
make: spend 25 treats to buy a Hissing Cat 50 more ticks of shooting, or save up for a wall. The
mechanic is new (a one-shot trap with a timed stun) and doesn't depend on any proposed feature,
so it can ship on its own now.

## Rules

Terms used below:
- **Eligible mutant**: alive (health above 0), not the Equivalent Mutant, not stunned, and not
  ambushed before.
- **Stunned**: the mutant's stun counter is above 0.
- **Ambush tick**: the tick on which the Boxer Cat springs. Called T below.

Stats and placement

1. New cat type **Boxer Cat**, sprite `[^.^]`. Cost 25, health 20, interval 0 (no timed action).
2. You place and remove it like any other cat: one cat per cell, the same `PlaceResult` outcomes,
   and no refund when removed. You may place it on a cell where a mutant is standing.
3. A Boxer Cat never fires, never makes treats, and is never a source of laser or hairball
   damage.

The ambush (tick step 6)

4. In step 6, mutants are processed in vector order (spawn order; mutants spawned on the same
   tick follow schedule order). When an eligible mutant is processed and a Boxer Cat is in that
   mutant's current cell, the Boxer Cat ambushes it:
   1. The mutant takes `ambushDamage` (40) damage.
   2. Its stun counter is set to `stunDuration` (50).
   3. Its move cooldown is set to its type's `moveInterval`.
   4. It is marked as ambushed. A mutant can be ambushed at most once in its life.
   5. The Boxer Cat is removed from the board at once, before the next mutant is processed.
   6. The mutant does not move on tick T, whatever `stunDuration` is.
5. One Boxer Cat ambushes exactly one mutant. Once the box is gone, any later mutant in the same
   cell is no longer blocked and moves normally in that same step 6.
6. A mutant that is not eligible treats a Boxer Cat like any other cat. It is blocked, it bites
   (10 damage every 10 ticks), and a Hopper that hasn't jumped yet jumps over it. This covers:
   - **The Equivalent Mutant.** It never triggers an ambush, so the box stays until bitten to
     death (2 bites).
   - **A mutant that was already ambushed** by another Boxer Cat.
   - **A mutant that is stunned** when a Boxer Cat is placed on its cell. The ambush is the only
     source of stun, so such a mutant has always been ambushed already; it stays ineligible after
     the stun ends. No separate rule is needed for it.
7. **Hopper**: the ambush is checked before the Hopper jump. An ambushed Hopper does not use its
   jump (it stays unjumped), so it can still jump over the next cat that blocks it. A Hopper that
   has already jumped is still eligible for an ambush.
8. A mutant whose health falls to 0 or below in step 4 or 5 of a tick is not alive in step 6, so
   it does not trigger an ambush on that tick. The Boxer Cat stays.
9. If the ambush damage brings the mutant's health to 0 or below, it is removed in step 8 like
   any other dead mutant. If it was the last mutant and every scheduled mutant has spawned, the
   game is won on tick T.

The stun

10. A stunned mutant:
    - does not move, and its move cooldown is frozen (not decremented) in step 6;
    - does not jump (Hopper);
    - does not bite in step 7, and its bite timer is reset to `biteInterval` on every stunned
      tick;
    - can still be hit by hairballs and lasers, triggers Hissing and Laser Cats, and counts as on
      the board for the win check.
11. At the end of step 7, every mutant with a stun counter above 0 decrements it by 1.
12. Timing, with `stunDuration` of 1 or more: the mutant is stunned on ticks T to
    T + stunDuration - 1. The first tick it is not stunned is T + stunDuration. Its first step is
    on tick **T + stunDuration + moveInterval - 1**, provided nothing blocks it.
    Defaults: a Runner ambushed on T first moves on T + 50, a Blob on T + 51, a Brute on T + 52.
13. With `stunDuration = 0`, the mutant still doesn't move on tick T (rule 4.6), is never
    stunned, and first moves on tick **T + moveInterval**.
14. When the stun ends while the mutant shares a cell with another cat (one placed on the stunned
    mutant's cell), the normal blocking rules apply from tick T + stunDuration. Its first bite on
    that cat lands on tick T + stunDuration + biteInterval - 1.

Boundaries

15. A Boxer Cat in column 0 works the same way. An ambushed mutant in cell 0 stays there for the
    stun and cannot reach home while stunned.
16. Game over: once the status is `Won` or `Lost`, ticks stop, so stun counters freeze along
    with everything else. Nothing more is applied.
17. If the player removes a Boxer Cat (`x` / `remove`), it is gone. Removing it never ambushes
    anyone.
18. Placing and stunning use no randomness.

Interaction with proposed features (these apply only if the feature has shipped)

19. Feature 1 (Knight): ambush damage **ignores armor** (a pounce, like the laser).
20. Feature 2 (Frosty Cat): a stunned mutant's `slowTicks` keeps decrementing as Frosty
    specifies for blocked mutants. The stun and the slow are independent. When the stun ends,
    a mutant that is still slowed uses the slowed cooldown on its next reset.
21. Feature 3 (Roomba): a sweep removes stunned mutants like any others.
22. Feature 4 (Bounties): a mutant killed by ambush damage is a kill and pays its bounty and
    combo.

## Out of scope
- No refund, upgrade or re-arming of a used Boxer Cat. To trap again, place a new one.
- No area effect. The ambush hits exactly one mutant.
- No ranged effect. The Boxer Cat does nothing to mutants outside its own cell.
- No changes to the shipped waves, the demo script or the other cats' stats.
- No new header text.

## Config
All new fields. The feature is **on by default**: the Boxer Cat is simply one more cat the player
can choose. Nothing changes unless one is placed. `scripts/demo.txt` and the existing tests never
place one, so the demo still ends `STATUS: Won` at tick 1648 with 3 lives and all 121 tests pass
unchanged. No on/off switch is needed.

| Name | Default | Meaning |
|---|---|---|
| `boxer` (cat stats: cost, health, interval) | `{25, 20, 0}` | Boxer Cat stats |
| `ambushDamage` | 40 | Damage dealt by the ambush |
| `stunDuration` | 50 | Value the stun counter is set to on ambush (ticks stunned, counting tick T) |

## Player-visible changes
- **Sprite**: `[^.^]` on the cat row.
- **Stunned mutants**: in the interactive game, drawn with their normal sprite in yellow when
  colours are available. No change without colours.
- **Key**: `6` selects the Boxer Cat (25). Key `5` is reserved for the Frosty Cat (Feature 2),
  whether or not it has shipped. The help line lists `6 Boxer 25`, in the same format as the
  existing entries (`1 Rich 50  2 Hissing 100 ...`), with the number taken from the configured
  Boxer cost.
- **Headless**: `place boxer <lane> <col>`.
- **Headless print**: a stunned mutant's line ends with ` stun <n>`, where `n` is the counter
  after the tick (49 right after a default ambush). Mutants that aren't stunned print exactly as
  today.

## Acceptance criteria
Unless stated otherwise: one lane is used (lane 0), `passiveIncome = 0`, `startingTreats` is
large enough for the placements, and the Boxer Cat is placed before tick 1. Spawn timing: an
event scheduled at tick 0 or tick 1 spawns on tick 1; an event scheduled at tick N >= 1 spawns on
tick N. Every mutant spawns at position 90. A blocked mutant's bite timer starts counting down on
the tick it first becomes blocked, so its first bite lands `biteInterval - 1` ticks after that
tick (the same as for any cat today).

1. **Runner is ambushed and stunned**
   Given a Boxer Cat at (0, 8) and one Runner scheduled at tick 0,
   When the game runs to tick 2,
   Then no cat is at (0, 8), the Runner is at position 89 with health 20 and stun counter 49.

2. **Stun length for an interval-1 mutant**
   Given scenario 1,
   When the game runs to tick 51, then to tick 52,
   Then the Runner is at 89 after tick 51 and at 88 after tick 52.

3. **Stun length for an interval-2 mutant**
   Given a Boxer Cat at (0, 8) and one Blob scheduled at tick 0,
   When the game runs,
   Then the ambush happens on tick 3 (Blob health 60), the Blob is at 89 after tick 53 and at 88
   after tick 54.

4. **The Equivalent Mutant does not trigger it**
   Given a Boxer Cat at (0, 8) and one Equivalent Mutant scheduled at tick 0,
   When the game runs,
   Then the Equivalent reaches 89 (cell 8) on tick 2 and is blocked from then on; the Boxer Cat
   has health 20 after tick 10 and 10 after tick 11; after tick 21 it is gone; the Equivalent is
   at 89 after tick 22 and at 88 after tick 23, with health 1 throughout and stun counter 0.

5. **Hopper keeps its jump**
   Given a Boxer Cat at (0, 8), a Sleepy Cat at (0, 5) and one Hopper scheduled at tick 0,
   When the game runs,
   Then after tick 3 the Hopper is at 89 (not 79) with health 40; after tick 112 it is at 59;
   after tick 113 it is at 49 (it jumped the Sleepy Cat).

6. **One box, one victim**
   Given a Boxer Cat at (0, 8) and two Runners both scheduled at tick 0 in lane 0,
   When the game runs to tick 2,
   Then the first Runner in spawn order is at 89 with health 20 and stun 49, and the second is
   at 88 with health 60 and stun 0.

7. **Ambushed once, then the next box is just a wall**
   Given Boxer Cats at (0, 8) and (0, 7) and one Runner scheduled at tick 0,
   When the game runs,
   Then after tick 61 the Runner is at 79 (it enters cell 7 and is blocked on that tick); after
   tick 69 the Boxer Cat at (0, 7) has health 20; after tick 70 it has health 10 and the Runner
   still has health 20; after tick 80 that Boxer Cat is gone and the Runner is still at 79; after
   tick 81 the Runner is at 78.

8. **Ambush can kill**
   Given `ambushDamage = 60`, a Boxer Cat at (0, 8) and one Runner scheduled at tick 0 (the only
   scheduled mutant),
   When the game runs to tick 2,
   Then there are no mutants and the status is `Won` at tick 2.

9. **A mutant killed earlier in the tick doesn't trigger it**
   Given `hissing = {100, 60, 2}`, `hairballSpeed = 79`, `hairballDamage = 60`, a Hissing Cat at
   (0, 0), a Boxer Cat at (0, 8) and one Runner scheduled at tick 0,
   When the game runs to tick 2,
   Then the Runner is gone and the Boxer Cat is still at (0, 8) with health 20.

10. **Stunned mutants don't bite**
    Given scenario 1, and after tick 2 a Sleepy Cat is placed at (0, 8),
    When the game runs,
    Then the Sleepy Cat has health 300 after tick 60 and 290 after tick 61, and the Runner is
    still at 89.

11. **Zero stun duration**
    Given `stunDuration = 0`, a Boxer Cat at (0, 8) and one Runner scheduled at tick 0,
    When the game runs,
    Then after tick 2 the Runner is at 89 with health 20 and stun 0; after tick 3 it is at 88.

12. **Placed on a walking mutant**
    Given one Runner scheduled at tick 0 and no cats,
    When the game runs to tick 5 (Runner at 85), a Boxer Cat is placed at (0, 8), and the game
    runs one more tick,
    Then after tick 6 the Runner is at 85 with health 20 and stun 49, and no cat is at (0, 8).

13. **Earlier-spawned Equivalent in the same cell**
    Given a Boxer Cat at (0, 8), an Equivalent Mutant scheduled at tick 0 (spawns on tick 1) and
    a Runner scheduled at tick 2 (spawns on tick 2, after the Equivalent in vector order),
    When the game runs,
    Then after tick 3 the Boxer Cat is gone, the Runner is at 89 with health 20 and stun 49, the
    Equivalent is at 89 with stun 0; after tick 5 the Equivalent is at 88.

14. **Cost, health and no action**
    Given exactly 25 treats and `passiveIncome = 0`,
    and one Blob scheduled at tick 1000 in lane 1 (so the game keeps running),
    When a Boxer Cat is placed at (0, 0) and the game runs 200 ticks,
    Then placing returns `Ok`, treats are 0 after placing and still 0 after 200 ticks, the cat has
    health 20, and no hairballs exist.

15. **Not enough treats**
    Given 24 treats,
    When a Boxer Cat is placed,
    Then the result is `NotEnoughTreats` and treats stay 24.

16. **Default config**
    Given `Config{}`,
    Then `cat(Boxer)` is `{25, 20, 0}`, `ambushDamage` is 40, and `stunDuration` is 50.

17. **Shipped game unchanged**
    Given the existing test suite and `scripts/demo.txt`,
    When they run,
    Then all 121 existing tests pass unchanged, and the demo ends `STATUS: Won` at tick 1648 with
    3 lives.

18. **Headless**
    Given a script with `place boxer 0 8` followed by enough ticks for an ambush and a `print`
    during the stun,
    Then the print shows `[^.^]` before the ambush, and after it a mutant line ending in
    ` stun <n>`.

## Open questions
None blocking. Note for the architect: rules 4.4 and 6 need each mutant to remember whether it
has been ambushed, and rules 10 to 13 need a per-mutant stun counter. How these are stored is up
to you, as long as existing aggregate initialisation and tests compile unchanged.
