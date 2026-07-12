# Step 2: Research the Codebase

> Build a factual map of what exists before forming opinions about what to change.

**Note:** This exercise is a greenfield project (no existing code), so you will **skip this step** and proceed directly to [Step 3: Design Discussion](03-design.md). Read this page to understand when and why research matters — you'll need it whenever you work with an existing codebase.

## Why This Step Matters

When an AI agent is asked to add a feature to an existing codebase, it faces a temptation: read just enough code to propose a solution, then start planning. The result is a plan that sounds reasonable but misses how the code actually works — it might propose a new authentication middleware when one already exists, or use a pattern the team abandoned two months ago.

The fix is to separate **fact-gathering** from **opinion-forming.** During research, the agent traces logic flows, maps existing endpoints, and catalogs patterns — without knowing what feature it's about to build. This separation is the key design move: by hiding the feature ticket during research, you prevent the agent from cherry-picking facts that support its preferred solution.

The output is a technical map: "Here is what the code does, here is where things are defined, here are the patterns in use." Not a plan. Not a recommendation. Just facts, with file and line references. You review this map before any implementation thinking begins.

This directly prevents a common failure mode where an AI produces a plan that reads well but rests on a wrong assumption about the codebase. When the plan is built on a factual foundation you've verified, wrong assumptions get caught early.

## What You'd Do (on a brownfield project)

1. Take the research questions from Step 1 (not the feature description — just the questions)
2. Have the AI investigate the codebase to answer each question
3. Produce a factual research document with file:line references
4. Review the findings for accuracy before proceeding

The agent's role during this step is **documentarian, not critic.** It describes what IS, not what SHOULD BE. No recommendations, no "this could be improved," no opinions on code quality.

## Input Artifacts

| Artifact | Description |
|----------|-------------|
| `thoughts/<task-id>/questions.md` | Research questions from Step 1 (brownfield variant) |
| The existing codebase | The code the agent will investigate |

**Important:** The agent should NOT read `task.md` during this step. It researches the codebase without knowing what feature is planned. This prevents confirmation bias.

## How To Execute

```
/research
```

The skill will:
1. Check if the project has existing application code
2. If greenfield: stop immediately (nothing to research)
3. If brownfield: read `questions.md`, investigate the codebase, and write findings
4. Produce a factual research document with references

## Output Artifacts

| Artifact | Description |
|----------|-------------|
| `thoughts/<task-id>/research.md` | Factual findings organized by question, ~300 lines max, with `file:line` references |

## Success Criteria

- [ ] Every finding includes a `file:line` reference
- [ ] The document contains zero recommendations or opinions
- [ ] Someone unfamiliar with the codebase could use the document to understand the relevant parts
- [ ] The agent did not read the task/feature description during research
- [ ] You verified the key findings are accurate (spot-checked the referenced code)

## When You Need This

- Adding a feature to an existing application
- Refactoring code you (or the AI) haven't worked with before
- Investigating a bug in unfamiliar code
- Any time the AI needs to understand existing patterns before proposing changes

## When You Skip This

- **Greenfield projects** (like this exercise) — there's no code to research
- Trivial changes where you already know the codebase well
- Documentation-only changes

## What's Next

Proceed to [Step 3: Design Discussion](03-design.md), where you'll align on architecture and scope using the facts gathered here (or the answers from Step 1, for greenfield).
