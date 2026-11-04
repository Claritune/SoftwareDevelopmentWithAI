# DEMO.md — The Live Demo Flow

A tight, repeatable script for demonstrating multi-agent orchestration in VS Code +
Copilot by building Maestro live. Total runtime: **~20–25 minutes**. Every beat has
a purpose; nothing here is filler.

The arc is deliberately shaped around two payoffs:
- **Minute ~8: "Sound comes out."** The first audible note. Cheap dopamine, earns
  attention.
- **Minute ~18: "Orchestration is real."** QA finds a bug, the Producer routes it,
  a specialist fixes only its lane, and the fixed build plays a full track.

---

## Before you start (setup — do this off-camera)

- [ ] Repo cloned, `.github/copilot-instructions.md` and all six
      `.github/agents/*.agent.md` present.
- [ ] Copilot + Copilot Chat extensions signed in; agent mode + custom agents
      available; the agent picker shows all six agents.
- [ ] A terminal open, `cmake` and a C++17 compiler on PATH. Do one throwaway
      `cmake -S . -B build` so the first on-stage build is fast.
- [ ] Speakers/output tested — you *will* be playing audio.
- [ ] Have `SPEC.md` open in a tab. It's the star; you'll keep pointing at it.
- [ ] Optional safety net: the `maestro-demo-complete` git branch has the finished
      code (sources, tests, CMakeLists), in case live generation stalls. Never show it unless you need it.

> **Framing line to open with:** "I'm not going to ask one AI to write a music
> app. I'm going to run a *team* of agents — a producer and specialists — against a
> shared spec, and orchestrate them the way you'd orchestrate people. Watch the
> handoffs."

---

## Act 0 — The idea (2 min, no typing)

1. Show the two-layer diagram from the README: the **runtime** agents (Producer →
   Composer → Arranger → Synth → Critic) and the **dev** agents with the same
   names.
2. Say the one sentence that makes it land: *"The music system is a team of agents,
   and we're going to build it using a team of agents. Same shape, two levels."*
3. Open `SUBAGENTS.md` to the ownership table. Point out that **each agent owns
   different files** — the boundaries in the code are the boundaries between agents.

---

## Act 1 — The Producer plans (3 min)

1. Switch the agent to **@producer**.
2. Prompt: *"Read SPEC.md and give me the ordered build plan with the owning agent
   for each milestone."*
3. It produces the milestone list (Contracts → Sound → Composer → Synth → Arranger
   → Critic loop → QA/Docs). **Don't build yet.** The point of this beat is that
   the coordinator planned the work and assigned owners — exactly like a lead
   engineer, not like autocomplete.
4. Say: *"Notice it didn't write code. It delegated. That's orchestration."*

---

## Act 2 — Architect lays the contracts (3 min)

1. Producer says the first task belongs to the Architect. Switch to **@architect**.
2. Prompt: *"Create include/maestro/Contracts.h and Agent.h per SPEC section 2–3,
   and the CMakeLists.txt from section 6."*
3. Show the generated `Contracts.h`. Point at `Score` and `AudioBuffer`:
   *"This is the blackboard. Every other agent reads and writes exactly these
   types. The Architect owns them so nobody else can quietly change the interface."*
4. Build to confirm it compiles. (Fast, thanks to the warm build dir.)

---

## Act 3 — First sound (4 min)  ⟵ payoff #1

1. Producer routes to the DSP-Engineer for milestone 2. Switch to **@dsp-engineer**.
2. Prompt: *"Implement WavWriter (16-bit PCM, no deps) and a temporary main that
   writes 2 seconds of a 440 Hz sine to test.wav."*
3. Build, run: `./build/maestro` → `afplay test.wav` (or `aplay`/`ffplay`/`start`).
4. **Play it.** A pure tone fills the room. This is the attention hook — the agents
   have produced something you can *hear* eight minutes in.
5. Say: *"That's the DSP agent's whole job — Score in, samples out. It never
   touched the music theory. Different agent."*

---

## Act 4 — The Composer writes music (4 min)

1. Switch to **@composer-engineer**.
2. Prompt: *"Implement Composer::process — pick a diatonic progression in the
   brief's key and write a melody over it, per SPEC section 4.2 and 5. Symbolic
   only."*
3. Show the `Score` being populated (log the notes, or run a quick test). Emphasize:
   *"No audio here at all. This agent thinks in notes. That's why it's testable
   without listening."*
4. Now switch back to **@dsp-engineer**: *"Update Synth::process to render a full
   Score, not just a sine."*
5. **The handoff moment.** Point out explicitly: the Composer's output type is the
   Synth's input type, fixed by the Architect. Neither agent negotiated it live.
   Build, run, **play** — now it's an in-key melody, not a test tone.

---

## Act 5 — The Arranger fills it out (2 min)

1. Back to **@composer-engineer**: *"Implement the Arranger — add bass, pad, and a
   drum pattern, and assign oscillators per mood (SPEC 4.3)."*
2. Build, run with `--mood lofi` then `--mood chiptune`. **Play both.** Same code,
   audibly different music. Say: *"One brief field changed the whole texture — the
   agent layer did the interpreting."*

---

## Act 6 — Orchestration gets real (5 min)  ⟵ payoff #2

This is the climax. Slow down here.

1. Switch to **@qa**: *"Write tests: every sample finite and in [-1,1]; same seed →
   identical bytes; notes stay in-key."*
2. Run `ctest`. Engineer it so a test **fails** — the classic one is a clipping /
   NaN sample when several loud tracks stack before normalization. (If your Synth
   is already clean, ask QA to also assert peak ≤ 0.95 pre-limiter; it'll catch the
   raw mix.)
3. **Do not fix it as yourself.** Switch to **@producer** and paste QA's failure.
   Prompt: *"QA reports clipping on seed 7. Assign the fix to the owning agent."*
4. Producer routes it to **@dsp-engineer** — because mixing/normalization is *its*
   file, not QA's, not the Composer's. Switch there and prompt the fix (add a
   limiter / normalize before write).
5. Re-run `ctest` — green. Build, run the full command:

   ```bash
   ./build/maestro --mood lofi --key Am --tempo 82 --seconds 20 --seed 7 --play
   ```

6. **Play the finished track.** Land the closing line: *"A defect was found by one
   agent, triaged by the coordinator, and fixed by exactly the specialist that owns
   that code — nobody reached outside their lane. That's the difference between an
   AI that types and a team you orchestrate."*

---

## Act 7 — Wrap (2 min)

1. Switch to **@docs**: *"Update the README run command to match what we built."*
   One-liner; shows the last agent in the pipeline closing the loop.
2. Recap the three ideas the audience should leave with:
   - **Decompose by real skill boundaries** (theory vs. DSP vs. structure), and let
     each agent own its files.
   - **A shared contract is the interface** between agents — define it once, up
     front, with a single owner.
   - **A coordinator + a feedback loop** (Producer + QA) is what turns parallel
     agents into a system instead of chaos.
3. Point forward to the extension ideas in the README (MIDI export agent, a Critic
   with teeth, a Style agent, an MCP tool).

---

## If something goes wrong (recovery)

- **A generation stalls or wanders:** stop it, restate the task with the exact file
  and the acceptance line from `SUBAGENTS.md`. Narrate it as "re-scoping the
  task" — tighter scope is the lesson, not a failure.
- **Build breaks live:** run `git stash` / checkout the `maestro-demo-complete` branch for
  just that file, say "here's the version this agent produced in rehearsal," and
  keep moving. Don't debug C++ in front of the room.
- **No audio device:** open the `.wav` in any player already on screen, or fall
  back to showing the file size / waveform. Have this tested beforehand so it never
  happens.

---

## One-glance cheat sheet

| Time | Act | Agent driving | Audience sees |
|---|---|---|---|
| 0:00 | Idea | — | Two-layer diagram, the pitch |
| 2:00 | Plan | @producer | Delegation, not coding |
| 5:00 | Contracts | @architect | The shared blackboard types |
| 8:00 | First sound | @dsp-engineer | 🔊 a tone plays |
| 12:00 | Music | @composer-engineer → @dsp-engineer | 🔊 melody + the handoff |
| 16:00 | Arrange | @composer-engineer | 🔊 lofi vs chiptune |
| 18:00 | Fix loop | @qa → @producer → @dsp-engineer | 🔊 bug found, routed, fixed |
| 23:00 | Wrap | @docs | The three takeaways |
