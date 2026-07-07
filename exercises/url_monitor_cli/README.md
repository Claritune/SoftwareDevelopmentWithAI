# Exercise: Building a URL Monitor with AI — The Right Way

## The Problem

Open your AI assistant and type: *"Build me a CLI tool that monitors URLs for uptime."*

Watch what happens. The agent will immediately start writing code. It will choose a language, pick libraries, design an architecture, define output formats, and make dozens of decisions — all without asking you a single question.

The result might work. But it won't be what you wanted, because you never said what you wanted. You just said *roughly* what to build, and the AI filled in every gap silently.

This exercise teaches you a structured approach to AI-assisted development that fixes this. Instead of cramming all your intent into a single prompt, you'll build alignment through a series of short, reviewable steps — each producing a document you verify before moving on.

## What You'll Build

A Python CLI tool that monitors URLs for uptime:

```bash
url-monitor https://example.com https://api.example.com/health \
  --failure-threshold 3 \
  --interval 30 \
  --timeout 10 \
  --log-file monitor.log
```

```
[2026-06-11T10:00:00Z] DOWN  https://example.com  (3 consecutive failures, last: HTTP 503)
[2026-06-11T10:02:00Z] UP    https://example.com  (HTTP 200, 142ms)
```

But the tool itself is secondary. The real deliverable is learning a workflow that works for *any* AI-assisted project.

## The Steps

Each step produces a reviewable artifact. The agent does not write code until Step 6.

| Step | What You Do | What It Prevents |
|------|-------------|------------------|
| [**1. Questions**](steps/01-questions.md) | Surface what the agent doesn't know | Silent assumptions about scope, libraries, behavior |
| [**2. Research**](steps/02-research.md) | Map the existing codebase *(skip for greenfield)* | Plans built on wrong assumptions about existing code |
| [**3. Design**](steps/03-design.md) | Align on architecture and patterns | Discovering wrong patterns after 500 lines of code |
| [**4. Structure**](steps/04-structure.md) | Break work into testable vertical slices | "Nothing works until everything is assembled" |
| [**5. Plan**](steps/05-plan.md) | Tactical implementation details | Unconstrained plans that smuggle in design decisions |
| [**6. Implement**](steps/06-implement.md) | Build, verify, review, ship | Untested code, missing commits, unread diffs |

**This exercise is greenfield** (no existing code), so you'll skip Step 2 and go directly from Questions to Design.

## Prerequisites

- Python 3.11+
- An AI coding assistant (Claude Code, Cursor, or similar) with the skills in `.cursor/skills/` loaded
- Git

## How Long This Takes

- Steps 1–5 (alignment): ~30–60 minutes
- Step 6 (implementation): ~20–40 minutes

Most of that time is thinking and reviewing, not waiting for the AI.

## Getting Started

1. Read `goal.md` — a one-line description of what you're building
2. Open [Step 1: Questions](steps/01-questions.md)
3. Follow each step in order

## Project Layout

```
url_monitor_cli/
├── README.md               ← you are here
├── goal.md                 ← starting point for Step 1
├── steps/                  ← exercise instructions
│   ├── 01-questions.md
│   ├── 02-research.md
│   ├── 03-design.md
│   ├── 04-structure.md
│   ├── 05-plan.md
│   └── 06-implement.md
├── .cursor/skills/         ← agent skills for each step
├── docs/skills/            ← human-readable copies of skills
├── src/                    ← application code (empty until Step 6)
└── thoughts/               ← artifacts produced during Steps 1–5
```

## Deliverables

When you're done, you should have:

- [ ] `thoughts/<task-id>/questions.md` — questions that cover scope, technical choices, and output
- [ ] `thoughts/<task-id>/answers.md` — your explicit decisions
- [ ] `thoughts/<task-id>/design.md` — architecture document you reviewed and corrected
- [ ] `thoughts/<task-id>/structure.md` — vertical slices with verification checkpoints
- [ ] `thoughts/<task-id>/plan.md` — tactical plan with all checkboxes checked
- [ ] Working CLI tool with passing tests
- [ ] Git history with one commit per implementation phase

## Key Principle

**The speed comes from the alignment, not from the typing.**

An AI can write code in minutes. But without alignment, you'll spend hours debugging code that technically works but isn't what you wanted. The five alignment steps (30–60 minutes) prevent the multi-hour rework cycle that comes from jumping straight to code.

## Further Reading

- [From RPI to QRSPI](https://alexlavaee.me/blog/from-rpi-to-qrspi/) — the methodology behind this workflow
- Demo project: `../demos/url_monitor_cli_demo/` — a completed version of this exercise
