# Exercise: Expression Parser & Evaluator (C#)

## Overview

Build a C# console application that reads a nested function-call expression from the user, evaluates it, and prints both the human-readable mathematical notation and the result.

**You are expected to use an AI coding agent (GitHub Copilot, Claude Code, Cursor, or similar) throughout this exercise.** The goal is to practice collaborating with an AI assistant on a real programming task — not to write every line by hand.

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

### More Examples

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

## Supported Operations

| Function | Math Symbol | Description |
|---|---|---|
| `Sum(a, b)` | `+` | Addition |
| `Mult(a, b)` | `*` | Multiplication |
| `Div(a, b)` | `/` | Integer division |
| `Exponent(a, b)` | `^` | Exponentiation |

Each operation takes exactly **two arguments**. Arguments can be:
- An integer (positive or negative, e.g. `3`, `-7`)
- Another operation (enabling nesting to any depth)

---

## Requirements

1. **Parse** the input string into a tree of operations and integer values.
2. **Evaluate** the tree to produce an integer result.
3. **Format** the tree into a human-readable infix string with full parenthesization (every operation is wrapped in parentheses).
4. **Print** the formatted expression followed by ` = ` and the result.
5. Use **integer arithmetic** throughout (no floating-point).

---

## Getting Started

### Prerequisites

- .NET SDK 8.0 or later ([download](https://dotnet.microsoft.com/download))
- An AI coding assistant set up in your editor or terminal

### Create the Project

```bash
cd exercise_intro_csharp
dotnet new console -n ExpressionEvaluator
cd ExpressionEvaluator
```

### Suggested Project Structure

```
ExpressionEvaluator/
  Program.cs              <-- entry point
  Models/
    Expression.cs          <-- expression tree types
  Services/
    Parser.cs              <-- expression parsing
    Evaluator.cs           <-- tree evaluation
    Formatter.cs           <-- infix string formatting
  ExpressionEvaluator.csproj
```

You're free to organize the code however you like — putting everything in `Program.cs` is fine too.

### Build & Run

```bash
dotnet run
# Then type: Sum(Exponent(3, 2), -2)
# Expected: ((3 ^ 2) + (-2)) = 7
```

Or pipe input directly:

```bash
echo "Sum(Exponent(3, 2), -2)" | dotnet run
```

---

## Step-by-Step Guide

Work through these steps **with your AI assistant**. At each step, describe what you need to the AI, review the code it generates, and iterate until it works.

### Step 1 — Define the Expression Tree

Ask your AI assistant to help you design a class hierarchy that represents an expression tree. Each node is either:
- A **number** (leaf node holding an integer), or
- An **operation** (internal node with an operator type and two child expressions).

C# offers several good approaches here — abstract classes, interfaces, or records. Let the AI suggest one and discuss the tradeoffs.

> **Prompt idea:** *"Help me define a C# class hierarchy for an expression tree. A node is either an integer literal or a binary operation (Sum, Mult, Div, Exponent) with two children. What's the best approach — abstract class, interface, or records?"*

### Step 2 — Evaluate the Tree

Implement a method that takes an expression tree and returns the integer result by recursively evaluating it.

> **Prompt idea:** *"Write a method that evaluates this expression tree recursively. Sum adds, Mult multiplies, Div does integer division, and Exponent raises to a power. Use `Math.Pow` or a loop for exponentiation and cast the result to int."*

### Step 3 — Format the Tree as a String

Implement a method that converts the tree into a fully parenthesized infix string. Numbers just become their string representation. Operations become `(left OP right)`.

> **Prompt idea:** *"Write a method that converts the expression tree to an infix string like ((3 ^ 2) + (-2)). Every operation should be wrapped in parentheses."*

### Step 4 — Parse the Input

This is the most involved step. You need to turn a string like `Sum(Exponent(3, 2), -2)` into the expression tree from Step 1.

Key parsing challenges:
- Recognize the function name (`Sum`, `Mult`, `Div`, `Exponent`)
- Handle the opening `(`, comma `,`, and closing `)`
- Recursively parse nested expressions
- Handle negative numbers

> **Prompt idea:** *"Write a recursive descent parser in C# that takes a string like `Sum(Exponent(3, 2), -2)` and builds the expression tree I defined earlier."*

### Step 5 — Wire It All Together

Read a line from the console, parse it, evaluate it, format it, and print the result.

> **Prompt idea:** *"Write the Main method that reads a line from Console.ReadLine(), parses it into the expression tree, evaluates it, formats it, and prints: formatted_expression = result"*

### Step 6 — Test

Test with all the examples from the table above. Fix any issues you find — again, with help from the AI.

---

## Tips for Working with the AI Assistant

1. **Start small.** Get a simple case working (`Sum(3, 5)`) before tackling deep nesting.
2. **Be specific in your prompts.** Instead of "write me a parser," describe the exact input format and the data structure it should produce.
3. **Review the generated code.** Don't blindly accept — read through it, understand the approach, and ask the AI to explain anything unclear.
4. **Iterate.** If the first attempt doesn't handle edge cases (like negative numbers), describe the failing case and ask the AI to fix it.
5. **Ask "why" questions.** Use the AI to learn, not just to produce code. Ask it to explain design choices, alternative approaches, or tricky parts.

---

## Bonus Challenges

If you finish early, try extending the program:

- **Error handling:** Print a clear error message for malformed input (e.g. `Sum(3,)`, `Foo(1,2)`, unmatched parentheses).
- **More operations:** Add `Sub` (subtraction), `Mod` (modulus), or `Neg` (unary negation — single argument).
- **Floating-point mode:** Support decimal numbers and produce `double` results.
- **Interactive mode:** Loop continuously, reading and evaluating one expression per line until EOF.
- **Pattern matching:** Refactor evaluation and formatting to use C# pattern matching with `switch` expressions.
