"""
Properties derived from the SPEC (not from the code).

This file is the agent's artifact: the "logic" part. It states what
correct means and where bugs are likely to hide. Hypothesis does the
searching.

Spec:
  1. Empty input        -> []
  2. Single value > 100 -> clamp to 100
  3. All values <= 100  -> pass through unchanged
  4. Any value > 100    -> min-max normalize to [0, 100]:
       (x - min) / (max - min) * 100, as an integer
"""

from fractions import Fraction

from hypothesis import strategies as st

# ── Properties ───────────────────────────────────────────


def never_crashes(impl, items):
    """Any list of integers is valid input."""
    impl(items)


def output_in_range(impl, items):
    """The function's whole purpose: results land in [0, 100]."""
    try:
        result = impl(items)
    except ZeroDivisionError:
        return  # crashes are never_crashes' job; check one thing at a time
    assert all(0 <= v <= 100 for v in result), result


def matches_exact_formula(impl, items):
    """Normalized values equal the formula computed with exact fractions."""
    if len(items) < 2 or max(items) <= 100 or max(items) == min(items):
        return  # rule 4 only; span == 0 is undefined by the formula
    lo, span = min(items), max(items) - min(items)
    expected = [int(Fraction(x - lo, span) * 100) for x in items]
    assert impl(items) == expected, f"got {impl(items)}, expected {expected}"


# ── Strategies (where to search) ─────────────────────────

any_batch = st.lists(st.integers(min_value=-10_000, max_value=10_000), max_size=200)


@st.composite
def whole_percent_batches(draw):
    """Batches whose exact normalized values are whole numbers.

    Float division is most fragile exactly here: 29/100*100 must be 29.0,
    and if it lands at 28.999... then int() truncates it to 28. Random
    lists almost never hit whole percentages; this strategy builds them
    on purpose.
    """
    lo = draw(st.integers(min_value=1, max_value=1000))
    step = draw(st.integers(min_value=1, max_value=100))
    percents = draw(st.lists(st.integers(min_value=0, max_value=100), min_size=1, max_size=8))
    return [lo] + [lo + p * step for p in percents] + [lo + 100 * step]
