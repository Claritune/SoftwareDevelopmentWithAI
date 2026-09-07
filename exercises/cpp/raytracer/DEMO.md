# DEMO — Live Flow

The minute-by-minute script for running the mini ray tracer as a live multi-agent orchestration demo in VS Code with Copilot. Target length: **~25 minutes** of active demo plus Q&A. Every step lists what you *do*, what you *say*, and what can go wrong.

The golden rule of a live agent demo: **the agents will not do exactly what you expect, and that is the show.** Narrate the coordination, not the code. If an agent goes off-script, that is a teaching moment, not a failure.

---

## Before you start (setup — do this off-stage)

- [ ] VS Code open with Copilot + Copilot Chat, agent mode on.
- [ ] The six agent chat modes from [SUBAGENTS.md](./SUBAGENTS.md) installed in the workspace.
- [ ] Workspace contains **only** `README.md`, `SPEC.md`, `SUBAGENTS.md`, `DEMO.md` — no code yet.
- [ ] A terminal open, `cmake` and a C++17 compiler verified (`cmake --version`, `c++ --version`).
- [ ] An image viewer ready to open `out/render.png` (VS Code's built-in preview is fine).
- [ ] **A pre-baked `out/render.png`** stashed outside the workspace as an insurance frame, so you always have a picture to show even if the live build stalls.
- [ ] Font size up, minimap off, terminal readable from the back row.

**Rehearse once end to end.** Agent runs vary; you want to know roughly how long each dispatch takes on your machine and network.

---

## Act 0 — Frame it (2 min)

**Say:**
> "We're going to build a real C++ ray tracer — a program that renders a 3D scene to an image — and we're not going to write a line of it ourselves. A team of six AI agents will. My job, and the job of the lead agent, is *orchestration*: deciding who builds what, defining how the pieces fit, and stitching it together. Watch for two things: where the agents work in parallel, and where one has to wait for another."

**Show:** the empty workspace — just the four markdown files. Open `SUBAGENTS.md` to the "team at a glance" table for five seconds so people see the roster.

**Point to make:** the docs *are* the design. The agents are only as good as the decomposition and the interfaces you hand them.

---

## Act 1 — The Orchestrator plans and freezes interfaces (4 min)

**Do:** Switch to the **Orchestrator** chat mode. Prompt:

> "Read SPEC.md. Produce the build plan (who builds what, what's parallel, what's sequential), then create the shared interface headers with signatures only and TODO bodies, plus a CMakeLists skeleton. Vendor stb_image_write.h. Don't implement any module yet."

**Show:** the plan it prints and the interface-only headers appearing in `src/`.

**Say, while it works:**
> "Notice it's not writing the ray tracer. It's writing *contracts* — the shape of `vec3`, the shape of `hit`. This is the single most important step. Once these signatures are frozen, five agents can work against them without ever talking to each other."

**Watch for / recover:**
- If it starts implementing bodies, interrupt: *"Just the signatures for now — bodies are for the specialists."* Great live illustration of keeping the lead in its lane.
- If it invents an interface that contradicts SPEC, point it back at SPEC §4. Shows why the written spec matters.

---

## Act 2 — Parallel fan-out: Math + I/O (5 min)

**Do:** Dispatch **Math** and **I/O & CLI** back to back — they have no dependency on each other.

Math prompt:
> "Implement vec3.hpp and ray.hpp against the frozen interfaces. Header-only, C++17, warnings-clean."

I/O prompt:
> "Implement color.hpp and image_writer.hpp against the frozen interfaces, plus the CLI parse struct from SPEC §5."

**Say:**
> "These two share nothing — `vec3` math and PNG writing don't touch. So they go at the same time. In a real setup these could be two agents literally running concurrently. This is the parallel edge of the dependency graph."

**Show:** both modules filling in. Skim the `refract` function in `vec3.hpp` — *"this is Snell's law; a human took an afternoon on this once, here it's a few seconds."*

**Watch for / recover:**
- I/O may forget the NaN guard or gamma correction. Don't fix it now — note it; QA should catch it. *(If QA misses it, that's your cue to show the speckled image and route it back.)*

---

## Act 3 — Sequential handoff: Geometry → Rendering (6 min)

**Do:** Now dispatch **Geometry**. Emphasize it *couldn't* start until Math was done.

Geometry prompt:
> "Implement hittable.hpp, sphere.hpp, hittable_list.hpp against the frozen interfaces, using vec3/ray read-only. Forward-declare material only."

**Say:**
> "This one had to wait. Geometry needs `vec3` and `ray` to even compile. That's a sequential edge — the handoff. The interface froze earlier means the handoff is clean: Geometry got exactly the `vec3` it was promised."

**Then dispatch Rendering** once Geometry lands:

> "Implement camera.hpp, material.hpp, and ray_color per SPEC §6, using Math and Geometry read-only."

**Show:** the `dielectric` material and the `ray_color` recursion. *"This recursion is the whole ray tracer in eight lines — bounce, shade, repeat until it runs out of depth."*

**Watch for / recover:**
- The classic bug: forgetting `t_min = 0.001`, giving shadow acne. If it happens, *let it* — it's the best visual bug in graphics and a perfect QA catch.

---

## Act 4 — Integrate and first build (3 min)

**Do:** Back to **Orchestrator**:

> "Integrate all modules into main.cpp with the three-spheres scene from SPEC §7, wire the CMake target, and run the build."

**Show:** the terminal build. Then run:

```bash
./build/raytracer --width 200 --samples 4 --out out/preview.png
```

Fast and grainy on purpose. Open it.

**Say:**
> "There it is — rough, noisy, four samples per pixel. But those are real reflections in the metal sphere and real refraction in the glass. The orchestrator didn't write the math; it wired six people's work into one program."

**Watch for / recover:**
- **First build almost never passes.** A missing include, a signature that drifted, the one-definition-rule on `STB_IMAGE_WRITE_IMPLEMENTATION`. Do not panic — this is Act 5.

---

## Act 5 — QA finds the seam, Orchestrator routes the fix (4 min) — *the money moment*

**Do:** Switch to **QA**:

> "Build with -Wall -Wextra, run the SPEC §9 unit tests, and run the §8 acceptance checklist. Report PASS/FAIL per item and name the likely owning agent for each failure."

**Show:** the QA report. There will be at least one FAIL.

**Then back to Orchestrator** with the QA report:

> "QA reports <symptom>. Route the fix to the owning agent and re-integrate."

**Say — this is the core lesson:**
> "Here's the thing about orchestration: the lead does *not* dive in and fix it. It reads the symptom, identifies whose contract broke, and sends it back to that owner. That's the difference between a coordinator and a hero. Things break at the *seams* between agents, and having an owner for every seam is what makes the recovery fast."

**Watch for / recover:**
- If QA somehow reports all green on the first try (rare), manufacture the lesson: *"Let's ask for a stretch goal and watch a new interface ripple through"* — dispatch a `--threads` request and show the coordination.

---

## Act 6 — The payoff (2 min)

**Do:** Run the nice version:

```bash
./build/raytracer --width 800 --samples 100 --out out/render.png
```

Open `out/render.png` full screen.

**Say:**
> "Six agents. One orchestrator. Zero lines of C++ written by me. Smooth edges, a mirror sphere, a glass sphere bending the world behind it — a real image that didn't exist twenty-five minutes ago."

*(If the live 100-sample render is slow, kick it off during Act 5 and reveal it here, or fall back to your pre-baked insurance frame.)*

---

## Act 7 — Debrief (3 min, into Q&A)

Land these four points explicitly:

1. **Decomposition is the skill.** The agents were easy to direct because the split was clean. A bad split makes every agent's job ambiguous.
2. **Interfaces are the contract.** Freezing signatures first is what let five agents work without colliding.
3. **Orchestration is coordination, not code.** The lead wrote the least and mattered the most.
4. **Failures live at the seams.** Recovery was fast because every seam had an owner.

**Questions to pose back to the room:**
- "How would *you* have split this? More agents? Fewer?"
- "What would happen if two agents both thought they owned `vec3`?"
- "Where would this break on a 50,000-line codebase — and what would you change?"

---

## Timing summary

| Act | Content | Minutes |
|-----|---------|---------|
| 0 | Frame it | 2 |
| 1 | Orchestrator: plan + interfaces | 4 |
| 2 | Parallel: Math + I/O | 5 |
| 3 | Sequential: Geometry → Rendering | 6 |
| 4 | Integrate + first build | 3 |
| 5 | QA finds seam, Orchestrator routes fix | 4 |
| 6 | The payoff image | 2 |
| 7 | Debrief + Q&A | 3+ |
| | **Total active demo** | **~25 + Q&A** |

---

## Contingency table

| If this happens | Do this |
|-----------------|---------|
| An agent stalls / no response | Move on to a parallel agent; return to it. Never wait in silence. |
| Build won't pass after two fix cycles | Show the grainy `--samples 4` preview you already have; the point is orchestration, not a pixel-perfect render. |
| Live 100-sample render too slow | Start it during Act 5; reveal in Act 6. Insurance frame if needed. |
| Agent rewrites an interface it doesn't own | Perfect — narrate it: "this is exactly the collision the Orchestrator prevents," and route it back. |
| Copilot/network down entirely | Walk the four docs and a pre-recorded screen capture; the design story stands on its own. |
| Q&A goes deep on ray tracing math | Redirect: "great question, but the star here is the workflow — grab me after for the Snell's law." |

---

## One-line pre-flight

Before you present, run this and confirm a clean image so you have your insurance frame:

```bash
cmake -S . -B build && cmake --build build && \
./build/raytracer --width 800 --samples 100 --out out/render.png && \
echo "insurance frame ready: out/render.png"
```
