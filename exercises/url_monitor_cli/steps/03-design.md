# Step 3: Design Discussion

> Align on where you're going before planning how to get there.

## Why This Step Matters

This is the highest-leverage step in the entire process — and the one most people skip.

Here's what typically happens without it: the AI reads your requirements, picks a set of patterns and architectural choices, and buries them inside a detailed implementation plan. You skim the plan, it looks reasonable, you say "go ahead." Three hours later you discover it built the whole thing using a pattern your team moved away from last quarter, or it designed for horizontal scaling when you needed a simple foreground process.

The problem isn't that the AI made bad choices. The problem is that architectural decisions were hidden inside implementation details, where they're hard to spot. A plan that says "create a `URLChecker` class with a `check()` method that returns a `CheckResult`" reads perfectly well whether the underlying architecture is right or wrong.

The fix is to have the AI "brain dump" its understanding into a design document — separate from any code or implementation plan. The document covers:
- **Current state** — What exists now (from research, or "nothing" for greenfield)
- **Desired end state** — What the system should look like when done
- **Design decisions** — The patterns, libraries, and architectural choices the AI proposes
- **What we're NOT building** — Explicit scope boundaries
- **Open risks** — Things that could go wrong

You review this document specifically to catch misaligned patterns. If the AI picks a legacy pattern, you redirect it here — in a document, before any code exists. This is orders of magnitude cheaper than discovering the mismatch after implementation.

Think of it as the cheapest possible point for direction changes. A 10-minute review of a design doc can prevent a multi-hour rework cycle.

## What You'll Do

1. Have the AI read the task description and your answers (or research findings)
2. The AI may ask 0–5 remaining design questions
3. The AI produces a ~200-line design document
4. **You review the document for pattern mismatches** — this is the critical step
5. If anything is wrong, correct it now (the AI updates the document)

### What to Look For During Review

- Does the proposed architecture match how your team builds things?
- Are the library choices consistent with your existing stack?
- Does the "What We're NOT Building" section actually exclude what you want excluded?
- Are the data types and interfaces reasonable?
- Would the state machine / data flow actually work for your use case?

## Input Artifacts

| Artifact | Description |
|----------|-------------|
| `thoughts/<task-id>/task.md` | Task description |
| `thoughts/<task-id>/questions.md` | Questions from Step 1 |
| `thoughts/<task-id>/answers.md` | Your decisions (greenfield) |
| `thoughts/<task-id>/research.md` | Codebase findings (brownfield, if applicable) |

## How To Execute

```
/design
```

The skill will:
1. Read the task, questions, and answers (or research)
2. Present any remaining design questions
3. Write a design document covering architecture, patterns, scope, and risks
4. Present it for your review

### For This Exercise

When reviewing the design document, pay attention to:
- **Component breakdown** — Does the proposed architecture (CLI → Config → Checker → StateTracker → Notifier → Logger → PollLoop) make sense for a simple CLI tool? Is it over-engineered? Under-engineered?
- **State machine** — Does the proposed UP/DOWN/UNKNOWN state machine handle edge cases? What happens on the first check? What about flapping URLs?
- **Output channels** — Is the stdout/stderr separation clear? Would you actually want transition notifications on stdout and everything else on stderr?
- **Scope boundaries** — Is the "What We're NOT Building" section realistic? Are there things in scope that should be excluded, or vice versa?

If you disagree with any choice, say so. The AI will update the design. This is the cheapest possible point to change direction.

## Output Artifacts

| Artifact | Description |
|----------|-------------|
| `thoughts/<task-id>/design.md` | Architecture document (~200 lines) covering: component overview, data flow, state machine, key types, notification format, CLI interface, error handling, dependencies, and explicit scope boundaries |

## Success Criteria

- [ ] The document covers what you're building AND what you're not building
- [ ] Architectural choices are stated explicitly (not buried in code)
- [ ] You reviewed the proposed patterns and confirmed they match your intent
- [ ] Key data types and interfaces are defined (CheckResult, URLState, Transition, etc.)
- [ ] The data flow is clear: input → processing → output
- [ ] You made at least one correction or confirmation ("yes, that's right" counts)
- [ ] No code was written during this step

## Common Mistakes

- **Rubber-stamping.** If you say "looks good" without reading it, you've wasted the step. The whole point is catching misalignment before code exists.
- **Over-designing.** The document should be ~200 lines, not 20 pages. It's an alignment tool, not a specification.
- **Skipping scope boundaries.** The "What We're NOT Building" section prevents scope creep during implementation. Don't skip it.

## What's Next

Proceed to [Step 4: Structure Outline](04-structure.md), where you'll break the design into vertical slices that can be built and tested independently.
