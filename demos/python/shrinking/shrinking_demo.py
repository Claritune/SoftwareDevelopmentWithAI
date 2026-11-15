"""
Property-Based Testing with an AI Agent
=======================================

Three roles, kept strictly apart:

  AGENT       logic:    spec -> properties, where to search, diagnosis, fix
  HYPOTHESIS  search:   runs thousands of inputs and shrinks failures (0 tokens)
  HUMAN       decision: resolves what the spec itself leaves ambiguous

Run:  python shrinking_demo.py          (pauses between steps)
      python shrinking_demo.py --auto   (no pauses)
"""

import ast
import inspect
import sys
import time

from hypothesis import HealthCheck, Phase, given, seed, settings

import process_batch
import process_batch_fixed
import properties as P
from process_batch import process_batch as buggy
from process_batch_fixed import process_batch as fixed

AUTO = "--auto" in sys.argv
COLOR = sys.stdout.isatty()

ROLES = {
    "AGENT": ("35", "logic"),
    "HYPOTHESIS": ("36", "search · 0 tokens"),
    "HUMAN": ("33", "decision"),
}

totals = {"inputs": 0, "seconds": 0.0}


def banner(role, title):
    code, kind = ROLES[role]
    text = f" {role} · {kind} ── {title} "
    line = f"\n──{text}{'─' * max(0, 64 - len(text))}"
    print(f"\033[1;{code}m{line}\033[0m" if COLOR else line)


def pause(prompt="  [Enter] "):
    if not AUTO:
        input(prompt)


def fmt(lst, max_show=6):
    if len(lst) <= max_show:
        return str(lst)
    return f"[{', '.join(map(str, lst[:max_show]))}, ...] ({len(lst)} items)"


def show_source(module, name, docstring=True):
    """Print a function's source, read via ast (works for @st.composite too)."""
    source = inspect.getsource(module)
    node = next(n for n in ast.walk(ast.parse(source)) if getattr(n, "name", None) == name)
    lines = source.splitlines()[node.lineno - 1 - len(node.decorator_list) : node.end_lineno]
    body = node.body[0]
    if not docstring and isinstance(body, ast.Expr) and isinstance(body.value, ast.Constant):
        del lines[body.lineno - node.lineno + len(node.decorator_list) : body.end_lineno - node.lineno + len(node.decorator_list) + 1]
    for line in lines:
        print(f"    {line}")


def search(check, impl, strategy, max_examples=1000, label=None):
    """Let Hypothesis hunt for a counterexample to one property."""
    calls, failures = [0], []

    @seed(1)
    @settings(
        max_examples=max_examples,
        database=None,
        report_multiple_bugs=False,
        suppress_health_check=[HealthCheck.too_slow],
        phases=[Phase.explicit, Phase.generate, Phase.shrink],
    )
    @given(strategy)
    def run(items):
        calls[0] += 1
        try:
            check(impl, items)
        except Exception as e:
            failures.append((list(items), e))
            raise

    start = time.perf_counter()
    try:
        run()
    except Exception:
        pass
    seconds = time.perf_counter() - start
    totals["inputs"] += calls[0]
    totals["seconds"] += seconds

    name = label or check.__name__
    if not failures:
        print(f"    {name:<24s} PASS   {calls[0]:>6,} inputs  {seconds:5.2f}s")
        return None
    first, (minimal, error) = failures[0][0], failures[-1]
    print(f"    {name:<24s} FAIL   {calls[0]:>6,} inputs  {seconds:5.2f}s")
    print(f"        first failure:  {fmt(first)}")
    print(f"        shrunk to:      {minimal}   -> {type(error).__name__}")
    return minimal


# ─────────────────────────────────────────────────────────


def step_0_problem():
    print("=" * 66)
    print("  Normalizing sensor readings to [0, 100]")
    print("=" * 66)
    print(P.__doc__.split("Spec:")[1].rstrip())
    print("\n  Implementation (process_batch.py):\n")
    show_source(process_batch, "process_batch", docstring=False)


def step_1_properties():
    banner("AGENT", "turn the spec into properties")
    print("  Not 'find the bug' — just: what must ALWAYS be true?\n")
    for prop in (P.never_crashes, P.output_in_range, P.matches_exact_formula):
        show_source(P, prop.__name__)
        print()


def step_2_search():
    banner("HYPOTHESIS", "search any list of 0..200 ints in ±10,000")
    found = {}
    for prop in (P.never_crashes, P.output_in_range, P.matches_exact_formula):
        found[prop.__name__] = search(prop, buggy, P.any_batch)
    return found


def step_3_diagnose(found):
    banner("AGENT", "read 3 short lines, not 3,000 inputs")
    print(f"""
  {found['never_crashes']} -> crash.
    All values equal and > 100: span = max - min = 0, then we divide by it.

  {found['output_in_range']} -> returned [-1], outside [0, 100].
    This is not a coding slip. The spec contradicts itself:
      rule 3 says "values <= 100 pass through unchanged"
      the goal says "output is in [0, 100]"
    Neither the agent nor Hypothesis can decide which rule wins.""")

    banner("HUMAN", "resolve the spec")
    print('  "The [0, 100] range wins: normalize whenever any value is out of it."')

    banner("AGENT", "a PASS is not proof — where else could it break?")
    print("""
  matches_exact_formula passed, but look at the formula: float division,
  then int() truncation. That goes wrong only when the exact answer is a
  WHOLE number and the float lands a hair below it. Random lists almost
  never hit whole percentages — so search there on purpose:
""")
    show_source(P, "whole_percent_batches", docstring=False)


def step_4_targeted_search():
    banner("HYPOTHESIS", "search the space the agent pointed at")
    return search(P.matches_exact_formula, buggy, P.whole_percent_batches())


def step_5_fix(minimal):
    banner("AGENT", "diagnose and fix")
    lo, mid = minimal[0], minimal[1]
    print(f"""
  {minimal} -> {buggy(minimal)}, but ({mid}-{lo})/100*100 is exactly {mid - lo}.
    Python agrees:  {mid - lo}/100*100 = {(mid - lo) / 100 * 100!r}
    int() truncates that to {int((mid - lo) / 100 * 100)}. Fix: integer arithmetic.

  Fixed (process_batch_fixed.py):
""")
    show_source(process_batch_fixed, "process_batch", docstring=False)


def step_6_verify():
    banner("HYPOTHESIS", "verify the fix, harder than before")
    for prop in (P.never_crashes, P.output_in_range, P.matches_exact_formula):
        search(prop, fixed, P.any_batch, max_examples=5000)
    search(
        P.matches_exact_formula, fixed, P.whole_percent_batches(),
        max_examples=5000, label="  ...on whole percents",
    )
    print("\n  Shrunk counterexamples are pinned as @example(...) regressions")
    print("  in tests/test_process_batch.py — they run in CI forever.")


def summary():
    print("\n" + "=" * 66)
    print("  WHO DID WHAT")
    print("=" * 66)
    print(f"""
  AGENT       3 properties, 1 targeted strategy, 3 diagnoses, 1 fix
              -> the parts that need understanding of the spec
  HYPOTHESIS  {totals['inputs']:,} inputs executed and shrunk in {totals['seconds']:.1f}s
              -> the part that needs brute force, at zero token cost
  HUMAN       1 decision the spec could not make
""")


if __name__ == "__main__":
    step_0_problem()
    pause()
    step_1_properties()
    pause()
    found = step_2_search()
    pause()
    step_3_diagnose(found)
    pause()
    minimal = step_4_targeted_search()
    pause()
    step_5_fix(minimal)
    pause()
    step_6_verify()
    summary()
