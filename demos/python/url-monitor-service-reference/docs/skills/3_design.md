---
description: Design discussion — align on where we are going before planning how
model: opus
argument-hint: "thoughts/qrspi/<id>/"
---

# Design — Where Are We Going?

Create a ~200-line design document that captures the current state, desired end state, design decisions, and patterns to follow. This is the **lowest-cost point for direction changes** — get alignment here before investing in detailed planning.

## Input

Read `$ARGUMENTS/task.md` and `$ARGUMENTS/questions.md`.

Then branch on project type (from `questions.md` `## Project Type`):
- **Greenfield**: Also read `$ARGUMENTS/answers.md`. `research.md` is not expected — use `questions.md` Existing Constraints and user answers instead.
- **Brownfield**: Also read `$ARGUMENTS/research.md`.

## Process

1. **Read all applicable artifacts fully.** `task.md` tells you what we're building. For brownfield, `research.md` tells you what exists. For greenfield, `answers.md` tells you the user's decisions.

2. **Targeted exploration** (brownfield, or greenfield with existing constraint docs):
   - Brownfield: If research revealed areas needing deeper investigation, spawn **codebase-pattern-finder** or **codebase-analyzer** agents.
   - Greenfield: If `questions.md` lists existing constraints in rules docs, read those files directly for `file:line` references.

3. **Present open questions and wait for answers** — only for decisions NOT already resolved:
   - **Greenfield with `answers.md`**: Skip re-asking questions already answered. Only surface 0-3 remaining design forks not covered by the Q phase.
   - **Brownfield or greenfield without `answers.md`**: List 3-5 design questions requiring human judgment, with options and trade-offs grounded in research or constraints.
   - Wait for the user to respond before writing `design.md`.

4. **Write `design.md`** (~200 lines) to the artifact directory:

   ```markdown
   # Design Discussion

   ## Current State
   [Greenfield: empty project + documented constraints. Brownfield: what exists, with file:line refs]

   ## Desired End State
   [What we're building and how to verify it's correct]

   ## Patterns to Follow
   [Existing conventions the implementation should match, with file:line refs.
   Flag any patterns that should NOT be followed.]

   ## Design Decisions
   1. **[Decision name]**: [chosen option] — [why]
   2. **[Decision name]**: [chosen option] — [why]
   ...

   ## What We're NOT Doing
   [Explicit scope boundaries to prevent creep]

   ## Open Risks
   [Anything uncertain that might surface during implementation]
   ```

5. **Present the design to the user** for review. Iterate until they approve.

## Output

- File written: `thoughts/qrspi/<id>/design.md`
- Tell the user: "Next: run `/qrspi/4_structure thoughts/qrspi/<id>/`"

## Rules

- ~200 lines max. This is a steering document, not a specification.
- Every pattern reference must cite `file:line` from research or constraint docs.
- Do NOT re-ask questions already answered in `answers.md`.
- "Patterns to Follow" is critical — call out both good and bad patterns found in constraints or codebase.
- "What We're NOT Doing" prevents scope creep downstream.

## When to Go Back

- **Greenfield without `answers.md`**: Tell the user to answer clarifying questions first — re-run `/qrspi/1_question` or provide answers directly.
- **Brownfield with incomplete research**: Suggest re-running `/qrspi/1_question` and `/qrspi/2_research` before proceeding.
