"""
Property-Based Testing: Shrinking Demo
=======================================

Demonstrates HOW shrinking works in Hypothesis:
  When a property fails on a complex input (e.g., a 200-element list),
  Hypothesis automatically simplifies it to the MINIMAL reproducing case.

We'll test a deliberately buggy function and watch Hypothesis:
  1. Find an initial failing case (often large and noisy)
  2. Shrink it down to the smallest input that still triggers the bug
  3. Report the minimal counterexample

The Bug:
  Our `process_batch` function has a subtle edge case — it breaks
  when any element exceeds a threshold AND the list has more than
  one element. Hypothesis will discover this and shrink the 200-element
  input down to a tiny 2-element list.
"""

from hypothesis import given, settings, HealthCheck, Phase, Verbosity
from hypothesis import strategies as st
import traceback


# ─────────────────────────────────────────────────────────
# The system under test (with a deliberate bug)
# ─────────────────────────────────────────────────────────

def process_batch(items: list[int]) -> list[int]:
    """
    Normalize a batch of integers to the range [0, 100].
    
    BUG: When any value > 100 appears in a multi-element list,
    the function divides by zero due to a flawed normalization.
    """
    if not items:
        return []

    if len(items) == 1:
        return [min(items[0], 100)]

    max_val = max(items)

    # Bug: if max_val > 100, we try to scale — but when all
    # elements equal max_val, (max_val - min_val) == 0 → ZeroDivisionError
    if max_val > 100:
        min_val = min(items)
        span = max_val - min_val  # 💥 Zero when all elements are equal!
        return [int((x - min_val) / span * 100) for x in items]

    return items


# ─────────────────────────────────────────────────────────
# Demo 1: Manual shrinking (what you'd do without PBT)
# ─────────────────────────────────────────────────────────

def demo_manual_shrinking():
    """Show the tedious manual process of narrowing down a failure."""
    
    print("=" * 65)
    print("DEMO 1: Manual Shrinking (the hard way)")
    print("=" * 65)

    # Imagine your CI found this failure on a 200-element list:
    original_failing = [101] * 200

    print(f"\n❌ Original failure: list of {len(original_failing)} elements")
    print(f"   First 10: {original_failing[:10]}...")
    try:
        process_batch(original_failing)
    except ZeroDivisionError:
        print("   → ZeroDivisionError!")

    # Manual bisection: try cutting in half
    print("\n🔍 Manual bisection attempt:")
    for size in [100, 50, 10, 5, 3, 2, 1]:
        test = [101] * size
        try:
            process_batch(test)
            print(f"   {str(test):>30s}  →  ✅ passes")
        except ZeroDivisionError:
            print(f"   {str(test):>30s}  →  ❌ fails")

    print("\n📌 After tedious manual work: minimal case is [101, 101]")
    print("   But this took effort, and we had to GUESS the structure.")


# ─────────────────────────────────────────────────────────
# Demo 2: Hypothesis does it automatically
# ─────────────────────────────────────────────────────────

def demo_hypothesis_shrinking():
    """Hypothesis finds AND shrinks the counterexample automatically."""
    
    print("\n" + "=" * 65)
    print("DEMO 2: Hypothesis Shrinking (the smart way)")
    print("=" * 65)

    # Track every attempt so we can show the shrinking journey
    attempts = []

    @given(
        st.lists(
            st.integers(min_value=0, max_value=500),
            min_size=2,
            max_size=200,
        )
    )
    @settings(
        max_examples=500,
        database=None,                       # Don't cache across runs
        suppress_health_check=[HealthCheck.too_slow],
        verbosity=Verbosity.quiet,
        phases=[Phase.generate, Phase.shrink], # Skip replay of old examples
    )
    def prop_process_batch_never_crashes(items):
        """Property: process_batch should handle ANY valid input without crashing."""
        attempts.append(list(items))
        process_batch(items)  # Should never raise

    # Run it and catch the expected failure
    print("\n🔬 Running Hypothesis with lists of 2-200 integers [0..500]...\n")
    
    try:
        prop_process_batch_never_crashes()
        print("   No failure found (unlikely with this bug!)")
        return
    except Exception as e:
        pass  # Expected — we'll analyze the shrinking below

    # ── Analyze the shrinking journey ──
    
    # Find where failures start (the shrinking phase)
    failing = []
    passing_during_shrink = []

    for a in attempts:
        try:
            process_batch(a)
            passing_during_shrink.append(a)
        except ZeroDivisionError:
            failing.append(a)

    first_failure = failing[0] if failing else None
    final_failure = failing[-1] if failing else None

    print(f"   Total attempts:  {len(attempts)}")
    print(f"   Failing cases:   {len(failing)}")
    print(f"   Passing (shrink): {len(passing_during_shrink)}")

    # Show the shrinking journey
    print("\n📉 Shrinking journey (failing cases, largest → smallest):\n")
    
    # Sort failing cases by size to show the progression
    seen_sizes = set()
    milestones = []
    for case in failing:
        size = len(case)
        if size not in seen_sizes:
            seen_sizes.add(size)
            milestones.append(case)
    
    milestones.sort(key=len, reverse=True)
    
    for i, case in enumerate(milestones[:8]):
        label = "INITIAL" if i == 0 else f"shrunk "
        if len(case) <= 10:
            print(f"   {label}  len={len(case):>3d}  →  {case}")
        else:
            print(f"   {label}  len={len(case):>3d}  →  {case[:5]}...{case[-3:]}")

    print(f"\n✨ Hypothesis minimal counterexample: {final_failure}")
    print(f"   Length: {len(final_failure)}")

    # Show the boundary: smallest passing vs smallest failing
    print("\n" + "─" * 65)
    print("🔎 THE BOUNDARY (minimal fail vs. nearby pass):\n")
    print(f"   ❌ Minimal FAILING case:  {final_failure}")
    try:
        process_batch(final_failure)
    except ZeroDivisionError as e:
        print(f"      → ZeroDivisionError (span=0, all elements equal & >100)")

    # Demonstrate what passes nearby
    nearby_passes = [
        ([101],          "single element >100 (len=1 path)"),
        ([101, 102],     "two distinct elements >100"),
        ([99, 99],       "two equal elements ≤100"),
        ([0, 101],       "mixed: one ≤100, one >100, distinct"),
    ]

    print()
    for case, reason in nearby_passes:
        try:
            result = process_batch(case)
            print(f"   ✅ Passing neighbor:      {str(case):<16s} → {result}  ({reason})")
        except Exception:
            print(f"   ❌ Also fails:            {str(case):<16s}  ({reason})")

    print()
    print("💡 INSIGHT: Hypothesis discovered the bug requires exactly:")
    print("     1. More than one element  (len > 1)")
    print("     2. All elements equal     (max == min → span == 0)")  
    print("     3. Value > 100            (triggers the scaling branch)")
    print("   It shrunk values toward 101 (smallest int > 100)")
    print("   and list size toward 2 (smallest multi-element list).")


# ─────────────────────────────────────────────────────────
# Demo 3: Show shrinking strategies on different types
# ─────────────────────────────────────────────────────────

def demo_shrinking_strategies():
    """Show how Hypothesis shrinks different data types."""
    
    print("\n" + "=" * 65)
    print("DEMO 3: How Hypothesis Shrinks Different Types")
    print("=" * 65)

    examples = {
        "integers":   "723  →  shrinks toward 0 (or smallest boundary)",
        "strings":    "'xK!9zQ'  →  shrinks toward '' then 'a','aa',...",
        "lists":      "[5,3,99,2,7]  →  shrinks by removing elements, then shrinking values",
        "tuples":     "(42, 'hello')  →  each component shrinks independently",
        "floats":     "3.14159  →  shrinks toward simpler floats (0.0, 1.0, etc.)",
        "dicts":      "{'a':1,'b':2,'c':3}  →  removes keys, then shrinks values",
    }

    print("\nHypothesis shrinking heuristics by type:\n")
    for dtype, description in examples.items():
        print(f"  {dtype:>10s}:  {description}")

    print("\nShrinking strategies used:")
    print("  • Delete elements (lists, dicts, strings → try shorter)")
    print("  • Reduce values (integers → toward 0, floats → simpler)")
    print("  • Simplify characters (strings → toward 'a')")
    print("  • Binary search (try half the elements, quarter, etc.)")
    print("  • Redistribute (swap complex combos for simpler ones)")
    print("  • Each step must STILL FAIL — passing attempts are discarded")


# ─────────────────────────────────────────────────────────
# Run all demos
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║     Property-Based Testing: Shrinking Demonstration         ║")
    print("╠═══════════════════════════════════════════════════════════════╣")
    print("║  When Hypothesis finds a failing input, it doesn't stop.    ║")
    print("║  It SHRINKS it — systematically simplifying the input       ║")
    print("║  until it finds the MINIMAL case that still fails.          ║")
    print("╚═══════════════════════════════════════════════════════════════╝")

    demo_manual_shrinking()
    demo_hypothesis_shrinking()
    demo_shrinking_strategies()

    print("\n" + "=" * 65)
    print("KEY TAKEAWAY")
    print("=" * 65)
    print("""
  Without shrinking:  "Your test failed on [101, 101, 101, ... 200 items]"
                      → Good luck figuring out WHY.

  With shrinking:     "Your test failed on [101, 101]"
                      → The bug is obvious: equal values > 100 in a
                        multi-element list cause division by zero.

  Shrinking transforms NOISE into SIGNAL.
""")
