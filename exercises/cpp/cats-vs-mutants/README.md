# Cats vs Mutants: Agent Orchestration Exercise

The point of this exercise is to learn how **agents** and **agent orchestration** work. You
start with a working game and three role-based agents: a product manager, an architect and a
QA engineer. You'll study how they hand work to each other, add the missing developer role,
and then orchestrate the whole team to ship features.

The game is only the playground. It's small enough to understand in an hour, but it has
real rules, real tests and a real architecture, so the agents have something meaningful to
argue about.

## The game

Cats vs Mutants is a lane defense game in C++20 with ASCII graphics for the terminal. Cats
defend the left side of a 5-lane board against mutants walking in from the right. You spend
treats to place cats: some earn treats, some spit hairballs, some block, some fire lasers.
Mutants that reach your home cost a life. Survive three waves to win.

```
cmake -S . -B build
cmake --build build
./build/cats                                  # play (arrow keys, 1-4 to pick a cat, space to place, q to quit)
./build/cats --headless scripts/demo.txt      # scripted game; must end STATUS: Won at tick 1648, 3 lives
ctest --test-dir build                        # 121 unit tests
```

Requirements: CMake 3.20+, a C++20 compiler (Apple Clang is fine), ncurses (ships with macOS).

**[`docs/SPEC.md`](docs/SPEC.md) describes the game in detail**: the cast, tick order, rule
details, headless mode, code layout and the engineering ground rules every change must keep.
Read it before you start; your agents will.

Other documents:

| File | What it is |
|---|---|
| [`docs/SPEC.md`](docs/SPEC.md) | The game as implemented today |
| [`NEW_FEATURES.md`](NEW_FEATURES.md) | A backlog of five proposed features, with rules and test plans |
| [`docs/agents/`](docs/agents/) | The agents, in a harness-neutral form |

## The agents

| Agent | Role | Reads | Writes | Never touches |
|---|---|---|---|---|
| `product` | Product manager: decides **what** to build | `README.md`, `docs/SPEC.md`, `NEW_FEATURES.md`, `src/core/config.hpp` | `docs/features/<slug>.md`: rules, config, acceptance criteria | Code, tests |
| `architect` | Architect: decides **how** it fits the codebase | The spec, the code | `docs/design/<slug>.md`: data changes, tick steps, implementation steps, decisions | Code, tests, specs |
| `qa` | QA engineer: proves it works | The spec, the design, the tests | `tests/<slug>_test.cpp`, `docs/qa/<slug>.md`: test plan and verification report | Game code, specs, designs |

Each feature gets one **slug** (for example `frosty-cat`), and the agents hand off through
files that share it:

```
product ──► docs/features/frosty-cat.md
                 │
architect ──► docs/design/frosty-cat.md
                 │
   (someone implements src/ changes)  ◄── no agent does this yet: that's your first task
                 │
qa ──► tests/frosty-cat_test.cpp + docs/qa/frosty-cat.md
```

The agent definitions live in two places with the same instructions:

- `.claude/agents/*.md`: Markdown with YAML frontmatter (`name`, `description`, `tools`).
  Claude Code and Cursor both read this folder.
- `docs/agents/*.md`: the same prompts without the frontmatter, with "when to use" and the tools
  each agent needs, for harnesses that use another format (Codex, Copilot, Aider, ...).

### Using the agents in Claude Code

Claude Code loads project agents from `.claude/agents/` when a session starts. If you add or
edit an agent file during a session, run `/agents` to check it's loaded, or restart.

- **Ask in plain language.** The main agent picks a subagent from its `description`:
  `Use the product agent to write a spec for the Knight mutant from NEW_FEATURES.md.`
- **Call one by name** with an @-mention: `@agent-architect design docs/features/knight.md`.
- **List and manage agents** with `/agents`.

Each subagent runs in its own context window with only the tools in its `tools` field, and
returns a single report to the main session. **Subagents can't start other subagents**, so the
main session is the orchestrator: it calls `product`, reads the result, calls `architect`, and
so on.

### Using the agents in Cursor

Cursor (2.4 and later) supports subagents, and reads `.claude/agents/` as well as
`.cursor/agents/`. If both define an agent with the same name, the `.cursor/agents/` version
wins.

- **Ask in plain language** in the Agent chat: `Use the qa subagent to verify the knight feature.`
- **Call one by name** with a slash: `/qa verify docs/features/knight.md`.

Cursor uses its own frontmatter options (such as `model` and `readonly`) and may ignore
Claude-specific ones like `tools`. Either way, the "only write under X" limits in these agents
come from their instructions, not from the harness. That's worth keeping in mind when you
design your own agents.

## Tasks

### Part I: one team, one feature

1. **Understand the handoffs.** Read the three agents in `.claude/agents/`. For each one,
   write down its role, what it reads, what it produces and who uses that output next. Then
   look for the gaps: what happens when the architect finds the spec ambiguous? When QA finds a
   defect? Where is the developer?
2. **Define a `developer` agent** that implements a feature from its spec and design. Decide its
   inputs, outputs, boundaries (which folders may it change?), tools, and what it reports when
   it finishes. Put it in `.claude/agents/developer.md` and a harness-neutral copy in
   `docs/agents/developer.md`.
3. **Ship a feature with automated handoff.** Pick a feature from
   [`NEW_FEATURES.md`](NEW_FEATURES.md) or invent your own. Run it through
   `product → architect → developer → qa` so that each step starts from the previous step's
   output without you copying anything between them. Decide what happens when QA reports a
   failure. Keep the orchestration somewhere you can reuse, such as a slash command, a skill
   or a rule, and commit it.

   Done means: the spec, design and QA report exist; the new tests pass; the 121 existing
   tests pass unchanged; the demo still ends `STATUS: Won` at tick 1648 with 3 lives.

### Part II: a team per module

1. **Map the architecture.** Ask the `architect` agent to write `docs/ARCHITECTURE.md`,
   covering every module of the game, its responsibilities, its public interface and how the
   modules depend on each other.
2. **Define module-scoped developer agents**, one per module in the architecture document.
   Each one may change only its own module and must go through the owning agent when it needs
   another module's interface to change.
3. **Ship a cross-module feature.** Pick or invent a feature that touches several modules
   (for example core rules, the renderer and the headless runner), and implement it with the
   module-scoped developers. The orchestration has to split the design into per-module work,
   run the developers in a safe order, and bring the results back together for QA.

   Compare with Part I: what got better, what got harder, and where did the handoffs break?
