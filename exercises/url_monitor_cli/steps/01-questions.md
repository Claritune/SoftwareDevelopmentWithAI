# Step 1: Ask the Right Questions

> Before writing a single line of code, figure out what you don't know.

## Why This Step Matters

Try this experiment: open your AI assistant and type "build me a CLI tool that monitors URLs for uptime." Watch what happens. The agent will immediately start writing code. It will silently choose Python or Node, pick an HTTP library, decide on a check interval, choose an output format, and architect a solution — all without asking you a single question.

The result might compile. It might even work. But it won't be what you wanted, because you never told it what you wanted. You just told it *roughly* what to build, and it filled in every gap with its own assumptions.

This is the core problem with jumping straight to code: the agent makes dozens of design decisions on your behalf, and you don't discover them until you're reading through hundreds of lines of generated code trying to figure out why it used `requests` instead of `httpx`, or why it's running as a daemon when you wanted a foreground process.

The fix is simple: **start by identifying what the agent doesn't know.** Write questions that force it to touch all the relevant decision points — scope, behavior, technical choices, output format, error handling. Each question should be one where a different answer would change the design. If the answer doesn't affect anything, it's not worth asking.

For a brand-new project (no existing code), these are *clarifying questions* — "what should this do?" For a project with existing code, these are *research questions* — "what does this code already do?" (See [Step 2](02-research.md) for that distinction.)

## What You'll Do

1. Write (or have your AI draft) a short goal document describing what you want to build
2. Have the AI read the goal and generate 5–15 clarifying questions, organized by topic
3. Answer each question with a concrete decision
4. Capture both questions and answers as versioned artifacts

The questions should cover:
- **Scope & behavior** — What does it do? What does it explicitly not do?
- **Technical decisions** — Which libraries, frameworks, patterns?
- **Output & interfaces** — What does the user see? What format?
- **Testing & packaging** — How will it be verified? How will it be installed?

Each question should include *why the answer matters* — what changes in the design depending on the answer.

## Input Artifacts

| Artifact | Description |
|----------|-------------|
| `goal.md` | A short (1–5 sentence) description of what you want to build |

## How To Execute

Run the question skill against your goal document:

```
/question goal.md
```

The skill will:
1. Detect whether this is a greenfield project (no existing code) or brownfield (existing codebase)
2. Generate clarifying questions appropriate to the project type
3. Present the questions for your review
4. Capture your answers in a structured document

### For This Exercise

Your `goal.md` should describe a CLI tool that monitors URLs. You don't need to specify every detail — that's what the questions are for. Something like:

> Build a CLI tool that monitors a list of URLs for uptime, checks them on a schedule, and prints notifications when a site goes down or comes back up.

When the AI asks questions, make explicit decisions about things like:
- Foreground process vs. background daemon?
- Where do URLs come from — CLI args, config file, or both?
- What counts as "down" — any error, or consecutive failures?
- Which HTTP library? Sync or async?
- Stdout-only, or also Slack/email notifications?

Don't worry about making "perfect" decisions. The point is to make *explicit* decisions rather than letting the AI decide silently.

## Output Artifacts

| Artifact | Description |
|----------|-------------|
| `thoughts/<task-id>/task.md` | Cleaned-up task description |
| `thoughts/<task-id>/questions.md` | The generated questions, organized by topic |
| `thoughts/<task-id>/answers.md` | Your decisions, one per question |

## Success Criteria

- [ ] You have 5+ questions that cover scope, technical choices, and output format
- [ ] Every question explains why the answer matters to the design
- [ ] You answered each question with a concrete decision (not "whatever you think is best")
- [ ] Reading the answers, someone could predict the rough shape of the system without seeing any code
- [ ] The AI didn't write any code during this step

## Common Mistakes

- **Too few questions.** If the AI only asks 3 questions, it's being lazy. Push for more: "What other decisions would change the architecture?"
- **Vague answers.** "Whatever is easiest" is not a decision. Pick one: "Use httpx, synchronous, with follow_redirects=True."
- **Jumping to code.** If the AI starts writing code, stop it. This step produces documents, not code.

## What's Next

If this is a greenfield project (no existing code), skip to [Step 3: Design Discussion](03-design.md). If you're adding to an existing codebase, proceed to [Step 2: Research](02-research.md).
