# SUBAGENTS.md — The Copilot Agents That Build Maestro

This file defines the **development-time** agents you orchestrate in VS Code to
build Maestro, how they're configured, and how they hand off to each other.

The runtime music agents (Producer/Composer/Arranger/Synth/Critic) live in the C++
code. The **dev agents** below have deliberately parallel names and roles, so the
audience sees the same orchestration shape at both levels: *a lead coordinator
delegating scoped work to specialists over a shared contract.*

> **How this maps to VS Code + Copilot.** Each agent is a **workspace custom agent**
> (`.github/agents/<name>.agent.md`) with its own instructions and its own
> allowed tool set. All agents share `.github/copilot-instructions.md`, which
> carries the non-negotiable context (the data contracts, coding standards, "don't
> touch other modules"). You switch the active agent from the custom agent picker;
> the **Producer** is the one you drive, and it delegates by telling you which
> agent to switch to next and exactly what to ask it. Feature names and menu
> locations differ slightly across Copilot versions — treat the custom-agent files as
> the source of truth.

---

## The shared context every agent obeys  (`.github/copilot-instructions.md`)

Put the invariants here so no single agent has to be reminded of them:

```md
# Maestro — shared instructions for all agents
- Language: C++17, standard library only. No third-party deps. Must build with
  -Wall -Wextra and zero warnings.
- The data contracts in include/maestro/Contracts.h are the interface between
  modules. Do NOT change them unless you are the Architect agent.
- Each agent edits ONLY the files it owns (see SUBAGENTS.md). If your task needs
  another module changed, stop and report it to the Producer — do not reach in.
- All randomness comes from MusicalContext::rng. No other RNG, no global state.
- Symbolic logic (notes) must be unit-testable without audio playback.
- Prefer small, reviewable diffs. Explain any non-obvious music/DSP choice in a
  one-line comment.
```

That file is the dev-side equivalent of the runtime **blackboard**: the single
shared surface everyone reads before acting.

---

## The agents

### 1. 🎯 Producer  (the orchestrator — the one you talk to)
**Custom agent:** `producer.agent.md`
**Owns:** planning, delegation, integration, the build/run loop. Edits wiring in
`src/main.cpp` and `src/Producer.cpp` only.
**Tools:** read all files, run tasks/terminal (build + run), no free-form edits to
specialist modules.
**Job:**
- Read `SPEC.md`, produce an ordered task list matching the milestones.
- For each task, name the specialist agent, the exact files it may touch, the
  contract it must honor, and the acceptance check.
- After a specialist reports back, build, run, and either accept or route the
  result to QA or back to the specialist.
- Run the Critic-style loop at the *project* level: if QA finds a defect, decide
  who fixes it.

**Delegation prompt template the Producer emits:**
```
Switch to @dsp-engineer. Task: implement Synth::process in src/Synth.cpp.
Input contract: a fully-populated Score (see Contracts.h).
Output contract: fills Blackboard.audio (mono, 44100, samples in [-1,1]).
Do not modify Contracts.h or any Composer/Arranger file.
Done when: `./build/maestro --seconds 3` produces an audible, non-clipping wav.
```

---

### 2. 🎹 Composer-Engineer  (music theory specialist)
**Custom agent:** `composer-engineer.agent.md`
**Owns:** `src/Composer.cpp`, `src/Arranger.cpp`.
**Expertise instruction:** "You are a music-theory-literate C++ engineer. You know
scales, diatonic chords, voice leading, and rhythm. You produce *symbolic* music
(Note/Track/Score); you never write audio samples."
**Tools:** edit its two files, read contracts + spec, run `maestro_tests`.
**Job:** implement progression choice, melody generation, and the bass/pad/drum
arrangement, all deterministic from the RNG. Guarantees notes stay in-key.
**Hands off to:** DSP-Engineer (its `Score` is the Synth's input).

---

### 3. 🔊 DSP-Engineer  (audio/synthesis specialist)
**Custom agent:** `dsp-engineer.agent.md`
**Owns:** `src/Synth.cpp`, `src/WavWriter.cpp`.
**Expertise instruction:** "You are a DSP engineer. You know oscillators, ADSR
envelopes, mixing, normalization, clipping, and the WAV format. You turn a Score
into an AudioBuffer and write a valid file."
**Tools:** edit its two files, read contracts + spec, run the executable, inspect
output size/peak.
**Job:** oscillator bank, envelopes, mixdown, normalization + NaN/clip guards, and
a dependency-free 16-bit PCM WAV writer with optional OS playback.
**Hands off to:** QA (numerical safety) and Producer (integration).

---

### 4. 🏛️ Architect  (contracts & structure specialist)
**Custom agent:** `architect.agent.md`
**Owns:** `include/maestro/Contracts.h`, `include/maestro/Agent.h`, `CMakeLists.txt`.
**The only agent allowed to change the shared contracts.** This is the whole
point — a single owner for the interface prevents two specialists from silently
diverging.
**Job:** define/evolve the blackboard types, the `Agent`/`Blackboard` interface,
and the build. When a specialist needs a contract change, it files the request to
the Producer, who routes it here.

---

### 5. ✅ QA  (test & verification specialist)
**Custom agent:** `qa.agent.md`
**Owns:** `tests/test_core.cpp`.
**Expertise instruction:** "You are adversarial about correctness. You write tests
that try to break the module, then report defects precisely."
**Tools:** edit tests, run `ctest`, read all source (read-only).
**Job:** assert notes stay in-key; assert every sample is finite and within range;
assert determinism (same seed → same bytes); assert `--mood` changes output. When
a test fails, report the failing input and expected vs. actual to the Producer —
QA does **not** fix the code it tests.
**Hands off to:** Producer, who routes the fix to the owning specialist.

---

### 6. 📝 Docs  (documentation specialist)
**Custom agent:** `docs.agent.md`
**Owns:** `README.md`, code comments, and the demo notes.
**Job:** keep the README build/run commands accurate, document non-obvious
choices, and make sure a newcomer can go from clone to sound in under five
minutes. Runs last so it documents what actually shipped, not what was planned.

---

## Ownership map (who may edit what)

| File / area | Owner | Read-only for |
|---|---|---|
| `include/maestro/Contracts.h`, `Agent.h` | Architect | everyone else |
| `CMakeLists.txt` | Architect | everyone else |
| `src/main.cpp`, `src/Producer.cpp` | Producer | others |
| `src/Composer.cpp`, `src/Arranger.cpp` | Composer-Engineer | others |
| `src/Synth.cpp`, `src/WavWriter.cpp` | DSP-Engineer | others |
| `tests/test_core.cpp` | QA | others |
| `README.md`, comments | Docs | others |

Non-overlapping ownership is what keeps parallel agents from fighting. It's also
the single most important thing to point out to the audience: **the boundaries in
the code are the boundaries between the agents.**

---

## Orchestration pattern (how a task actually flows)

```
        ┌─────────────────────────────────────────────┐
        │                 PRODUCER                     │
        │  reads SPEC → makes task list → delegates    │
        └───────┬───────────────┬───────────────┬──────┘
                │ scoped task    │               │
                ▼                ▼               ▼
        ┌───────────────┐ ┌───────────────┐ ┌───────────┐
        │ Composer-Eng. │ │  DSP-Engineer │ │ Architect │
        │  Score  ──────┼▶│  AudioBuffer  │ │ contracts │
        └───────┬───────┘ └───────┬───────┘ └───────────┘
                │ output           │ output
                ▼                  ▼
              (shared contracts = the interface)
                │                  │
                └────────┬─────────┘
                         ▼
                   ┌───────────┐   defect report
                   │    QA     │────────────────▶ back to Producer
                   └───────────┘
```

**The two things to narrate on stage:**
1. **Handoff over a contract.** The Composer-Engineer's output type *is* the
   DSP-Engineer's input type. Neither agent negotiates the format live — the
   Architect fixed it up front. That's why they can work independently.
2. **The feedback loop.** QA finds a real defect, the Producer decides who owns
   the fix, the specialist fixes only its file. No agent oversteps its lane.

---

## Minimal custom-agent file template

Each `.github/agents/<agent>.agent.md` looks roughly like:

```md
---
description: <one line — what this agent is for>
tools: [read, search, edit, execute]   # scope per role
---
You are the <ROLE> agent for Maestro.
Owned files: <list>. Edit nothing else.
Contracts you must honor: <input> in, <output> out (see Contracts.h).
When your task needs a change outside your files, STOP and report to the Producer.
Definition of done: <acceptance check>.
```

Ship all six. They're small, and they're what turns "I told Copilot to write some
code" into "I orchestrated a team of agents against a shared spec" — which is the
lesson.
