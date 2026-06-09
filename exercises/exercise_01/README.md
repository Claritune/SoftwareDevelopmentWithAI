# Exercise: The Curious Case of the Runaway Context

## Background

Cursor Hooks let you intercept the agent's lifecycle events — including every file it
reads — by running external scripts that receive structured JSON on stdin. One practical
use is **token budget tracking**: monitoring how many tokens the agent consumes by reading
files, and nudging or stopping it when it gets greedy.

In this exercise you'll experience the problem first, then build the solution.

---

## Setup

### 1. Generate the project

```bash
python generate_repo.py
```

This creates a `shopapi/` directory — a small Express.js API project for a product catalog.
Take a minute to browse the repo. It looks like a normal project.

### 2. Open in Cursor

```bash
cd shopapi
cursor .
```

---

## Phase 1: Observe the Problem

### The Task

There's a real bug in the product search endpoint: **it returns duplicate results when a
category filter is combined with pagination.** This is a focused, ~10 line fix.

Open Cursor Agent and submit this prompt:

> There's a bug in the product search endpoint — it returns duplicates when the category
> filter is combined with pagination. Find and fix it.

### While It Runs

Watch the agent work. Pay attention to which files it reads — not just the source files,
but everything.

### After It Finishes

Answer these questions in `answers.md`:

1. **List every file the agent read** during the session. (Check the agent's activity log
   in the Cursor UI.)

2. **Estimate the total token cost** of those file reads. Use the rough heuristic:
   `tokens ≈ characters / 4`. For each file, note its approximate size.

3. **Which reads were actually necessary** to fix the bug? Which were the agent
   "exploring" or "being thorough" without real benefit?

4. **What percentage of tokens consumed went to unnecessary reads?**

You'll likely find the agent read fixture data, the OpenAPI spec, and/or the config file —
none of which were needed to fix a pagination bug in the route handler.

---

## Phase 2: Build the Token Budget Hook

Now build a `beforeReadFile` hook that tracks cumulative token usage and intervenes when
the agent reads too much.

### Requirements

Your hook must:

- **Estimate tokens** from the `content` field passed via stdin (use `chars / 4`)
- **Track cumulative usage** across the agent session (use a temp file keyed by
  `generation_id`)
- **Soft warning at 20K tokens**: allow the read, but inject an `agentMessage` telling
  the agent to reconsider whether it needs more files
- **Hard cutoff at 50K tokens**: deny the read entirely with a clear `userMessage`

### Hook Input (what you receive on stdin)

```json
{
  "conversation_id": "...",
  "generation_id": "...",
  "content": "<full file contents as a string>",
  "file_path": "fixtures/products.json",
  "hook_event_name": "beforeReadFile",
  "workspace_roots": ["/path/to/shopapi"]
}
```

### Hook Output (what you write to stdout)

```json
{
  "continue": true,
  "permission": "allow",
  "agentMessage": "Optional message fed back to the agent"
}
```

Or to deny:

```json
{
  "continue": false,
  "permission": "deny",
  "userMessage": "Read denied: token budget exceeded (52,340 / 50,000)"
}
```

### Setup

1. Create `.cursor/hooks.json` in the `shopapi/` project root
2. Create your hook script (bash or python — your choice)
3. Make it executable

### Test It

Re-run the exact same prompt from Phase 1 with your hook active. Then answer:

5. **How did the agent's behavior change?** Did it still try to read the large files?
   Did the soft warning redirect it?

6. **Compare token consumption** before and after. How much did you save?

7. **Write a better agent nudge.** The `agentMessage` at the soft threshold talks to the
   model. Write a message that steers it toward source code without naming specific files
   to skip. (The agent should learn to be lean, not just follow a blocklist.)

8. **Where does this approach break down?** Think about: minified bundles that are
   technically source code, legitimate large files (e.g., a 3000-line migration), or
   generated code that's actually relevant to the bug.

---

## Deliverables

- `answers.md` — your responses to questions 1–8
- `.cursor/hooks.json` — your hook configuration
- `.cursor/hooks/token-budget.sh` (or `.py`) — your hook implementation
- A brief token consumption log showing before vs. after

## Reference

- [Cursor Hooks Deep Dive (GitButler blog)](https://blog.gitbutler.com/cursor-hooks-deep-dive)
- [Cursor Changelog — Hooks Beta](https://cursor.com/changelog#hooks-beta)
