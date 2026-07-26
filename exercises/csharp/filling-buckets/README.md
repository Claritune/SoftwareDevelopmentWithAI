# Exercise: Filling Buckets — Algorithm & Testing (C#)

## Overview

Implement a recursive algorithm that determines whether a large bucket can be filled exactly using combinations of smaller buckets, then write comprehensive tests to verify it.

**You are expected to use an AI coding agent (GitHub Copilot, Claude Code, Cursor, or similar) throughout this exercise.** The goal is to practice collaborating with an AI assistant on algorithm design and test writing — not to write every line by hand.

---

## The Problem

Given a big bucket of size `N` and a set of smaller buckets with known sizes, determine whether the big bucket can be filled exactly by using any combination of the smaller buckets (each can be used zero or more times).

If a valid combination exists, return **which buckets were used and how many times each**.

### Examples

| Big Bucket | Small Buckets | Can Fill? | Plan |
|---|---|---|---|
| `12` | `[3, 5]` | Yes | `{3: 4}` (four 3s) |
| `12` | `[5, 7]` | Yes | `{5: 1, 7: 1}` (one 5 + one 7) |
| `11` | `[3, 5]` | Yes | `{3: 2, 5: 1}` (two 3s + one 5) |
| `7` | `[3, 5]` | No | — |
| `0` | `[3, 5]` | Yes | `{}` (empty — nothing needed) |
| `10` | `[]` | No | — |
| `12` | `[12]` | Yes | `{12: 1}` |
| `100` | `[3, 7, 11]` | Yes | (multiple valid plans) |

---

## Requirements

1. **Implement** a function `CanFill(int bigBucket, int[] smallBuckets)` that returns:
   - Whether the big bucket can be filled exactly
   - A fill plan: a dictionary mapping each used bucket size to the number of times it was used
2. **Handle edge cases:** empty bucket lists, zero-size big bucket, duplicate bucket sizes, zero-size small buckets
3. **Write tests** that cover normal cases, edge cases, and boundary conditions

---

## Getting Started

### Prerequisites

- .NET SDK 8.0 or later ([download](https://dotnet.microsoft.com/download))
- An AI coding assistant set up in your editor or terminal

### Create the Project

```bash
cd filling-buckets
dotnet new console -n FillingBuckets
cd FillingBuckets
```

### Suggested Project Structure

```
FillingBuckets/
  Program.cs              <-- entry point with demo cases
  BucketFiller.cs         <-- algorithm implementation
  FillingBuckets.csproj
```

For tests, create a separate test project:

```bash
cd ..
dotnet new xunit -n FillingBuckets.Tests
cd FillingBuckets.Tests
dotnet add reference ../FillingBuckets/FillingBuckets.csproj
```

---

## Step-by-Step Guide

### Step 1 — Define the Return Type

Design a type to represent the result of a fill attempt. C# offers several good options:

- A `record` with a `bool Success` and a `Dictionary<int, int> Plan`
- A tuple `(bool CanFill, Dictionary<int, int> Plan)`
- A custom result type with pattern matching support

> **Prompt idea:** *"Help me define a C# result type for a bucket-filling algorithm. It should indicate success/failure and include a dictionary mapping bucket sizes to usage counts. What's the most idiomatic approach — a record, a tuple, or a custom type?"*

### Step 2 — Implement the Algorithm

The algorithm works by trying each bucket size, exploring how many times it can be used, and recursing on the remainder. Key ideas:

- Sort and deduplicate the bucket list
- For each bucket size, try different usage counts (from max down to 0)
- If the remainder is exactly divisible by the current bucket, return immediately
- Recurse on the next bucket size for the remaining volume

> **Prompt idea:** *"Implement a recursive bucket-filling algorithm in C#. Given a big bucket size and a sorted array of smaller bucket sizes, determine if the big bucket can be filled exactly. Use backtracking — try each bucket size from the most uses down to zero, recurse on the remainder with the next bucket size."*

### Step 3 — Handle Edge Cases

Make sure your implementation correctly handles:
- Big bucket size of 0 (should succeed with an empty plan)
- Empty small buckets list (should fail)
- Duplicate bucket sizes in the input
- Zero-size small buckets in the list
- Single bucket that divides evenly

### Step 4 — Write Tests

This is the core of the exercise. Write tests that cover:

**Basic cases:**
- Single bucket that divides evenly
- Two buckets where only one is needed
- Two buckets where both are needed
- Impossible combinations

**Edge cases:**
- Big bucket is 0
- Empty small bucket list
- Bucket sizes with duplicates
- Single bucket that doesn't divide evenly

**Validation of the plan:**
- The returned plan sums to exactly the big bucket size
- The plan only contains bucket sizes from the input
- All usage counts are positive

**Property-based thinking:**
- For any successful result, `plan.Sum(kv => kv.Key * kv.Value)` must equal the big bucket size
- An unsuccessful result must have an empty plan

> **Prompt idea:** *"Write xUnit tests for the bucket-filling algorithm. Cover basic success/failure, edge cases, and verify that successful plans always sum to the target size. Use [Theory] with [InlineData] for parameterized tests where possible."*

### Step 5 — Run and Verify

```bash
cd FillingBuckets.Tests
dotnet test
```

---

## Tips for Working with the AI Assistant

1. **Implement first, test second.** Get the algorithm working with a few manual checks in `Program.cs`, then move to formal tests.
2. **Ask the AI to explain the recursion.** If backtracking isn't intuitive, have the AI walk through a specific example step by step.
3. **Challenge the AI's tests.** Ask: "What edge cases are we missing?" or "Can you think of an input that would break this?"
4. **Verify plans, not just booleans.** A test that only checks `CanFill == true` without verifying the plan is incomplete.

---

## Bonus Challenges

- **Performance:** Handle large bucket sizes (e.g., `CanFill(1_000_000, [3, 7, 11])`) — add memoization or convert to dynamic programming.
- **All solutions:** Modify the algorithm to return all valid fill plans, not just the first one found.
- **LINQ approach:** Rewrite using a functional style with LINQ and immutable collections.
- **Span-based:** Use `ReadOnlySpan<int>` instead of arrays for zero-allocation slicing.
