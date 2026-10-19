# Maestro Implementation Plan

This plan uses the six workspace agents in `.github/agents`, preserves their file ownership, and makes parallel work visible without introducing integration conflicts. The Producer is the active coordinator throughout.

## 1. Open With The Architecture

- Select `Producer`.
- Ask it to read `SPEC.md`, `SUBAGENTS.md`, and `.github/copilot-instructions.md`.
- Have it state the build order, ownership boundaries, contracts, and acceptance checks.
- Narrate the essential rule: specialists do not negotiate interfaces live; they work through the Architect-owned contracts.

## 2. Milestone 1: Establish The Shared Contract

- Delegate to `Architect`.
- Task: create `include/maestro/Contracts.h`, `include/maestro/Agent.h`, and `CMakeLists.txt`.
- Contract outcome: define `Brief`, `MusicalContext`, `Note`, `Track`, `Score`, `AudioBuffer`, `Critique`, `Blackboard`, and `Agent`.
- Acceptance check: configure and build the CMake skeleton with C++17 and `-Wall -Wextra`.
- Return to `Producer` for the first integration build.

## 3. Milestone 2: Demonstrate "Hello, Sound"

- Delegate to `DSP-Engineer`.
- Task: implement `src/WavWriter.cpp` and a temporary 440 Hz sine-wave route through `src/Synth.cpp`, constrained to its owned files.
- In parallel, delegate to `Producer`.
- Task: implement the minimal wiring in `src/main.cpp` needed to construct a basic buffer and write a WAV.
- This is safe parallelism because DSP owns audio implementation while Producer owns only runtime wiring.
- Producer integrates both results, builds, runs the executable, and plays the output WAV.
- Acceptance check: an audible, valid 16-bit PCM WAV is created.

## 4. Milestone 3: Implement Symbolic Composition

- Delegate to `Composer-Engineer`.
- Task: implement `src/Composer.cpp`:
  - derive `lengthBeats` from duration and tempo;
  - choose a mood-appropriate diatonic progression;
  - emit chord notes and a melody;
  - use only `MusicalContext::rng`;
  - ensure generated pitches remain in the configured scale.
- In parallel, delegate to `QA`.
- Task: create the initial `tests/test_core.cpp` harness and tests for scale membership and deterministic symbolic score generation for the same seed.
- This is safe parallelism because QA owns only tests and Composer owns only symbolic implementation.
- Producer collects both results, runs `ctest`, and routes failures to Composer-Engineer.

## 5. Milestone 4: Replace The Tone With Real Synthesis

- Delegate to `DSP-Engineer`.
- Task: extend `src/Synth.cpp` to render a complete `Score`:
  - beat-to-sample conversion;
  - per-track oscillator choice;
  - MIDI-to-frequency conversion;
  - ADSR envelopes by role;
  - mixing, normalization, finite-value guards, and clipping protection.
- In parallel, delegate to `QA`.
- Task: add audio-safety tests for finite samples and range `[-1, 1]`.
- Producer integrates and runs a short seeded composition.
- Acceptance check: the full symbolic score produces audible normalized audio without NaN, infinity, or clipping.

## 6. Milestone 5: Arrange The Track

- Delegate to `Composer-Engineer`.
- Task: implement `src/Arranger.cpp`:
  - bass roots on downbeats;
  - sustained pad chord tones;
  - kick, snare, and hat patterns;
  - oscillator and gain assignments by mood.
- In parallel, delegate to `DSP-Engineer`.
- Task: refine drum rendering in `Synth.cpp` so noise and impulse drum notes are distinct and decay quickly.
- Producer runs the integrated track and confirms all tracks traverse the shared `Score` contract unchanged.
- Acceptance check: output contains melody, harmony, bass, pad, and drums, while remaining within audio bounds.

## 7. Milestone 6: Make Orchestration Real

- Before assigning implementation, identify the ownership gap: `src/Critic.cpp` is required by `SPEC.md` but is not assigned in `SUBAGENTS.md`.
- The Producer asks the Architect to propose a narrowly scoped ownership decision, then updates the ownership map before coding begins. Do not have an agent edit `Critic.cpp` until this is explicit.
- In parallel after that decision, delegate the Critic implementation to its assigned owner and delegate to `Producer` to implement the `Composer -> Arranger -> Synth -> Critic` sequence and retry logic in `src/Producer.cpp`.
- Producer implementation details:
  - resolve brief key and scale into `MusicalContext`;
  - seed the RNG once;
  - run until acceptable or `maxPasses` is reached;
  - apply known `suggestedFix` values before retrying.
- Acceptance check: pick a mood and seed that triggers a critique; show the Producer rerunning the relevant stages and improving the flagged metric.

## 8. Milestone 7: Adversarial Verification

- Delegate to `QA`.
- Task: complete tests for:
  - notes stay in key;
  - samples are finite and in range;
  - the same seed produces byte-identical output;
  - a different `--mood` produces different output;
  - Critic retry behavior has a reproducible case.
- QA reports defects only: failing command, exact inputs, expected output, actual output, and owning agent.
- Producer routes each report to the single responsible specialist, then reruns QA after each fix.
- Acceptance check: `ctest --test-dir build --output-on-failure` passes.

## 9. Finish With Documentation

- Delegate to `Docs` only after implementation and QA are complete.
- Task: update `README.md` and `DEMO.md` with verified commands, expected output, and concise explanations of non-obvious DSP and music choices.
- Docs reruns the documented configure, build, test, and playback commands.
- Acceptance check: a newcomer can clone, build, test, and generate `song.wav` using only the README.

## 10. Close The Demo With Producer

- Select `Producer` for the final integration run:

```bash
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
./build/maestro --mood lofi --key Am --tempo 82 --seconds 20 --seed 7 --out song.wav --play
```

- Narrate the two outcomes:
  - The shared contracts enabled independent parallel work.
  - QA fed defects back through Producer, which assigned each fix to the proper owner without boundary violations.