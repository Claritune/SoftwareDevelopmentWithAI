---
name: structure
description: Creates a vertical-slice structure outline with test checkpoints from the design. Use when running the QRSPI Structure phase with design.md and research.md, or when the user invokes /structure.
model: opus
argument-hint: "thoughts/qrspi/<id>/"
---

# Structure -- How Do We Get There?

Create a ~2-page structure outline that breaks the design into **vertical slices** -- each independently testable. Show the signatures, types, and phase boundaries -- not the full implementation.

## Input

Read `$ARGUMENTS/design.md` and `$ARGUMENTS/research.md`.

## Process

1. **Read both artifacts fully.**

2. **Break the work into vertical slices.** Each slice delivers end-to-end functionality:
   - Crosses all necessary layers (build system, library, CLI, tests) for that slice
   - Can be tested independently after implementation
   - Has a clear verification checkpoint

   **Vertical** (correct):
   > Phase 1: Add URL checking -- CMakeLists.txt, checker.h/cpp, main.cpp CLI entry point, checker_test.cpp. Test: binary builds and `./url-monitor https://example.com` prints result.

   **Horizontal** (wrong):
   > Phase 1: All header files. Phase 2: All implementation files. Phase 3: All tests. Phase 4: CMake configuration.

3. **Define the phase order.** Earlier phases should establish foundations that later phases build on. If Phase 3 fails, Phases 1-2 should still be independently valuable.

4. **For each phase, list**:
   - What it accomplishes (1-2 sentences)
   - Files affected
   - Key type signatures or interface changes
   - How to verify it works (automated command + what to check manually)

5. **Write `structure.md`** to the artifact directory:

   ```markdown
   # Structure Outline

   ## Approach
   [1-2 sentences: the implementation strategy from design.md, condensed]

   ## Phase 1: [Name]
   [What this phase delivers end-to-end]

   **Files**: `path/to/file.ext`, `path/to/other.ext`
   **Key changes**:
   - `ReturnType functionName(ParamType param)` -- new/modified
   - `struct NewType { Type field; };` -- new type

   **Verify**: [project test command] passes; [manual check description]

   ---

   ## Phase 2: [Name]
   ...

   ## Testing Checkpoints
   [Summary of what should be true after each phase, useful for resuming if context resets]
   ```

6. **Present the outline to the user** and wait for feedback. Common adjustments:
   - Reordering phases
   - Splitting a phase that's too large
   - Adding a testing phase between sensitive phases
   - Requesting more detail on a specific phase

## Output

- File written: `thoughts/qrspi/<id>/structure.md`
- Tell the user: "Next: run `/qrspi/5_plan thoughts/qrspi/<id>/`"

## Rules

- ~2 pages max. If it's longer, you're writing the plan, not the outline.
- Vertical slices, not horizontal layers. Every phase must cross all relevant layers.
- Signatures and types, not full implementation. Show WHAT changes, not HOW.
- Each phase must have a verification checkpoint.
- If the design calls for something that can't be sliced vertically, note it explicitly.

## When to Go Back

If you discover the design missed a critical constraint or made a decision based on incorrect assumptions about the codebase, tell the user and suggest re-running `/qrspi/3_design` rather than working around a flawed design.
