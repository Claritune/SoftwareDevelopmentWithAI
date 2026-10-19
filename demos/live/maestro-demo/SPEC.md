# SPEC.md — Maestro Technical Specification

This is the contract every agent builds against. It is deliberately precise about
**interfaces** and deliberately loose about **implementation**, so that specialist
agents can own their modules without stepping on each other. The shared types in
this document are the "blackboard": the only thing agents pass between them.

Target: **C++17**, standard library only, CMake. No third-party dependencies.

---

## 1. Design principles

- **One data spine.** Everything flows through a single `Score` object plus a
  final `AudioBuffer`. Agents transform the spine; they do not invent private
  side-channels.
- **Agents are pure-ish transforms.** Each agent reads from the blackboard and
  writes back to it. Given the same blackboard and seed, an agent is
  deterministic. Determinism is what makes the demo repeatable on stage.
- **Symbolic first, audio last.** Composition and arrangement work on *notes*
  (cheap, debuggable). Only the Synth touches *samples*. This keeps the
  interesting logic testable without listening.
- **No global mutable state.** All randomness comes from a seeded RNG carried in
  the context, so results are reproducible.

---

## 2. Core data contracts  (`include/maestro/Contracts.h`)

These structs are the interface between agents. **Changing them is an
architectural decision** and belongs to the Architect agent, never a specialist.

```cpp
namespace maestro {

// ---- Input ----------------------------------------------------------------
struct Brief {
    std::string mood      = "lofi";   // lofi | chiptune | cinematic | ambient
    std::string key       = "A";      // note name, e.g. "A", "C#", "Eb"
    std::string scale     = "minor";  // major | minor | dorian | pentatonic
    int         tempoBpm  = 82;
    double      seconds   = 20.0;
    uint32_t    seed      = 7;
    int         maxPasses = 2;         // how many Critic-driven retries allowed
};

// ---- Musical context (set by Producer, read by everyone) ------------------
struct MusicalContext {
    int      keyRootMidi = 69;   // MIDI note of the tonic (A4 = 69)
    std::vector<int> scaleSemitones;   // e.g. minor = {0,2,3,5,7,8,10}
    int      tempoBpm    = 82;
    int      beatsPerBar = 4;
    int      sampleRate  = 44100;
    std::mt19937 rng;            // seeded once, shared, advanced by agents
};

// ---- Symbolic music -------------------------------------------------------
enum class Osc { Sine, Square, Saw, Triangle, Noise };
enum class Role { Melody, Chords, Bass, Pad, Drums };

struct Note {
    int    pitchMidi;      // 0..127; ignored for Drums (use velocity/osc)
    double startBeat;      // in beats from t=0
    double durBeats;       // length in beats
    double velocity;       // 0.0 .. 1.0
    int    trackId;
};

struct Track {
    int    id;
    Role   role;
    Osc    osc;            // which voice the Synth uses
    double gain = 0.8;     // pre-mix level 0..1
};

struct Score {
    MusicalContext     ctx;
    std::vector<Track> tracks;
    std::vector<Note>  notes;
    double             lengthBeats = 0.0;
};

// ---- Audio ----------------------------------------------------------------
struct AudioBuffer {
    int  sampleRate = 44100;
    int  channels   = 1;
    std::vector<float> samples;   // interleaved if channels > 1, range [-1,1]
};

// ---- Feedback -------------------------------------------------------------
struct Critique {
    double dissonance;     // 0 good .. 1 bad
    double density;        // notes per bar, normalized
    double dynamicRange;   // 0 flat .. 1 lively
    bool   acceptable;
    std::vector<std::string> notes;   // human-readable remarks
    std::string suggestedFix;         // machine-readable hint, e.g. "reduce_density"
};

} // namespace maestro
```

---

## 3. The Agent interface  (`include/maestro/Agent.h`)

```cpp
namespace maestro {

struct Blackboard {
    Brief        brief;
    Score        score;
    AudioBuffer  audio;
    Critique     critique;
    int          pass = 0;
};

class Agent {
public:
    virtual ~Agent() = default;
    virtual const char* name() const = 0;
    virtual void process(Blackboard& bb) = 0;   // read + mutate the blackboard
};

} // namespace maestro
```

Every runtime agent implements `Agent`. The Producer owns the list and the loop.
This is the smallest possible orchestration primitive, and that's on purpose — the
demo is about *how you drive it with dev agents*, not about a clever framework.

---

## 4. Agent responsibilities

### 4.1 Producer  (`src/Producer.cpp`)
- Parse the `Brief` into a `MusicalContext`: resolve `key` + `scale` to
  `keyRootMidi` and `scaleSemitones`; seed the RNG.
- Own the pipeline order: `Composer → Arranger → Synth → Critic`.
- Own the retry loop: while `!critique.acceptable && pass < brief.maxPasses`,
  apply `critique.suggestedFix` to the brief/context and re-run from the Composer.
- Never generate notes or samples itself. It coordinates.

### 4.2 Composer  (`src/Composer.cpp`)
- Choose a 4-chord progression from the scale (diatonic triads; e.g. i–VI–III–VII
  in minor). Encode each chord as scale degrees.
- Write a melody: one `Melody` track, notes drawn from the scale, biased toward
  chord tones on strong beats, with rests. Rhythm from a small set of durations.
- Emit a `Chords` track holding the block chords.
- Set `lengthBeats` from `seconds` and `tempoBpm`.
- Deterministic given the RNG.

### 4.3 Arranger  (`src/Arranger.cpp`)
- Add a `Bass` track: root of each chord, on the downbeat, one octave down.
- Add a `Pad` track: sustained chord tones for texture.
- Add a `Drums` track: a simple kick/snare/hat pattern derived from the tempo and
  bar count (encoded via velocity + a chosen `Osc::Noise`/`Square` voice).
- Assign an `Osc` and `gain` per track appropriate to the `mood`
  (e.g. lofi → `Triangle` melody, soft pad; chiptune → `Square`/`Saw`).

### 4.4 Synth  (`src/Synth.cpp`)
- Convert beats to seconds using `tempoBpm` and `sampleRate`.
- For each note: generate the chosen oscillator at the note's frequency
  (`440 * 2^((midi-69)/12)`), shape it with an **ADSR** envelope, scale by
  `velocity * track.gain`, and add it into the mix buffer at the right offset.
- Drums: short noise/impulse bursts with fast decay.
- Normalize to peak ≈ 0.9 and guard against clipping and NaN/Inf.

### 4.5 Critic  (`src/Critic.cpp`)
- Compute three cheap metrics on the `Score` (and optionally the buffer):
  - **dissonance**: fraction of simultaneous intervals that are minor 2nds/tritones.
  - **density**: notes per bar vs. a target band for the mood.
  - **dynamicRange**: spread of note velocities / buffer RMS-to-peak.
- Set `acceptable` and a `suggestedFix` string the Producer understands
  (`"reduce_density"`, `"raise_energy"`, `"resolve_dissonance"`, or `""`).

### 4.6 WavWriter  (`src/WavWriter.cpp`)
- Write a canonical 16-bit PCM `.wav` from the `AudioBuffer`. No dependencies.
- Optionally shell out to the OS player when `--play` is set.

### 4.7 main  (`src/main.cpp`)
- Parse CLI flags into a `Brief`, construct the Producer, run it, write the file.

CLI:

```
--mood <s>   --key <NoteName[m]>   --scale <s>   --tempo <int>
--seconds <double>   --seed <uint>   --passes <int>
--out <path>   --play
```

---

## 5. Algorithms — enough detail to implement, not more

**Key/scale resolution.** Map note names to pitch classes (C=0…B=11), add to a
base octave to get `keyRootMidi`. Scale tables:
`major {0,2,4,5,7,9,11}`, `minor {0,2,3,5,7,8,10}`,
`dorian {0,2,3,5,7,9,10}`, `pentatonic {0,3,5,7,10}` (minor pent).

**Progression.** Pick from a mood-keyed table of degree sequences, e.g.
minor lofi → `[i, VI, III, VII]`. A chord = root scale-degree + 3rd + 5th
stacked within the scale.

**Melody rhythm.** Durations sampled from `{0.5, 1.0, 1.5, 2.0}` beats until a bar
is filled; insert a rest with small probability. Strong beats (1, 3) prefer chord
tones; weak beats allow passing tones.

**ADSR.** Linear attack/decay/release, sustain level per role
(pads long, drums near-zero sustain). Suggested defaults:
melody `A=5ms D=40ms S=0.6 R=120ms`; pad `A=60ms … R=400ms`.

**WAV.** Standard 44-byte header, `PCM`, `channels`, `sampleRate`, 16-bit little
endian samples = `clamp(sample, -1, 1) * 32767`.

---

## 6. Build

`CMakeLists.txt` targets:
- `maestro` — the executable (all of `src/*.cpp`).
- `maestro_tests` — `tests/test_core.cpp`, run via `ctest`.

```cmake
cmake_minimum_required(VERSION 3.16)
project(maestro CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_executable(maestro src/main.cpp src/Producer.cpp src/Composer.cpp
    src/Arranger.cpp src/Synth.cpp src/Critic.cpp src/WavWriter.cpp)
target_include_directories(maestro PRIVATE include)
enable_testing()
add_executable(maestro_tests tests/test_core.cpp src/Composer.cpp
    src/Arranger.cpp src/Synth.cpp src/Critic.cpp)
target_include_directories(maestro_tests PRIVATE include)
add_test(NAME core COMMAND maestro_tests)
```

---

## 7. Acceptance criteria  (what "done" means for the demo)

1. `cmake --build` succeeds with zero warnings at `-Wall -Wextra`.
2. `./maestro --seconds 5` writes a valid `.wav` that plays audible, in-key music.
3. Every sample is finite and within `[-1, 1]` after normalization (a QA test).
4. Two runs with the same `--seed` produce byte-identical output.
5. Changing `--mood` audibly changes the result.
6. The Critic loop demonstrably fires on at least one mood/seed and improves the
   metric it flagged.

---

## 8. Build order / milestones

| # | Milestone | Owner (dev agent) | Proves |
|---|-----------|-------------------|--------|
| 1 | Contracts + Agent interface + CMake skeleton | Architect | The blackboard compiles |
| 2 | WavWriter + a 440 Hz sine `main` | DSP-Engineer | Sound comes out |
| 3 | Composer (progression + melody) | Composer-Engineer | Symbolic music exists |
| 4 | Synth renders a full `Score` | DSP-Engineer | The score is audible |
| 5 | Arranger (bass/pad/drums) | Composer-Engineer | It sounds like a track |
| 6 | Critic + Producer retry loop | Architect + Producer | Orchestration is real |
| 7 | QA tests + `--play` polish + docs | QA + Docs | It's demo-ready |

Milestones 1–2 are the "hello, sound" moment; 6 is the "hello, orchestration"
moment. Structure the live demo around those two beats.
