# Exercise: Expression Parser & Evaluator (C++)

## Overview

Build a C++ command-line program that reads a nested function-call expression from the user, evaluates it, and prints both the human-readable mathematical notation and the result.

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

- A C++ compiler (g++, clang++, or MSVC)
- An AI coding assistant set up in your editor or terminal

### Suggested Project Structure

```
exercise_intro_cpp/
  README.md          <-- this file
  main.cpp           <-- entry point
  parser.h / .cpp    <-- expression parsing
  expr.h / .cpp      <-- expression tree & evaluation
  Makefile            <-- (optional) build script
```

You're free to organize the code however you like — a single `main.cpp` is fine too.

### Build & Run

```bash
# Example with g++
g++ -std=c++17 -o expr_eval main.cpp parser.cpp expr.cpp
echo "Sum(Exponent(3, 2), -2)" | ./expr_eval
# Expected: ((3 ^ 2) + (-2)) = 7
```

---

## Step-by-Step Guide

Work through these steps **with your AI assistant**. At each step, describe what you need to the AI, review the code it generates, and iterate until it works.

### Step 1 — Define the Expression Tree

Ask your AI assistant to help you design a data structure that represents an expression tree. Each node is either:
- A **number** (leaf node holding an integer), or
- An **operation** (internal node with an operator type and two child expressions).

> **Prompt idea:** *"Help me define a C++ data structure for an expression tree. A node is either an integer literal or a binary operation (Sum, Mult, Div, Exponent) with two children."*

### Step 2 — Evaluate the Tree

Implement a function that takes an expression tree and returns the integer result by recursively evaluating it.

> **Prompt idea:** *"Write a function that evaluates this expression tree recursively. Sum adds, Mult multiplies, Div does integer division, and Exponent raises to a power."*

### Step 3 — Format the Tree as a String

Implement a function that converts the tree into a fully parenthesized infix string. Numbers just become their string representation. Operations become `(left OP right)`.

> **Prompt idea:** *"Write a function that converts the expression tree to an infix string like ((3 ^ 2) + (-2)). Every operation should be wrapped in parentheses."*

### Step 4 — Parse the Input

This is the most involved step. You need to turn a string like `Sum(Exponent(3, 2), -2)` into the expression tree from Step 1.

Key parsing challenges:
- Recognize the function name (`Sum`, `Mult`, `Div`, `Exponent`)
- Handle the opening `(`, comma `,`, and closing `)`
- Recursively parse nested expressions
- Handle negative numbers

> **Prompt idea:** *"Write a recursive descent parser in C++ that takes a string like `Sum(Exponent(3, 2), -2)` and builds the expression tree I defined earlier."*

### Step 5 — Wire It All Together

Read a line from stdin, parse it, evaluate it, format it, and print the result.

> **Prompt idea:** *"Write the main function that reads a line from stdin, parses it into the expression tree, evaluates it, formats it, and prints: formatted_expression = result"*

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
