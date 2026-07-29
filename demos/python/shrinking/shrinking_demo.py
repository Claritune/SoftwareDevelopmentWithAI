"""
Property-Based Testing: Shrinking Demo
=======================================

When Hypothesis finds a failing input, it doesn't stop — it SHRINKS
it, systematically simplifying the input until it finds the MINIMAL
case that still fails. This demo shows shrinking in action.
"""

import string

from hypothesis import HealthCheck, Phase, Verbosity, given, seed, settings
from hypothesis import strategies as st

from process_batch import process_batch


def fmt(lst, max_show=6):
    if len(lst) <= max_show:
        return str(lst)
    shown = ", ".join(str(x) for x in lst[:max_show])
    return f"[{shown}, ...] ({len(lst)} items)"


def show_system_under_test():
    print("=" * 60)
    print("  The Problem: Normalizing Sensor Readings")
    print("=" * 60)
    print("""
  We have a batch processing pipeline that receives sensor
  readings as integers. Before storing them, we need to
  normalize values to the range [0, 100].

  Requirements:
    1. Empty input        -> return []
    2. Single value > 100 -> clamp to 100
    3. All values <= 100  -> pass through unchanged
    4. Any value > 100    -> apply min-max normalization:
         normalized = (x - min) / (max - min) * 100
       This maps the smallest value to 0 and the largest to 100.

  Example: sensor readings [200, 300, 400]
    min=200, max=400, span=200
    200 -> (200-200)/200*100 =   0
    300 -> (300-200)/200*100 =  50
    400 -> (400-200)/200*100 = 100
    Result: [0, 50, 100]
""")

    input("  Press Enter to see the implementation...")

    print("\n  Here's what the developer wrote:\n")
    print("  def process_batch(items: list[int]) -> list[int]:")
    print("      if not items:")
    print("          return []")
    print("      if len(items) == 1:")
    print("          return [min(items[0], 100)]")
    print("      max_val = max(items)")
    print("      if max_val > 100:")
    print("          min_val = min(items)")
    print("          span = max_val - min_val")
    print("          return [int((x - min_val) / span * 100) for x in items]")
    print("      return items")

    examples = [
        ([200, 300, 400], "normalizes to [0, 50, 100]"),
        ([0, 50, 100], "already in range, passes through"),
        ([150], "single element, clamped to 100"),
        ([], "empty list, returns []"),
    ]
    print("\n  Quick smoke test — all good:")
    for inp, desc in examples:
        result = process_batch(inp)
        print(f"    {str(inp):<20s} -> {str(result):<20s}  ({desc})")

    print("\n  Looks solid. But can it handle ANY valid input?")


# ─────────────────────────────────────────────────────────
# Demo 1: Manual shrinking — the detective work
# ─────────────────────────────────────────────────────────

def demo_manual_shrinking():
    print("\n" + "=" * 60)
    print("  DEMO 1: Manual Shrinking (the hard way)")
    print("=" * 60)

    failing_input = [347] * 50

    print(f"\n  Imagine a fuzzer hands you this failure:")
    print(f"    process_batch({fmt(failing_input)})")
    try:
        process_batch(failing_input)
    except ZeroDivisionError:
        print("    -> ZeroDivisionError!")

    print("\n  Now you have to figure out WHY. Where do you even start?")

    # Phase A: is it the length?
    print("\n  Step 1: Is it the length?")
    for size in [50, 25, 10, 5, 2, 1]:
        test = [347] * size
        try:
            process_batch(test)
            print(f"    {fmt(test):>35s}  ->  passes")
        except ZeroDivisionError:
            print(f"    {fmt(test):>35s}  ->  ZeroDivisionError")

    print("  Hmm, [347] alone passes. Needs length >= 2.")

    # Phase B: is it the value?
    print("\n  Step 2: Is it the specific value 347?")
    for val in [200, 150, 101, 100]:
        test = [val] * 3
        try:
            process_batch(test)
            print(f"    {str(test):>20s}  ->  passes: {process_batch(test)}")
        except ZeroDivisionError:
            print(f"    {str(test):>20s}  ->  ZeroDivisionError")

    print("  Interesting — [100, 100, 100] passes but [101, 101, 101] fails.")

    # Phase C: does equality matter?
    print("\n  Step 3: Wait... does it matter that they're EQUAL?")
    cases = [
        ([101, 102, 103], "distinct values > 100"),
        ([200, 300], "distinct values > 100"),
        ([101, 101], "EQUAL values > 100"),
    ]
    for test, desc in cases:
        try:
            result = process_batch(test)
            print(f"    {str(test):<20s}  ->  passes: {result}  ({desc})")
        except ZeroDivisionError:
            print(f"    {str(test):<20s}  ->  ZeroDivisionError!  ({desc})")

    print("""
  After three rounds of guessing we found it:
    equal values > 100 in a multi-element list -> division by zero.
  That took effort, and we had to GUESS which dimensions to vary.
  Hypothesis does this automatically.""")


# ─────────────────────────────────────────────────────────
# Demo 2: Hypothesis shrinks it for you
# ─────────────────────────────────────────────────────────

def demo_hypothesis_shrinking():
    print("\n" + "=" * 60)
    print("  DEMO 2: Hypothesis Shrinking (the smart way)")
    print("=" * 60)

    attempts = []

    @seed(30)
    @given(
        st.lists(
            st.integers(min_value=0, max_value=10000),
            min_size=2,
            max_size=200,
        )
    )
    @settings(
        max_examples=500,
        database=None,
        suppress_health_check=[HealthCheck.too_slow],
        verbosity=Verbosity.quiet,
        phases=[Phase.generate, Phase.shrink],
    )
    def prop_never_crashes(items):
        attempts.append(list(items))
        process_batch(items)

    print("\n  Running: process_batch should handle ANY list without crashing")
    print("  Strategy: lists of 2-200 integers in [0..10000]\n")

    try:
        prop_never_crashes()
        print("  No failure found.")
        return
    except Exception:
        pass

    # Classify attempts
    failing = []
    for a in attempts:
        try:
            process_batch(a)
        except ZeroDivisionError:
            failing.append(a)

    print(f"  Total attempts: {len(attempts)}")
    print(f"  Failing cases:  {len(failing)}")

    # Show shrinking journey (skip already-seen len/value combos)
    print("\n  Shrinking journey:\n")
    seen = set()
    for i, case in enumerate(failing):
        key = (len(case), case[0] if case else None)
        if key in seen:
            continue
        seen.add(key)
        label = "INITIAL" if i == 0 else "shrunk "
        print(f"    {label}  len={len(case)}  {fmt(case)}")

    final = failing[-1]
    print(f"\n  Minimal counterexample: {final}")

    # Show the boundary
    print("\n  Why is this minimal? Every simpler variant passes:\n")
    neighbors = [
        ([101], "single element (len=1 path)"),
        ([101, 102], "two DISTINCT values > 100"),
        ([99, 99], "two equal values <= 100"),
        ([100, 100], "two equal values at boundary"),
    ]
    for case, reason in neighbors:
        result = process_batch(case)
        print(f"    {str(case):<16s} -> {str(result):<16s}  ({reason})")

    print(f"\n    {str(final):<16s} -> ZeroDivisionError!  (equal values > 100)")

    print("""
  Hypothesis discovered the bug requires exactly:
    1. More than one element   (len > 1)
    2. All elements equal      (max == min, so span == 0)
    3. Value > 100             (triggers the normalization branch)
  It shrunk to [101, 101] — the smallest input satisfying all three.""")


# ─────────────────────────────────────────────────────────
# Demo 3: Shrinking works on all types
# ─────────────────────────────────────────────────────────

def demo_shrinking_other_types():
    print("\n" + "=" * 60)
    print("  DEMO 3: Shrinking Works on All Types")
    print("=" * 60)

    print('\n  Property: "no string should contain the letter x"')
    print("  (A toy property, but it shows shrinking mechanics clearly.)\n")

    attempts = []

    @seed(30)
    @given(st.text(
        alphabet=string.ascii_letters + string.digits,
        min_size=1,
        max_size=20,
    ))
    @settings(
        max_examples=200,
        database=None,
        suppress_health_check=[HealthCheck.too_slow],
        verbosity=Verbosity.quiet,
        phases=[Phase.generate, Phase.shrink],
    )
    def prop_no_x(text):
        attempts.append(text)
        assert "x" not in text

    try:
        prop_no_x()
        print("  No failure found.")
        return
    except Exception:
        pass

    failing = [a for a in attempts if "x" in a]

    # Show journey (deduplicate consecutive identical entries)
    print("  Shrinking journey:\n")
    prev = None
    for i, case in enumerate(failing):
        if case == prev:
            continue
        prev = case
        label = "INITIAL" if i == 0 else "shrunk "
        print(f"    {label}  len={len(case):>2d}  {repr(case)}")

    print(f"""
  Hypothesis stripped characters one by one, keeping the 'x'
  that causes failure, until only 'x' remained.

  Shrinking strategies by type:
    integers   shrink toward 0 (or the smallest boundary value)
    lists      remove elements first, then shrink remaining values
    strings    remove characters first, then simplify remaining ones
    dicts      remove keys first, then shrink remaining values""")


# ─────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    show_system_under_test()

    input("\n  Press Enter for Demo 1: Manual Shrinking...")
    demo_manual_shrinking()

    input("\n  Press Enter for Demo 2: Hypothesis Shrinking...")
    demo_hypothesis_shrinking()

    input("\n  Press Enter for Demo 3: Shrinking on Other Types...")
    demo_shrinking_other_types()

    print("\n" + "=" * 60)
    print("  KEY TAKEAWAY")
    print("=" * 60)
    print("""
  Without shrinking: "Failed on [347, 347, 347, 347, ...] (50 items)"
                     Good luck figuring out WHY.

  With shrinking:    "Failed on [101, 101]"
                     The bug is immediately obvious.

  Shrinking transforms NOISE into SIGNAL.
""")
