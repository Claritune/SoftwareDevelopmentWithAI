# Property-Based Testing with an AI Agent

A short demo of how an AI agent and [Hypothesis](https://hypothesis.readthedocs.io/)
split the work of finding bugs:

| Role | Does | Cost |
|---|---|---|
| **AGENT** (logic) | Turns the spec into properties, decides *where* to search, diagnoses failures, writes the fix | Tokens, spent on judgment |
| **HYPOTHESIS** (search) | Runs thousands of inputs, shrinks each failure to a minimal case | CPU time, 0 tokens |
| **HUMAN** (decision) | Resolves what the spec itself leaves ambiguous | A minute of thought |

An agent can often spot an obvious bug just by reading the code. Asking it to
*search* for failing inputs by itself, though, means guessing an input, running
it, reading the output and guessing again. Every round costs tokens and makes
the context longer. Moving the search into Hypothesis means the agent writes a
few properties once and reads a few short lines of output.

## The system under test

`process_batch(items: list[int]) -> list[int]` normalizes sensor readings to `[0, 100]`.

Spec:

1. Empty input → `[]`
2. Single value > 100 → clamp to 100
3. All values ≤ 100 → pass through unchanged
4. Any value > 100 → min-max normalize: `(x - min) / (max - min) * 100`, as an integer

`process_batch.py` passes the obvious smoke tests (`[200, 300, 400] → [0, 50, 100]`),
but it has three different kinds of bug:

| Bug | Minimal input | Kind |
|---|---|---|
| Division by zero | `[101, 101]` | Coding slip: easy to spot by reading |
| Float truncation | `[1, 30, 101] → [0, 28, 100]`, expected 29 | Hard to spot by reading: `29/100*100 == 28.999999999999996` |
| Negative output | `[-1] → [-1]` | Spec contradiction: rule 3 vs. the `[0, 100]` goal |

## The demo, step by step

```
python shrinking_demo.py          # pauses between steps
python shrinking_demo.py --auto   # runs straight through
```

1. **AGENT: spec → properties.** The question is "what must *always* be true?",
   not "find the bug". It produces three properties: `never_crashes`,
   `output_in_range`, and `matches_exact_formula`, which compares against exact
   `Fraction` arithmetic.
2. **HYPOTHESIS: broad search** over lists of up to 200 integers in ±10,000.
   - `never_crashes` fails and shrinks `[976, 976]` to `[101, 101]`.
   - `output_in_range` fails and shrinks `[-567]` to `[-1]`.
   - `matches_exact_formula` **passes** 1,000 inputs, even though the bug is there.
3. **AGENT: diagnosis.** It explains the crash and recognizes that `[-1]` is not
   a coding slip but a contradiction in the spec.
   **HUMAN: decision.** The `[0, 100]` range wins: normalize whenever any value
   falls outside it.
   **AGENT: "a PASS is not proof".** The float bug only appears when the exact
   answer is a whole number, and random lists almost never produce one. The agent
   writes a targeted strategy, `whole_percent_batches`, that builds such batches
   on purpose.
4. **HYPOTHESIS: targeted search.** It fails within about 60 inputs and shrinks to `[1, 30, 101]`.
5. **AGENT: fix.** It switches to integer arithmetic, guards equal values, and
   implements the human's decision (`process_batch_fixed.py`).
6. **HYPOTHESIS: verify.** Each property runs 5,000 inputs against the fixed
   version and all of them pass. The shrunk counterexamples are pinned as
   `@example(...)` regression tests.

Step 3 is the point of the demo. Hypothesis can't know where bugs hide, and the
agent can't search thousands of inputs cheaply. When the agent points the search
at the right input space, a bug that broad search missed is found in milliseconds.

## How Hypothesis works (the short version)

- A **strategy** (`st.lists(st.integers())`) describes the input space; `@given`
  turns a test into a search over it.
- Generation favors nasty values: 0, boundaries, duplicates, empty lists.
- **Shrinking** works on the recorded sequence of random choices behind each
  input, not on the values themselves. So it works for any strategy, and shrunk
  inputs still satisfy the strategy's constraints.
- **`@example(...)`** is not documentation: it is a guaranteed test case that
  runs on every run before generation, is never shrunk, and lives in version
  control. Use it to pin regressions.
- **`assume(...)`** throws away an input. Use it to narrow the input space, not
  to skip known bugs.

## Files

| File | Role |
|---|---|
| `process_batch.py` | Buggy implementation (kept as-is so the demo can be rerun) |
| `properties.py` | Spec, properties, and strategies: the agent's artifact |
| `process_batch_fixed.py` | Fixed implementation, including the human's spec decision |
| `shrinking_demo.py` | The scripted walkthrough |
| `tests/test_process_batch.py` | Properties plus `@example` pins, run against the fixed version |

## Setup

```
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python shrinking_demo.py
pytest
```

The demo uses `@seed(1)` and `database=None`, so every run follows the same
search and shrink path.

## Note

The agent's steps are scripted so the demo is reproducible. In a live session,
steps 1, 3 and 5 can be done in Claude Code by giving it the spec and
`process_batch.py`.
