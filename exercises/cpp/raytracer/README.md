# Mini Ray Tracer — A Multi-Agent Orchestration Demo

A small, self-contained C++ ray tracer built **entirely by a team of specialized AI agents** orchestrated from inside VS Code with GitHub Copilot. The point of this project is not the ray tracer — it is watching a *lead agent* decompose a real piece of software, hand each piece to a specialist, and integrate the results into something that produces a real rendered image.

You end the demo with a picture like this: a few shaded spheres on a ground plane, soft anti-aliased edges, a metal sphere reflecting its neighbors, and a glass sphere bending the scene behind it — written to a PNG by code that five different agents wrote and one agent stitched together.

---

## Why a ray tracer for this demo

Three reasons it works better than a to-do app or a REST service:

**It has a real, satisfying output.** A rendered image is a visceral "it actually works" moment for a room. Nobody is squinting at a passing test — they are looking at a picture that did not exist five minutes ago.

**It decomposes cleanly.** A ray tracer is a set of modules with narrow, well-understood interfaces: vector math, ray-geometry intersection, shading, image output. Each maps naturally onto one specialist agent, which is exactly what you want when you are teaching *how work gets divided among agents*.

**It is small enough to finish live.** The whole thing is roughly 500–700 lines of C++17 with zero external dependencies (a single-header PNG writer is vendored in). It builds with CMake in seconds and runs in under a second.

---

## What "multi-agent orchestration" means here

This is not one Copilot chat doing everything. The work is split across **six agents**, each with a defined role, scope, and contract:

| Agent | Owns |
|-------|------|
| **Orchestrator** (lead) | The plan, the shared interfaces/headers, integration, final build |
| **Math** | `vec3`, `ray`, numeric utilities |
| **Geometry** | `hittable`, `sphere`, `hittable_list`, intersection logic |
| **Rendering** | `camera`, ray color, materials (diffuse / metal / glass), anti-aliasing |
| **I/O & CLI** | color output, PPM/PNG writer, argument parsing, progress reporting |
| **QA** | unit tests, build verification, acceptance checks |

The Orchestrator defines the interfaces *first*, then fans the work out. Some agents run in parallel (Math and I/O have no dependency on each other); others hand off in sequence (Geometry can't finish until Math's `vec3` contract is fixed). That interplay — parallel fan-out plus sequential handoff, coordinated through shared contracts — is the whole lesson.

See **[SUBAGENTS.md](./SUBAGENTS.md)** for each agent's full definition and the orchestration graph.

---

## Repository layout

The docs come first; the code is what the agents produce during the demo.

```
mini-raytracer-demo/
├── README.md          ← you are here
├── SPEC.md            ← what to build: modules, interfaces, acceptance criteria
├── SUBAGENTS.md       ← the agents, their roles, and how they're orchestrated
├── DEMO.md            ← the live demo flow, minute by minute
│
└── (produced during the demo)
    ├── CMakeLists.txt
    ├── src/
    │   ├── vec3.hpp          (Math)
    │   ├── ray.hpp           (Math)
    │   ├── hittable.hpp      (Geometry)
    │   ├── sphere.hpp        (Geometry)
    │   ├── hittable_list.hpp (Geometry)
    │   ├── camera.hpp        (Rendering)
    │   ├── material.hpp      (Rendering)
    │   ├── color.hpp         (I/O)
    │   ├── image_writer.hpp  (I/O)
    │   └── main.cpp          (Orchestrator + Rendering)
    ├── third_party/
    │   └── stb_image_write.h (vendored)
    ├── tests/
    │   └── test_*.cpp        (QA)
    └── out/
        └── render.png        ← the payoff
```

---

## Quickstart (after the agents have built it)

```bash
cmake -S . -B build
cmake --build build
./build/raytracer --width 400 --samples 32 --out out/render.png
```

Open `out/render.png`. That's the whole thing.

Tune the knobs to trade quality for speed during a live session:

```bash
# Fast preview (grainy, instant)
./build/raytracer --width 200 --samples 4 --out out/preview.png

# Nicer final (a few seconds)
./build/raytracer --width 800 --samples 100 --out out/final.png
```

---

## Prerequisites

- **VS Code** with the **GitHub Copilot** and **Copilot Chat** extensions, agent mode enabled
- A **C++17 compiler** (clang, gcc, or MSVC) and **CMake ≥ 3.16**
- The six agent definitions from **[SUBAGENTS.md](./SUBAGENTS.md)** set up as custom chat modes / agent files in your workspace

No graphics libraries, no package manager, no network access required at build time.

---

## How to run the demo

Follow **[DEMO.md](./DEMO.md)**. In short:

1. Open the empty workspace with only the four `.md` files and the agent definitions.
2. Give the Orchestrator the goal and let it produce the plan and the shared interfaces.
3. Dispatch the specialist agents — parallel where possible, in sequence where dependencies demand it.
4. Let QA build and test; watch the Orchestrator resolve the inevitable interface mismatch.
5. Run the binary. Open the image. Applause optional.

---

## What the audience should walk away with

- Decomposition is the real skill: a good split makes the agents' jobs unambiguous.
- **Interfaces are the contract** that lets independent agents work without stepping on each other.
- Orchestration is coordination, not code — the lead agent's value is the plan and the integration, not writing the most lines.
- Things break at the seams (interface mismatches), and recovering from that gracefully is a feature of the workflow, not a failure of it.

---

*Built as an Edge3 Studio teaching demo for agentic development in VS Code.*
