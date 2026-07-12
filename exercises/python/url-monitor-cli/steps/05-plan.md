# Step 5: Plan

> Expand the structure into a tactical implementation document the agent can follow.

## Why This Step Matters

By this point, you've done all the hard alignment work:
- **Questions** ensured nothing was silently assumed
- **Design** aligned on architecture and patterns
- **Structure** defined testable vertical slices

The plan is where that investment pays off. Because the design and structure were already validated, the plan is constrained — it can't introduce new architectural decisions or change the slicing. It's purely tactical: which files to create, what code to write, which commands to run for verification.

This means you can **spot-check** the plan rather than performing a deep line-by-line review. If the design said "use httpx with synchronous Client" and the structure said "Phase 1 creates checker.py," the plan just fills in the implementation details for that checker. The strategic decisions are already settled.

Without the earlier alignment steps, a plan would be the first place architectural decisions appear — buried inside implementation details, mixed with boilerplate, hard to separate from tactical choices. That's how AI-generated plans become persuasive narratives that hide wrong assumptions. When the plan is constrained by validated design and structure, there's no room for that failure mode.

A good plan is also **self-contained**: an agent reading only the plan (without the earlier documents) should be able to implement the feature. This matters because implementation might happen in a different context window, a different session, or even by a different person.

## What You'll Do

1. Have the AI expand each phase from the structure into full implementation detail
2. Review for consistency with the design document
3. Confirm verification steps are concrete and runnable
4. Approve or adjust the plan

### What Goes in a Plan

For each phase:
- Exact file paths to create or modify
- Code snippets for key implementations (not every line — just the tricky parts)
- Test cases to write
- Verification commands (`pytest`, manual checks)
- Checkboxes to track progress during implementation

### What Doesn't Go in a Plan

- New architectural decisions (those belong in design)
- Refactoring unrelated code
- Features not in the structure
- Detailed explanations of why decisions were made (that's in the design doc)

## Input Artifacts

| Artifact | Description |
|----------|-------------|
| `thoughts/<task-id>/structure.md` | Vertical slices from Step 4 |
| `thoughts/<task-id>/design.md` | Architecture document from Step 3 |
| `thoughts/<task-id>/research.md` | Codebase findings (brownfield, if applicable) |

## How To Execute

```
/plan
```

The skill will:
1. Read the structure, design, and research documents
2. Expand each phase into tactical implementation steps
3. Include file paths, code snippets, test cases, and verification commands
4. Add checkboxes for progress tracking
5. Produce a self-contained implementation document

### For This Exercise

When reviewing the plan, check:
- **Does it stay in scope?** The plan should only implement what the design and structure describe. No surprise features.
- **Are verification steps runnable?** Each phase should end with specific `pytest` commands and manual checks you can actually execute.
- **Is it self-contained?** Could someone read just this plan and implement the feature without referencing the other documents?
- **Are the test cases specific?** "Test the checker" is too vague. "Test that a 500 response produces a CheckResult with success=False and status_code=500" is concrete.

## Output Artifacts

| Artifact | Description |
|----------|-------------|
| `thoughts/<task-id>/plan.md` | Tactical implementation document with: file paths, code snippets, test cases, verification commands, and progress checkboxes for each phase |

## Success Criteria

- [ ] Every phase from the structure outline has a corresponding section in the plan
- [ ] File paths are specific (not "create a module for X" but "create `src/url_monitor/checker.py`")
- [ ] Test cases are concrete with expected inputs and outputs
- [ ] Verification commands are copy-pasteable
- [ ] The plan introduces zero new design decisions beyond what's in `design.md`
- [ ] The plan is self-contained — readable without the other documents
- [ ] Progress checkboxes exist for all verification steps

## Common Mistakes

- **Scope creep.** The plan adds "nice to have" features not in the design. Push back — those go in a future iteration.
- **Vague verification.** "Verify it works" is not a verification step. "Run `pytest tests/test_checker.py -v` and confirm 4 tests pass" is.
- **Missing test cases.** Every new function or class should have tests specified in the plan.
- **Re-litigating design.** If the plan proposes a different pattern than the design, that's a red flag. Either update the design first, or follow the existing design.

## What's Next

Proceed to [Step 6: Implement](06-implement.md), where the agent executes the plan phase by phase with verification checkpoints between each slice.
