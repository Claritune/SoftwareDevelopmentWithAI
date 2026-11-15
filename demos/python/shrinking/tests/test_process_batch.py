"""Spec properties for the fixed process_batch, with shrunk counterexamples pinned."""

from hypothesis import example, given

import properties as P
from process_batch_fixed import process_batch


@given(P.any_batch)
@example([101, 101])
def test_never_crashes(items):
    P.never_crashes(process_batch, items)


@given(P.any_batch)
@example([-1])
def test_output_in_range(items):
    P.output_in_range(process_batch, items)


@given(P.any_batch)
def test_matches_exact_formula(items):
    P.matches_exact_formula(process_batch, items)


@given(P.whole_percent_batches())
@example([1, 30, 101])
def test_matches_exact_formula_on_whole_percents(items):
    P.matches_exact_formula(process_batch, items)
