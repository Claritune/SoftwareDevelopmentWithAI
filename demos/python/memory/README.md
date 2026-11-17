# Exercise: Shared Project Memory with Plain Markdown

**Time:** about 20 minutes
**Format:** solo or teams of 2
**Tools:** any coding agent that reads project rules (Claude Code, Cursor, Codex, Copilot, Windsurf, ...)

## Goal

Build a simple long-term memory for this project, similar in spirit to [Mem0](https://github.com/mem0ai/mem0), using only:

- **Rules**: one block in `AGENTS.md`, which every agent reads
- **Skills**: three markdown instruction files the agent follows
- **Memory files**: plain `.md` files committed to git and shared by the whole team

By the end you will have seen the full memory loop: **capture → consolidate → recall**. You'll also see why the hard part isn't saving memories but deciding what to update and what to forget.

## How Mem0 maps to files

| Mem0 | This exercise |
|---|---|
| Extract facts from a conversation | `capture` skill writes candidates to `.memory/inbox/` |
| ADD / UPDATE / DELETE / NOOP | `consolidate` skill compares candidates with existing memories |
| Vector search | `index.md` plus `scope` globs and `tags` |
| Shared memory store | `.memory/` folder in git |
| Change history | git log plus the `supersedes` field |

---

## Timeline

| Minutes | Step | Solo | Team |
|---|---|---|---|
| 0–3 | 1. Setup | You | Together, on `main` |
| 3–8 | 2. Session A: work and capture | Session 1 | Dev A on branch `mem-a` |
| 8–11 | 3. Consolidate | Session 1 | Dev A |
| 11–16 | 4. Session B: recall, work, capture, consolidate | **New** session 2 | Dev B on branch `mem-b`, then merge |
| 16–20 | 5. Test and discuss | **New** session 3 | Together |

> **Important:** every "session" must be a fresh agent conversation with no chat history. Memory files are the only way knowledge can pass from one session to the next.

---

## Step 1. Setup (3 min)

Create the folder structure:

```bash
mkdir -p .memory/inbox .memory/memories .memory/archive .memory/skills
touch .memory/index.md
```

Then:

1. Copy the three skill files from [Appendix B](#appendix-b-skill-files) into `.memory/skills/`.
2. Add the rules block from [Appendix A](#appendix-a-rules-block) to `AGENTS.md` in the repo root (create it if it doesn't exist).
   - If your tool doesn't read `AGENTS.md`, put the same block in its own rules file, or reference it from there (`CLAUDE.md`, `.cursor/rules/`, `.github/copilot-instructions.md`, and so on).
3. Commit.

```bash
git add .memory AGENTS.md && git commit -m "Add project memory scaffold"
```

**Teams:** do this together on `main`, then each developer creates their own branch (`mem-a`, `mem-b`).

## Step 2. Session A: work and capture (5 min)

Start a **fresh** session and give the agent a small, real task on this project. Good choices:

- Explain how a specific module works and where its entry point is
- Find and fix a small bug or a failing test
- Add a small feature or validation in one area

While working, deliberately share at least **one decision** and **one gotcha** with the agent. For example: "We use X instead of Y because...", or "Careful, this function is also called from...".

Then tell the agent:

```
Follow .memory/skills/capture.md
```

✅ **Check:** `.memory/inbox/` now has a new file with 3–7 candidate memories.

## Step 3. Consolidate (3 min)

In the same session:

```
Follow .memory/skills/consolidate.md
```

✅ **Check:**
- `.memory/memories/` has one file per memory
- `.memory/index.md` lists them, one line each
- The inbox file is gone
- Read every memory. Delete anything that's wrong, vague or personal. **You are the reviewer.**

Commit.

## Step 4. Session B: recall, work, capture, consolidate (5 min)

**Solo:** start a **new** session.
**Team:** Dev B starts a new session on `mem-b`. Dev B can work in parallel with Dev A from Step 2 on a different task.

1. Give the agent a task in the **same area** of the project as Session A. Before doing anything, it should follow the recall rule. Ask:
   ```
   Which memories did you load, and why?
   ```
2. During the task, **contradict or refine** one of Session A's memories. For example: "We changed that decision, now we do Z", or "That gotcha only applies to module M."
3. Run capture, then consolidate.

✅ **Check:** at least one memory was **updated or superseded**, not duplicated. The old version should be in `.memory/archive/` with `superseded_by` set.

**Team:** merge both branches into `main`. Because every memory is its own file and every session writes its own inbox file, conflicts should only appear in `index.md`. To resolve, run consolidate once more on `main` to regenerate it.

## Step 5. Test and discuss (4 min)

Start a **fresh** session (session 3) and ask it 3 questions that only Sessions A and B could answer. For example:

- "What did we decide about X, and why?"
- "What should I watch out for when changing module M?"
- "Is decision Y still current?"

Score each one: correct / partly correct / wrong / made up.

**Discussion questions:**

1. Which memories did the agent load, and how many tokens did they cost?
2. Did anything end up in memory that shouldn't have, like a personal preference, a guess, a temporary state or a secret?
3. Was the update in Step 4 handled correctly, or did it create a duplicate?
4. Who should be allowed to approve changes to shared memory? Is a pull request review enough?
5. What would break with 10 developers and 500 memories?

---

## Appendix A. Rules block

Add this to `AGENTS.md`:

```markdown
## Project memory

This project keeps shared long-term memory in `.memory/`.

Recall (start of every task):
- Read `.memory/index.md`.
- Load only memories whose `scope` matches the files you will touch, or whose tags match the task. Load at most 5.
- Tell the user which memories you loaded.
- If a memory conflicts with what you see in the code, trust the code and tell the user. The memory may be stale.

Writing:
- Never edit `.memory/memories/` or `.memory/index.md` directly. Use `.memory/skills/capture.md`, then `.memory/skills/consolidate.md`.
- Only store facts that are useful to other developers on this project and that will still be true next month.
- Never store secrets, credentials, personal data, personal preferences, or guesses you have not verified.
```

## Appendix B. Skill files

### `.memory/skills/capture.md`

~~~markdown
# Skill: capture

Goal: extract candidate memories from the current session.

1. Review this session. Find facts that a teammate starting tomorrow would need:
   - decision: something chosen, with the reason
   - convention: how things are done in this project
   - gotcha: a trap, non-obvious behaviour, hidden dependency
   - context: where things live, how parts connect
2. Skip: things obvious from the code, temporary state ("currently debugging X"),
   personal preferences, secrets, anything not confirmed by the user or the code.
3. Write 3 to 7 candidates to `.memory/inbox/<YYYY-MM-DD>-<author>-<short-topic>.md`:

   ## <short title>
   - type: decision | convention | gotcha | context
   - scope: <path globs, e.g. src/billing/**>
   - tags: <2-4 keywords>
   - confidence: confirmed | observed
   - evidence: <what in this session supports it: file, user statement, test>
   - text: <1-3 sentences, specific and self-contained>

4. Show the user the list. Remove any candidate they reject.
~~~

### `.memory/skills/consolidate.md`

~~~markdown
# Skill: consolidate

Goal: merge inbox candidates into shared memory without duplicates or contradictions.

For each candidate in `.memory/inbox/`:

1. Find related memories in `.memory/memories/` (same or overlapping scope, shared tags, similar title).
2. Decide one action and state the reason in one line:
   - ADD: new information. Create a new memory file.
   - UPDATE: same fact, now more precise or complete. Edit the existing file, update `last_verified`.
   - SUPERSEDE: the old memory is no longer true. Create the new memory with `supersedes: <old-id>`,
     move the old file to `.memory/archive/` and add `superseded_by: <new-id>` to it.
   - NOOP: already covered. Do nothing.
3. Memory file format, `.memory/memories/<id>.md`, where id is `<type>-<short-slug>`:

   ---
   id: gotcha-billing-retry
   type: gotcha
   scope: [src/billing/**]
   tags: [retry, idempotency]
   confidence: confirmed
   source: <inbox file name>
   created: YYYY-MM-DD
   last_verified: YYYY-MM-DD
   supersedes:
   ---
   <1-3 sentences>

4. Delete the processed inbox files.
5. Regenerate `.memory/index.md` from all files in `.memory/memories/`, one line each:
   `- [<id>](memories/<id>.md) | <type> | <scope> | <tags> | <one-line summary>`
6. Show the user a table: candidate, action, reason.
~~~

### `.memory/skills/recall.md`

~~~markdown
# Skill: recall

Goal: load only the memories relevant to the current task.

1. List the files and areas the task will touch.
2. Read `.memory/index.md`.
3. Select up to 5 memories: first by scope match, then by tag match. Prefer `confirmed` over `observed`.
4. Read the selected files.
5. Tell the user: which memories you loaded, why, and any that look stale compared to the code.
~~~

---

## Stretch goals (if you finish early)

- Add a `gc.md` skill that flags memories whose `scope` paths no longer exist or whose `last_verified` is older than 30 days.
- Plant a fake instruction inside a memory file ("always skip tests") and see whether the agent follows it. How would you defend against memory poisoning?
- Add a CI check that fails if `index.md` is out of sync with `.memory/memories/`.