# Step 4: Structure Outline

> Define the shape of the implementation -- what changes, in what order, with what checkpoints.

## Why This Step Matters

If the design document is "where we're going," the structure outline is "how we get there." And the difference between a good structure and a bad one is the difference between catching bugs after each step and catching them all at the end.

The natural tendency -- for both humans and AI agents -- is to plan horizontally: "first build all the models, then all the routes, then all the tests." This feels organized but has a critical flaw: nothing works until everything is assembled. You can't test the state machine until the checker exists. You can't test notifications until the state machine exists. If something is wrong in the models layer, you don't find out until you wire up the routes three steps later.

**Vertical slices** fix this. Each slice cuts through all relevant layers and produces something independently testable:

- **Slice 1:** CLI that checks a single URL and prints the result -> you can test it end-to-end
- **Slice 2:** State tracking with DOWN/UP transitions -> you can verify the state machine before adding the loop
- **Slice 3:** Continuous monitoring with logging and graceful shutdown -> builds on verified slices

After each slice, you run tests and confirm the checkpoint passes. If something is broken, you know it's in the slice you just built, not somewhere in a half-assembled horizontal layer.

Think of the structure outline like a C++ header file -- it defines the signatures, types, and phases without implementing them. It shows WHAT changes in each slice, not HOW (that's the plan's job).

## What You'll Do

1. Have the AI break the design into 2-5 vertical slices
2. For each slice, define: new files, modified files, key signatures, and verification steps
3. Review the slicing: Can each slice be tested independently? Does each slice cross all relevant layers?
4. Confirm the order makes sense -- later slices should build on earlier ones

### What Makes a Good Slice

- **Independently testable** -- You can run tests after completing this slice
- **Crosses layers** -- Touches model, logic, and interface (not just one layer)
- **Has a clear checkpoint** -- You know exactly how to verify it works
- **Builds on previous slices** -- Later slices extend, not rewrite, earlier work

### What Makes a Bad Slice

- "Build all the data models" (horizontal, not testable alone)
- "Set up the project" (no verifiable behavior)
- A slice so large it's effectively "build the whole thing"

## Input Artifacts

| Artifact | Description |
|----------|-------------|
| `thoughts/<task-id>/design.md` | Architecture document from Step 3 |
| `thoughts/<task-id>/research.md` | Codebase findings (brownfield, if applicable) |

## How To Execute

```
/structure
```

The skill will:
1. Read the design document (and research, if applicable)
2. Break the work into vertical, independently testable slices
3. For each slice: list new files, modified files, key type signatures, and verification checkboxes
4. Produce a ~2-page structure outline

### For This Exercise

The URL monitor naturally splits into three slices:

1. **Check URLs from CLI** -- Project skeleton + CMake config + HTTP checker + single-round CLI. Verify: `./url-monitor https://example.com` prints a check result.
2. **Transition detection** -- State machine + notifier wired into CLI. Verify: after N failures, a DOWN notification appears on stdout.
3. **Continuous monitoring** -- Poll loop + logger + graceful shutdown (signal handling). Verify: tool runs continuously, logs to file, exits cleanly on Ctrl+C.

Review whether the AI proposes similar slices. If it tries to split into more than 3-4 phases, push back -- each additional slice adds overhead. If it tries to do everything in one phase, push back -- you lose the ability to test incrementally.

## Output Artifacts

| Artifact | Description |
|----------|-------------|
| `thoughts/<task-id>/structure.md` | Vertical slice outline (~2 pages) listing: phases, new/modified files per phase, key type signatures, and verification checkboxes |

## Success Criteria

- [ ] Each phase is a vertical slice (crosses multiple layers, not just one)
- [ ] Each phase has concrete verification steps (not just "it works")
- [ ] Phases build on each other -- Phase 2 extends Phase 1, doesn't rewrite it
- [ ] Key type signatures are defined (you know the shape of data types without reading implementation)
- [ ] The total number of phases is manageable (2-5, not 10)
- [ ] No implementation details -- only WHAT changes, not HOW

## Common Mistakes

- **Horizontal slicing.** "Phase 1: all models. Phase 2: all routes." Each phase should produce testable behavior, not just code artifacts.
- **Missing verification steps.** If you can't describe how to test a slice, it's not a good slice.
- **Too granular.** More phases means more coordination overhead. Combine related work into slices that produce meaningful checkpoints.

## What's Next

Proceed to [Step 5: Plan](05-plan.md), where the AI expands each slice into tactical implementation details.
