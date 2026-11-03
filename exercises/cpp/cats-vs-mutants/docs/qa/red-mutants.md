# QA: red mutants (view-only colour change)

Change under test: `src/ui/renderer.cpp` line 138, `Renderer::Renderer()`:
`init_pair(kMutantColor, COLOR_GREEN, -1)` became `init_pair(kMutantColor, COLOR_RED, -1)`.
Other uncommitted boxer-cat work in the same file was not reviewed here, except where it
touches mutant colour (the stunned-yellow override).

## Test plan

| Check | Method | Expect | Guards against |
|---|---|---|---|
| Mutant pair is red | Code review, renderer.cpp:138 | `COLOR_RED` | Edit missed, or applied to the wrong pair (cat or hairball) |
| Init only with colour support | Code review, renderer.cpp:134-142 | All `init_pair` calls inside `if (has_colors())`, `colors_` set only there | `init_pair` on a monochrome terminal, colour attributes used without `colors_` |
| Non-stunned mutant row is bold red | Code review, renderer.cpp:194-204 | row 1, text not blank or `"  .  "`, `text[0] != ' '` gives `kMutantColor \| A_BOLD` | Hairball/mutant test inverted, row 0 coloured as mutant |
| Stunned beats mutant colour | Code review, renderer.cpp:199-202 | `kStunnedColor` when `frontMutant(...)->stunTicks > 0`, otherwise `kMutantColor` (red again after the stun ends) | Override in the wrong order, red stuck after the stun |
| Cats yellow, hairballs white | Code review, renderer.cpp:137,139,196,198 | Unchanged | Collateral edit |
| No-colour terminal | Code review | `colors_ == false` skips colouring; text is still printed; `A_REVERSE` cursor is applied outside the `colors_` block | Board blank or cursor lost without colours |
| Headless unchanged | Old-line scratch build vs current build, `cmp` of full demo output | Byte-identical | Colour change leaking into headless output |
| Regression | Clean build, ctest, demo | 0 warnings, all pass, `STATUS: Won` at tick 1648, LIVES 3 | Anything else |

No unit test added. Colour pairs are only set and used inside `Renderer`, whose constructor
calls `initscr()`. The pair choice is inline in `drawBoard`, and `frontMutant` is in an
anonymous namespace, so nothing can be observed without a real ncurses terminal.
Glyph content (`cellText`) is already covered and this change does not touch it. Making the
pair choice testable would mean pulling it into a pure function such as
`short cellColorPair(const Game&, int lane, int col, int row)`. That is a decision for the
architect, and it is optional.

## Verification report (2026-10-19)

- **Build:** clean rebuild in a scratch build dir with `-Wall -Wextra -Wpedantic`. 0 warnings, 0 errors.
- **Tests:** 163/163 passed (ctest). No new tests.
- **Demo:** `cats --headless scripts/demo.txt` exits 0. The final state header is
  `TREATS: 0   WAVE 3/3   LIVES: 3   TICK: 1648   STATUS: Won`.
- **Headless unchanged:** a scratch copy of the current tree with only line 138 put back to
  `COLOR_GREEN` produces output byte-identical (`cmp`) to the current build. Reason:
  `headless.cpp` uses only `cellText`, `headerText`, sprite and name helpers, never `Renderer`.

| Item | Result | Evidence |
|---|---|---|
| Non-stunned mutants bold red | PASS | renderer.cpp:138, 198, 203 |
| Init inside `has_colors()` | PASS | renderer.cpp:134-142 |
| Stunned yellow takes precedence, red once `stunTicks == 0` | PASS | renderer.cpp:199-202 (checks `stunTicks` again every frame) |
| Cats yellow, hairballs white unchanged | PASS | renderer.cpp:137, 139 |
| No-colour terminal draws; cursor reverse works | PASS | renderer.cpp:195 (`colors_` guard), 205 (`A_REVERSE` outside guard) |
| Headless output unchanged | PASS | `cmp` identical |
| Build / tests / demo | PASS | above |

## Defects and notes

1. **Docs: the `| tail -1` demo check is wrong, but not for the reason reported.**
   (Pre-existing, not caused by this change.) `scripts/demo.txt` does not end with `print`.
   Its last command is `tick 100`, and its `print` commands are on lines 23, 39 and 55. The
   real cause is that `runHeadless` always ends with `=== FINAL STATE ===` plus
   `printState` (src/ui/headless.cpp:113-114). `printState` prints the STATUS header first,
   then the board, then one line per cat, mutant and hairball. So the last line is the last
   entity line (here `cat     =O.O= lane 0 col 3 hp 60`), and it was the same at HEAD. The
   comment's expected text `TICK: 1648, LIVES: 3, STATUS: Won` also does not match the real
   format, `LIVES: 3   TICK: 1648   STATUS: Won`. A working check would be
   `| grep STATUS | tail -1`. Affected lines:
   - docs/agents/dev-view.md:92, dev-rules.md:96, dev-headless.md:85, dev-app.md:78, dev-model.md:88, dev-waves.md:73
   - docs/design/agents/dev-view.md:87, dev-rules.md:91, dev-headless.md:80, dev-app.md:73, dev-model.md:83, dev-waves.md:68
   - .claude/agents/dev-view.md:87, dev-rules.md:91, dev-headless.md:80, dev-app.md:73, dev-model.md:83, dev-waves.md:68

   Owner: whoever maintains the agent docs. QA does not edit them.
2. No defects in the colour change itself.
