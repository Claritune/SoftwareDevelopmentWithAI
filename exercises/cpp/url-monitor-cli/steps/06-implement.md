# Step 6: Implement, Verify, and Review

> Execute the plan one slice at a time, verifying each before moving to the next.

## Why This Step Matters

Implementation is often the fastest step in this process -- and that surprises people. An AI agent can write a complete phase of code in minutes. But the speed doesn't come from the model typing faster. It comes from the alignment work in Steps 1-5.

When a plan is constrained by a validated design and a verified structure, the agent doesn't need to make judgment calls. It doesn't need to guess at patterns, invent type signatures, or decide on architecture. All of that was settled. The agent just translates a tactical plan into code.

Without the earlier steps, implementation is where everything goes sideways: the agent makes silent architectural decisions, picks wrong patterns, and produces code that technically works but doesn't fit the project. With the earlier steps, implementation becomes mechanical -- which is exactly what you want from AI-generated code.

The key discipline is **one phase at a time.** Don't ask the agent to implement everything at once. Build Phase 1, run the tests, verify the checkpoint, commit. Then Phase 2. Each commit is a known-good state you can roll back to if something breaks.

## What You'll Do

### Setting Up the Work Environment

Before starting implementation, set up an isolated branch:

1. Create a feature branch (or git worktree for larger projects)
2. Copy any untracked QRSPI artifacts to the working branch if needed
3. Confirm the plan is accessible from the working environment

If using worktrees:
```
/worktree
```

### Implementing Phase by Phase

For each phase in the plan:

1. Tell the agent to implement the current phase
2. The agent reads all files it will modify before making changes
3. The agent writes code and tests
4. Run verification: `cmake --build build && ctest --test-dir build --output-on-failure` and any manual checks
5. Update checkboxes in `plan.md` as verification steps pass
6. Commit the phase: one commit per phase, with a descriptive message
7. Pause and review before starting the next phase

```
/implement
```

### Reviewing the Code

After all phases are complete, review the code as you would any pull request:

- Read every file the agent created or modified
- Run the full test suite
- Try the tool manually with different inputs
- Check edge cases the tests might miss

This is non-negotiable: **you own the code.** The agent wrote it, but your name is on the commit. No generated code should make it into production without a human reading and understanding it.

Because you already aligned on design and structure, this review should contain few surprises. You're checking that the implementation matches the plan, not discovering architectural decisions for the first time.

### Creating the Pull Request

Once review is complete:

1. Push the branch
2. Create a PR that references the design decisions (the "why," not just the "what")
3. Include verification steps others can run

## Input Artifacts

| Artifact | Description |
|----------|-------------|
| `thoughts/<task-id>/plan.md` | Tactical plan from Step 5 (the primary working document) |
| All earlier artifacts | Design, structure, research -- for reference |

## How To Execute

```
# Set up isolated branch
/worktree

# Implement one phase at a time
/implement

# Create PR when done
/pr
```

### For This Exercise

Implement the three phases in order:

**Phase 1 -- Check URLs from CLI**
```bash
# After implementation:
cmake -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
./build/url-monitor --help
./build/url-monitor https://httpbin.org/status/200    # should print check result to stderr
ctest --test-dir build --output-on-failure             # should pass
```

**Phase 2 -- Transition Detection**
```bash
# After implementation:
cmake --build build
ctest --test-dir build --output-on-failure             # Phase 1 + Phase 2 tests pass
# State machine tests verify: UNKNOWN->UP, UNKNOWN->DOWN, UP->DOWN, DOWN->UP
```

**Phase 3 -- Continuous Monitoring**
```bash
# After implementation:
cmake --build build
./build/url-monitor https://httpbin.org/status/200 --interval 5    # runs continuously
# Ctrl+C exits cleanly
./build/url-monitor https://example.com --log-file monitor.log     # logs to file
ctest --test-dir build --output-on-failure                          # all tests pass
```

Commit after each phase. Don't combine phases into one commit.

## Output Artifacts

| Artifact | Description |
|----------|-------------|
| Working code | Implemented and tested application |
| Passing tests | Full test suite for all phases |
| Git commits | One commit per phase, with descriptive messages |
| Updated `plan.md` | All verification checkboxes checked |
| Pull request | (Optional) PR with design context and verification steps |

## Success Criteria

- [ ] Each phase was implemented and verified before starting the next
- [ ] All tests pass: `ctest --test-dir build --output-on-failure`
- [ ] The tool works manually: `./build/url-monitor <url>` produces expected output
- [ ] Each phase has its own commit
- [ ] You read and understood every line of generated code
- [ ] The implementation matches the design document -- no surprise patterns or features
- [ ] `plan.md` checkboxes are all checked

## Common Mistakes

- **Implementing everything at once.** "Just build the whole thing" throws away the vertical slice structure. You lose the ability to catch bugs incrementally.
- **Skipping manual testing.** Tests verify code correctness, not feature correctness. Actually run the tool and look at the output.
- **Not reading the code.** If you can't explain what a function does, you shouldn't ship it. The agent is your co-author, not your replacement.
- **Skipping commits between phases.** Each commit is a checkpoint. Without them, you can't roll back to a known-good state.

## Wrapping Up

At this point you've completed the full cycle:

1. **Questions** -- Surfaced ambiguities and made explicit decisions
2. **Research** -- Built a factual map of existing code (skipped for greenfield)
3. **Design** -- Aligned on architecture and caught pattern mismatches early
4. **Structure** -- Defined testable vertical slices with clear checkpoints
5. **Plan** -- Expanded into tactical details constrained by validated design
6. **Implementation** -- Executed mechanically, verified incrementally, reviewed thoroughly

The total time spent on alignment (Steps 1-5) is typically 30-60 minutes. The implementation (Step 6) might take 20-40 minutes. But without the alignment steps, implementation takes hours -- and much of that time is spent debugging misalignment, not writing code.

The speed comes from the alignment, not from the typing.
