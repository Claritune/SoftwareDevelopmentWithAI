# Maestro

Maestro is a self-contained C++17 music renderer. Its deterministic runtime
pipeline is:

```text
Composer -> Arranger -> Synth -> Critic
```

The Producer initializes the musical context and runs this full pipeline.
Composer and Arranger work with symbolic notes; Synth renders audio samples; and
Critic may request another complete pass.

## Requirements

- CMake 3.16 or newer
- A C++17 compiler

Maestro uses the C++ standard library only. No package installation, audio SDK,
or network access is required.

## Build and test

From the repository root:

```bash
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

The executable is `build/maestro`. The project builds with `-Wall -Wextra`.
Tests cover deterministic symbolic output and scale membership, Critic outcomes,
and finite normalized mono audio samples.

## Render and listen

```bash
./build/maestro \
  --mood lofi --key A --scale minor --tempo 82 --seconds 20 \
  --seed 7 --passes 2 --out song.wav
```

On success, Maestro reports the sample count, destination path, and final
zero-based pipeline pass. It writes a 44.1 kHz, mono, 16-bit PCM WAV. The
duration follows `--seconds`; the generated content follows the complete brief
and its seed.

On macOS, add `--play` to invoke `afplay` after the WAV is written:

```bash
./build/maestro --mood lofi --key A --scale minor --tempo 82 --seconds 20 \
  --seed 7 --passes 2 --out song.wav --play
```

Playback depends on macOS and an available audio device. On other platforms,
use a local WAV player after rendering.

## CLI

All flags except `--play` require a following value. Unknown flags, missing
values, and non-numeric values for numeric flags are errors.

| Flag | Default | Meaning |
| --- | --- | --- |
| `--mood <name>` | `lofi` | Selects composition, arrangement, and Critic density behavior. `lofi`, `chiptune`, `cinematic`, and `ambient` are implemented; another name uses `lofi` behavior. |
| `--key <name>` | `A` | Tonic. Recognizes `C`, `C#`, `Db`, `D`, `D#`, `Eb`, `E`, `F`, `F#`, `Gb`, `G`, `G#`, `Ab`, `A`, `A#`, `Bb`, and `B`; another name falls back to `A`. |
| `--scale <name>` | `minor` | `major`, `minor`, `dorian`, or `pentatonic`; another name uses `minor`. |
| `--tempo <bpm>` | `82` | Initial tempo in beats per minute. |
| `--seconds <duration>` | `3.0` | Requested duration in seconds. The command-line default is three seconds. |
| `--seed <uint32>` | `7` | Shared musical RNG seed. Keep it fixed to reproduce output. |
| `--passes <count>` | `2` | Maximum Critic-driven retries after the initial pass. A negative value disables retries. |
| `--out <path>` | `song.wav` | Destination WAV path. Rendering fails if it cannot be written. |
| `--play` | none | On macOS, invokes `afplay` for the output WAV after writing it. Playback depends on the platform and available audio device. |

## Critic and retries

Critic evaluates mood-specific note density, the fraction of simultaneous
minor-second/tritone intervals, and dynamic range. It accepts a pass only when
input and audio are valid, density is in range, dissonance is at most `0.20`,
and dynamic range is at least `0.12`.

An unacceptable pass with retries remaining restarts at Composer with the same
seed. The Producer handles these suggestions:

- `reduce_density`: subtract 8 BPM, with a 40 BPM floor.
- `raise_energy`: add 8 BPM, with a 240 BPM ceiling.
- `resolve_dissonance`: retry without a current parameter adjustment.

The Producer stops on acceptance, on the final allowed pass, or with no Critic
suggestion. `--passes 2` means the initial pass plus up to two retries; the final
reported pass is therefore in `0..2`.

## Verify deterministic output

Render an identical brief twice and compare the WAV bytes:

```bash
./build/maestro --mood lofi --key A --scale minor --tempo 82 --seconds 3 --seed 7 --passes 2 --out first.wav
./build/maestro --mood lofi --key A --scale minor --tempo 82 --seconds 3 --seed 7 --passes 2 --out second.wav
cmake -E compare_files first.wav second.wav
```

`cmake -E compare_files` succeeds only when the files are byte-for-byte
identical. A different `--seed` produces a different deterministic result.

## Live demonstration

The concise script for a build, render, test, reproducibility, and playback
walkthrough is in [DEMO.md](DEMO.md).
# 🎼 Maestro — A Multi-Agent Music Studio in C++

> A small, self-contained C++ program that **composes and plays music** using a
> team of cooperating agents — and a teaching demo for **building it with
> multiple orchestrated agents in VS Code + GitHub Copilot**.

Maestro has two layers that mirror each other, and that mirror is the whole point
of the demo:

1. **The runtime system** is a multi-agent pipeline. A *Producer* agent takes a
   short creative brief ("dreamy lo-fi, 20 seconds, A minor") and coordinates a
   *Composer*, an *Arranger*, a *Synth* and a *Critic* to turn it into an actual
   `.wav` file you can play.
2. **The build process** is *also* a multi-agent pipeline. You develop Maestro
   inside VS Code by orchestrating a set of specialized Copilot agents — a lead
   *Producer* agent that delegates to a *Composer-Engineer*, a *DSP-Engineer*, an
   *Architect*, a *QA* agent and a *Docs* agent.

The runtime agents talk through a shared **blackboard** (a `Score` object passed
between them). The dev agents talk through a shared **repo** (this SPEC and the
shared contracts file). Same pattern, two levels. That parallel is what makes the
demo click for an audience.

---

## Why this makes a good demo

- **It's genuinely small.** Pure C++17, standard library only, one CMake file.
  No audio SDKs, no ML models, no network. It builds and runs in seconds on any
  laptop.
- **The output is undeniable.** At the end you double-click a `.wav` and music
  plays. Agents that produce a spreadsheet are abstract; agents that produce a
  melody get a reaction.
- **The agent boundaries are real, not cosmetic.** Composition, arrangement and
  synthesis are genuinely different skills with clean interfaces between them —
  so splitting them across agents is a natural decomposition, not a contrived one.
- **It teaches orchestration, not just autocomplete.** The interesting part isn't
  "Copilot wrote a function." It's the Producer agent planning the work, handing
  a well-scoped task to a specialist, integrating the result, and looping through
  a Critic for a second pass.

---

## What Maestro does (the runtime)

```
  brief ──▶ Producer ──▶ Composer ──▶ Arranger ──▶ Synth ──▶ song.wav
              ▲              │            │           │
              │              ▼            ▼           ▼
              └────────── Critic ◀── (shared Score on the blackboard)
```

Given a `Brief`:

```jsonc
{ "mood": "lofi",  "key": "A", "scale": "minor",
  "tempoBpm": 82,  "seconds": 20, "seed": 7 }
```

1. **Producer** sets the global musical context (key, tempo, time signature) and
   runs the pipeline, then decides whether a second pass is needed.
2. **Composer** picks a chord progression in the key and writes a melody over it.
3. **Arranger** fleshes the score out: a bassline from the chord roots, a pad for
   harmony, and a simple drum pattern. It assigns an oscillator voice to each
   track.
4. **Synth** renders the symbolic `Score` into raw audio samples (oscillators +
   ADSR envelopes + mixing) and normalizes the result.
5. **Critic** scores the result on a few cheap heuristics (dissonance, note
   density, dynamic range) and returns notes. If it flags a problem and we have
   passes left, the Producer nudges a parameter and re-runs the relevant stage.
6. **Output** writes `song.wav` and (optionally) plays it.

Run it:

```bash
./maestro --mood lofi --key Am --tempo 82 --seconds 20 --seed 7 --out song.wav --play
```

---

## What the demo actually shows (the build)

You don't ship Maestro pre-written and read it out. You **build a slice of it live**
by orchestrating agents in VS Code. The audience watches:

- The **Producer agent** read `SPEC.md`, break the work into scoped tasks, and
  delegate each to the right specialist.
- The **Composer-Engineer agent** implement the music-theory module against the
  agreed data contracts — and *only* that module.
- A **handoff**: the Composer-Engineer's `Score` output becomes the DSP-Engineer's
  input, with the shared contracts file acting as the interface neither agent is
  allowed to break.
- The **QA agent** write a test that catches a real bug (a clipped/NaN sample),
  the Producer route it back, and the fix land.
- Everything integrate into a build that produces sound.

`SUBAGENTS.md` defines each agent; `DEMO.md` is the minute-by-minute script.

---

## Repository layout

```
maestro/
├── README.md              ← you are here
├── SPEC.md                ← what to build: contracts, modules, algorithms
├── SUBAGENTS.md           ← the Copilot agents and how they're orchestrated
├── DEMO.md                ← the live demo flow, step by step
│
├── .github/
│   ├── copilot-instructions.md      ← shared context every agent obeys
│   └── agents/                      ← one workspace custom agent per role
│       ├── producer.agent.md
│       ├── composer-engineer.agent.md
│       ├── dsp-engineer.agent.md
│       ├── architect.agent.md
│       ├── qa.agent.md
│       └── docs.agent.md
│
├── CMakeLists.txt
├── include/maestro/       ← shared contracts (the "blackboard" types)
│   ├── Contracts.h        ← Brief, Note, Track, Score, AudioBuffer, Critique
│   └── Agent.h            ← the Agent interface + Blackboard
├── src/
│   ├── main.cpp           ← CLI + Producer wiring
│   ├── Producer.cpp
│   ├── Composer.cpp
│   ├── Arranger.cpp
│   ├── Synth.cpp
│   ├── Critic.cpp
│   └── WavWriter.cpp
└── tests/
    └── test_core.cpp
```

> The `.github/agents/` folder and `copilot-instructions.md` are the artifacts
> that make the orchestration *real* rather than a story you tell. They ship in
> the repo so the demo is reproducible.

---

## Requirements

- A C++17 compiler (GCC 9+, Clang 10+, or MSVC 2019+)
- CMake 3.16+
- VS Code with the **GitHub Copilot** and **GitHub Copilot Chat** extensions
  (agent mode + custom chat modes enabled)

No audio libraries are needed — Maestro writes a standard PCM `.wav` and lets your
OS play it (`afplay` on macOS, `aplay`/`ffplay` on Linux, `start` on Windows).

---

## Build and run

```bash
cmake -S . -B build
cmake --build build
./build/maestro --mood lofi --key Am --seconds 20 --play
```

Then open `song.wav`. That's the demo's payoff: a room full of people, and the
thing the agents built plays back.

---

## Where to go next (extension ideas for a workshop)

- Add a **MIDI export** agent alongside the WAV synth (same `Score`, new output).
- Give the **Critic** teeth: let it request a *specific* re-composition, not just
  a parameter nudge, and show the Producer managing the loop.
- Add a **Style agent** that expands "lofi" / "chiptune" / "cinematic" into
  concrete parameter sets, so briefs get shorter and the agent layer does more.
- Wire an **MCP tool** so an agent can call out to a real music-theory reference
  during development.
