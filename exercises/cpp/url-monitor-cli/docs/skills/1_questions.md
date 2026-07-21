---
description: Decomposes a task into clarifying questions (greenfield) or neutral research questions (brownfield) for the QRSPI workflow. Use when decomposing a task, ticket, issue URL, or task description before Research or Design, or when the user invokes /question.
model: opus
argument-hint: "<ticket file, issue URL, or task description>"
---

# Question -- Decompose the Task

Transform a task description into questions that drive the next QRSPI phase. The question style depends on whether the project is **greenfield** (no application code yet) or **brownfield** (existing codebase to extend).

## Input

The user provides a task description, ticket file path, or issue reference (commonly `goal.md`).

## Process

1. **Read any provided files fully** before doing anything else -- especially `goal.md` when referenced.

2. **Assess project maturity** with light exploration (codebase-locator agent or quick scan):
   - **Greenfield**: No application runtime code -- no `src/`, `app/`, entry points (`main.cpp`, `main()` function), domain modules, application tests, or dependency manifests tied to implementation. May contain only goal docs, coding rules, and workflow skills.
   - **Brownfield**: Application code exists that the task will extend, modify, or integrate with.

   When uncertain, treat as greenfield if there is no runnable application code.

3. **Determine the artifact directory**:
   - With ticket number: `thoughts/qrspi/PROJ-1234-brief-description/` (use the project's ticket prefix)
   - Without ticket: `thoughts/qrspi/YYYY-MM-DD-brief-description/`

4. **Create the artifact directory** if it doesn't exist (e.g., `mkdir -p thoughts/qrspi/<id>/`).

5. **Write `task.md`** -- a clean 2-3 sentence description of what's being built and why, sourced from `goal.md` or the provided task description.

6. **Branch on project maturity** and write `questions.md`:

### Greenfield path

The goal is to surface **decisions the user must make** before design -- not to research a codebase that doesn't exist.

Read `goal.md` (or the task description) as the source of truth. Also scan for **existing constraints**: coding rules, conventions, or partial scaffolding the implementation should respect (e.g., `.cursor/rules/`, `docs/rules/`).

Generate **3-7 clarifying questions** about what to build:
- Surface ambiguities and architectural forks in the goal (runtime model, persistence, notification channels, scheduling, failure criteria, config source, scope boundaries)
- Each question must explain **why the answer changes the design**
- State the **default assumption** you'd make if the user doesn't answer
- Prioritize decisions that would otherwise be made silently by an agent
- Questions target **the user**, not a blind codebase researcher

Write `questions.md`:

```markdown
# Clarifying Questions

## Project Type
greenfield

## Goal Summary
[2-3 sentences from goal.md -- what we're building and why]

## Existing Constraints
[Documented rules or conventions found in the repo, or "None"]
- [constraint with file path]

## Questions
1. **[Decision area]**: [Question]
   - *Why it matters*: [architectural impact]
   - *Default if unanswered*: [assumption]

2. ...
```

Present questions to the user. **Wait for their answers** -- when provided, write `answers.md`:

```markdown
# Answers

1. **[Decision area]**: [User's answer]
2. ...
```

### Brownfield path

Spawn a **codebase-locator** agent to find which areas of the codebase relate to the task.

Generate **3-7 neutral research questions**:
- Each question should cause a researcher to explore a different relevant area of the codebase
- Questions must be **neutral** -- they ask what exists and how it works, never how to build something
- Prefer "trace the flow" questions that reveal architecture over yes/no questions

Good: "How does the middleware chain handle request authentication, and where are auth policies defined?"
Bad: "What's the best way to add a new authenticated endpoint?"

Write `questions.md`:

```markdown
# Research Questions

## Project Type
brownfield

## Context
[2-3 sentences describing which areas of the codebase to focus on.
Do NOT mention what is being built or why.]

## Questions
1. [Neutral, fact-seeking question]
2. [Neutral, fact-seeking question]
...
```

Present questions to the user and wait for approval or edits.

## Output

- Directory created: `thoughts/qrspi/<id>/`
- Files written: `thoughts/qrspi/<id>/task.md` and `thoughts/qrspi/<id>/questions.md`
- Greenfield with answers: also `thoughts/qrspi/<id>/answers.md`
- **Greenfield next step**: After answers are captured, run `/qrspi/3_design thoughts/qrspi/<id>/` (skip Research)
- **Brownfield next step**: run `/qrspi/2_research thoughts/qrspi/<id>/`

## Rules

### Greenfield
- `questions.md` MUST summarize the goal and list clarifying questions about the build
- `questions.md` MUST include `## Project Type` with value `greenfield`
- Questions must target decisions that significantly change architecture or scope
- Note existing constraints from rules docs even when application code doesn't exist yet
- Do NOT write neutral "what exists in the codebase" questions -- there is nothing to research yet
- Capture user answers in `answers.md` before proceeding to Design

### Brownfield
- `questions.md` must NOT contain the task description, goals, or desired behavior
- `questions.md` MUST include `## Project Type` with value `brownfield`
- `task.md` is read by later phases but NOT by Research
- The researcher who reads these questions should have no idea what feature is being built
- Each question should target a different area or concern

### Both
- If the task is too simple for 3 questions, tell the user -- QRSPI is for complex tasks
