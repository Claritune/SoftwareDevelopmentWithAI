# BrainCLI — Final Exercise

Build a CLI-based "Second Brain" personal knowledge management system in Python, using AI coding agents and the practices from all three days of the workshop.

## What You're Building

BrainCLI is a simplified Obsidian-like system that stores markdown notes locally, links them together with `[[wiki-style links]]`, and lets you search and query across your knowledge base. Where Obsidian stops at keyword search and simple links, BrainCLI adds AI-powered semantic search and entity extraction using a local LLM.

The full product spec is in [`docs/spec.md`](docs/spec.md).

## Why This Exercise

This isn't a Python exercise — it's a software development exercise. The system is deliberately designed so that building it well requires applying the methodology and tooling from all three days of the workshop. Building it without that methodology will produce a working prototype, but one that demonstrates exactly the quality problems we discussed on Day 2.

## Topics Covered

### Day 1 — Methodology and Tooling
- Planning with QRSPI before jumping to code
- Setting up AGENTS.md as your project constitution
- Writing rules scoped to file types and project areas
- Creating skills with proper descriptions, constraints, and progressive disclosure
- Building hooks for guardrails (token budgets, linting)
- Designing deep modules with simple interfaces and complex internals

### Day 2 — Quality and Testing
- TDD to drive implementation of core modules
- Unit testing with mocking (isolating modules from their dependencies)
- Property-based testing for data roundtrip invariants
- Mutation testing to find gaps in your test suite
- Integration testing across the full pipeline
- Keeping tests immutable — fix the code, not the tests

### Day 3 — Advanced Topics
- RAG and vector search for semantic note retrieval
- Local LLM usage via Ollama for entity extraction
- Temporal knowledge modeling (facts that change over time)
- Writing ADRs for key design decisions
- Security awareness (path traversal, file scope boundaries)
- Code review using AI as an additional gate

### Across All Days
- Modular architecture that maps to subagent boundaries (Reverse Conway's Law)
- Managing context windows and token budgets
- Reviewing AI-generated code critically (the plausibility trap)
- Measuring what matters: code churn, intervention rate, code durability

## Prerequisites

- Python 3.12+
- A coding agent (Cursor, Claude Code, or similar)
- Ollama with Llama 3.1 8B pulled and running (`ollama pull llama3.1:8b`)
- pytest

## Getting Started

1. Read the [product spec](SPEC.md)
2. Don't start coding yet
3. Set up your project: AGENTS.md, rules, hooks
4. Plan using QRSPI — questions first, then research, then design
5. Implement one feature at a time, end-to-end. For example: "create a note and retrieve it" is one slice that cuts through storage, frontmatter, and CLI. Get it working and tested before moving to the next feature. Don't build all of storage, then all of search, then wire them together — you'll have nothing runnable until the very end.
6. Document your key decisions as ADRs

## Repository Structure

```
braincli/
├── docs/
│   ├── spec.md              # Product spec (start here)
│   └── adr/                 # Your architecture decision records
├── src/                     # Your implementation
├── tests/                   # Your tests
├── notes/                   # Default vault directory (sample notes)
└── README.md                # This file
```

## What Success Looks Like

A working BrainCLI is good. A working BrainCLI built with clear module boundaries, tested with multiple testing strategies, documented with ADRs, and developed using a methodical agent workflow — that's the point.

Pay attention to how you work, not just what you produce.