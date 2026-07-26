---
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
   - Crosses all necessary layers (project setup, library, CLI, tests) for that slice
   - Can be tested independently after implementation
   - Has a clear verification checkpoint

   **Vertical** (correct):
   > Phase 1: Add URL checking -- .csproj, Checker.cs, Program.cs CLI entry point, CheckerTests.cs. Test: project builds and `dotnet run -- https://example.com` prints result.

   **Horizontal** (wrong):
   > Phase 1: All model classes. Phase 2: All service classes. Phase 3: All tests. Phase 4: Project configuration.

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

   **Files**: `path/to/File.cs`, `path/to/Other.cs`
   **Key changes**:
   - `Task<CheckResult> CheckAsync(string url)` -- new/modified
   - `record CheckResult(bool Success, int StatusCode, TimeSpan Duration)` -- new type

   **Verify**: `dotnet test` passes; `dotnet run -- https://example.com` prints result

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
