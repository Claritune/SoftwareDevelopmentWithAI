# Software Development with AI Workshop

Hands-on workshop materials for learning how to develop software effectively with AI coding agents. Covers structured planning methodologies, testing strategies, and practical AI collaboration patterns across multiple languages and problem domains.

## Repository Structure

```
.
├── demos/          # Instructor-led walkthroughs
├── exercises/      # Hands-on tasks for participants
└── solutions/      # Reference implementations
```

## Demos

### Python

| Demo | Description |
|------|-------------|
| [url-monitor-cli](demos/python/url-monitor-cli/) | Build a URL uptime monitor from scratch using the QRSPI workflow (Question, Research, Structure, Plan, Implement). Demonstrates how structured alignment prevents silent architectural decisions. |
| [url-monitor-service-reference](demos/python/url-monitor-service-reference/) | FastAPI-based URL monitoring service with async health checking, SQLite persistence, and background scheduling. Reference architecture for the service exercise. |
| [shrinking](demos/python/shrinking/) | Interactive demo of property-based testing with Hypothesis, showing how the shrinking algorithm simplifies failing test cases to minimal reproducers. |

### C++

| Demo | Description |
|------|-------------|
| [url-monitor-cli](demos/cpp/url-monitor-cli/) | C++ implementation of the URL monitor using CMake, cpr, CLI11, and Catch2. Includes six step-by-step QRSPI phases in the `steps/` directory. |

## Exercises

### Python

| Exercise | Description | Key Topics |
|----------|-------------|------------|
| [url-monitor-cli](exercises/python/url-monitor-cli/) | Build a URL monitoring CLI following the full QRSPI workflow. Alignment steps take 30-60 min; implementation takes 20-40 min. | QRSPI methodology, structured planning |
| [url-monitor-service](exercises/python/url-monitor-service/) | Extend the CLI concept into a FastAPI REST service with SQLite, async checking, and a background scheduler. | REST API design, async programming, SQLite |
| [concurrent-agents](exercises/python/concurrent-agents/) | Fix 5 independent bugs in a Task Manager API by launching multiple AI agents in parallel. | Concurrent agent coordination, debugging |
| [filling-buckets](exercises/python/filling-buckets/) | Determine if a target bucket can be filled exactly using smaller buckets. Classic backtracking/DP problem. | Algorithms, dynamic programming |
| [valve-control](exercises/python/valve-control/) | Design a software module for adjusting water system valves with safety constraints around pipe pressure. | System design, hardware-software interface |
| [spreadsheets](exercises/python/spreadsheets/) | Aggregate weekly team timesheets from Excel files into a formatted monthly HR report with category mapping. | Data processing, Excel automation |
| [image-comparison](exercises/python/image-comparison/) | Build a computer vision pipeline to detect and visualize differences between two images using Pillow and NumPy. | Image processing, pixel analysis |
| [langchain](exercises/python/langchain/) | Extract structured company data from unstructured text using LangChain + Ollama with Pydantic validation. | LLM integration, structured extraction |
| [spec-02](exercises/python/spec-02/) | Design a Hardware-in-the-Loop (HIL) test bench management system for automotive ECU testing. | Domain-driven design, specification |
| [generate-repo](exercises/python/generate-repo/) | Generate a sample Express.js project to learn token budget tracking with Cursor Hooks. | Context management, agent constraints |
| [brain-cli](exercises/python/brain-cli/) | Capstone: build a local-first knowledge management system with wiki-links, entity extraction via Ollama, and semantic search. | Full QRSPI, TDD, local LLM, security |

### C++

| Exercise | Description | Key Topics |
|----------|-------------|------------|
| [intro](exercises/cpp/intro/) | Parse and evaluate nested expressions like `Sum(Exponent(3, 2), -2)` using recursive descent. | Parsing, expression trees, C++17 |

### C#

| Exercise | Description | Key Topics |
|----------|-------------|------------|
| [intro](exercises/csharp/intro/) | Same expression evaluator as C++ but using C# records, pattern matching, and .NET conventions. | Parsing, pattern matching, .NET 8 |

## Solutions

| Solution | Exercise |
|----------|----------|
| [filling-buckets](solutions/python/filling-buckets/) | Reference implementation with recursive backtracking and comprehensive test suite. |

## Core Methodology: QRSPI

Several demos and exercises teach the **QRSPI** workflow for AI-assisted development:

1. **Question** -- surface clarifying questions before writing any code
2. **Research** -- examine existing patterns and constraints in the codebase
3. **Design** -- make and document architectural decisions
4. **Structure** -- break work into vertical implementation slices
5. **Plan** -- create a tactical plan with verification steps for each slice
6. **Implement** -- build slice by slice with tests at each phase

The key insight: *speed comes from alignment, not typing*. Spending 30-60 minutes on steps 1-5 prevents hours of rework caused by silent assumptions.

## Prerequisites

- **Python 3.12+** with [uv](https://docs.astral.sh/uv/) (for Python exercises)
- **C++17 compiler** and CMake (for C++ exercises)
- **.NET 8.0+** (for C# exercises)
- **Ollama** with Llama 3.1 8B (for LLM-related exercises)
- An AI coding agent (Cursor, Claude Code, or similar)
