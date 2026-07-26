# Exercise: Expression Parser & Evaluator — Code Review (C#)

## Overview

This exercise provides a **complete, working implementation** of an expression parser and evaluator in C#. Your task is to:

1. **Read and understand** the code — trace through the parsing logic, understand the expression tree structure, and follow the evaluation flow.
2. **Review the implementation** — identify design choices, discuss tradeoffs with your AI assistant, and consider alternative approaches.
3. **Write tests** — the provided test suite covers many cases, but you'll extend it with additional edge cases and scenarios.

**You are expected to use an AI coding agent (GitHub Copilot, Claude Code, Cursor, or similar) throughout this exercise.** The goal is to practice reviewing and understanding AI-generated code, not just producing it.

---

## What the Program Does

The program reads a single line of input that looks like a nested function call:

```
Sum(Exponent(3, 2), -2)
```

It then outputs the expression in standard math notation alongside the computed result:

```
((3 ^ 2) + (-2)) = 7
```

### Examples

| Input | Output |
|---|---|
| `Sum(3, 5)` | `(3 + 5) = 8` |
| `Mult(4, 5)` | `(4 * 5) = 20` |
| `Div(10, 3)` | `(10 / 3) = 3` |
| `Exponent(2, 10)` | `(2 ^ 10) = 1024` |
| `Sum(Exponent(3, 2), -2)` | `((3 ^ 2) + (-2)) = 7` |
| `Exponent(Mult(3, 2), 2)` | `((3 * 2) ^ 2) = 36` |
| `Sum(Mult(2, 3), Div(10, 2))` | `((2 * 3) + (10 / 2)) = 11` |
| `Mult(Sum(1, 2), Sum(3, 4))` | `((1 + 2) * (3 + 4)) = 21` |
| `Sum(Sum(Sum(1, 2), 3), 4)` | `(((1 + 2) + 3) + 4) = 10` |

---

## Getting Started

### Prerequisites

- .NET SDK 8.0 or later ([download](https://dotnet.microsoft.com/download))
- An AI coding assistant set up in your editor or terminal

### Build & Run

```bash
cd ExpressionEvaluator
echo "Sum(Exponent(3, 2), -2)" | dotnet run
# Expected: ((3 ^ 2) + (-2)) = 7
```

### Run Tests

```bash
cd ExpressionEvaluator
dotnet run -- --test
```

---

## Project Structure

```
parser-code-review/
├── README.md                       <-- this file
└── ExpressionEvaluator/
    ├── ExpressionEvaluator.csproj
    ├── Program.cs                  <-- entry point + test runner
    ├── Expr.cs                     <-- expression tree types
    └── Parser.cs                   <-- recursive descent parser
```

---

## Code Review Guide

Work through these review tasks **with your AI assistant**. The goal is to understand the code deeply, not just confirm it works.

### 1. Trace the Data Flow

Pick an input like `Sum(Mult(2, 3), Div(10, 2))` and trace it through the code:
- How does the `Parser` consume characters?
- What `Expr` nodes does it construct?
- How does `Evaluate()` traverse the tree?
- How does `Format()` produce the output string?

> **Prompt idea:** *"Walk me through how the parser processes `Sum(Mult(2, 3), Div(10, 2))` step by step. Show me the expression tree it builds and how evaluation works."*

### 2. Discuss Design Choices

The implementation uses several C# idioms. Discuss with your AI assistant:
- **Abstract record hierarchy** vs. a single class with an enum discriminator — what are the tradeoffs?
- **Pattern matching** in `Evaluate()` and `Format()` — could this use virtual dispatch instead? When is each approach better?
- **ParseError exception** — is this the right error handling strategy? What about returning a `Result<T>` type?
- **ReadOnlySpan\<char\>** — why is it used? What are the performance implications?

> **Prompt idea:** *"Compare the abstract record approach used here with a single Expression class that uses an enum for the operation type. What are the tradeoffs for extensibility, type safety, and pattern matching?"*

### 3. Extend the Tests

The provided test runner covers basic cases, edge cases, whitespace, deep nesting, and error cases. Add tests for:
- Extremely large results (integer overflow)
- Unicode or special characters in input
- Very long expressions (stress test)
- Single-number expressions (no operation)
- Any other edge cases you can think of

> **Prompt idea:** *"What edge cases are missing from the test suite? Help me write tests for them."*

---

## Bonus Challenges

- **Refactor to OOP:** Convert the pattern-matching `Evaluate()` and `Format()` methods to virtual methods on each record type. Compare the two approaches.
- **Add operations:** Add `Sub` (subtraction), `Mod` (modulus), or `Neg` (unary negation). How much code changes?
- **Error recovery:** Instead of throwing on the first error, collect all errors and report them together.
- **Property-based testing:** Use a library like FsCheck to generate random expressions and verify invariants (e.g., `Format(Parse(x)) == x` for normalized inputs).
