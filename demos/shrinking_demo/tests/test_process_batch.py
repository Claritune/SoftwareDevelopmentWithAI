"""Property-based tests for process_batch."""

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from process_batch import process_batch

integers = st.integers(min_value=-10_000, max_value=10_000)
int_lists = st.lists(integers, max_size=200)


def _avoids_equal_above_100(items: list[int]) -> bool:
    """Skip inputs that trigger division-by-zero in the scaling branch."""
    return len(items) <= 1 or max(items) <= 100 or max(items) != min(items)


@given(st.just([]))
def test_empty_input_returns_empty_list(items):
    assert process_batch(items) == []


@given(int_lists)
def test_single_element_is_clamped_to_at_most_100(items):
    assume(len(items) == 1)
    assert process_batch(items) == [min(items[0], 100)]


@given(st.lists(integers, min_size=2))
def test_multi_element_passes_through_when_max_at_most_100(items):
    assume(max(items) <= 100)
    assert process_batch(items) == items


@given(st.lists(integers, min_size=0, max_size=200))
@settings(max_examples=500)
def test_never_crashes(items):
    """process_batch should handle any integer list without raising.

    This property fails on equal values >100 in multi-element lists,
    shrinking to a minimal counterexample like [101, 101].
    """
    process_batch(items)


@given(st.lists(integers, min_size=0, max_size=200))
def test_preserves_length(items):
    assume(_avoids_equal_above_100(items))
    assert len(process_batch(items)) == len(items)


@given(st.lists(integers, min_size=2))
def test_normalized_output_values_in_range_0_to_100(items):
    assume(max(items) > 100)
    assume(max(items) != min(items))
    result = process_batch(items)
    assert all(0 <= value <= 100 for value in result)


@given(st.lists(integers, min_size=2))
def test_normalization_maps_extremes_to_0_and_100(items):
    assume(max(items) > 100)
    assume(max(items) != min(items))
    result = process_batch(items)
    assert min(result) == 0
    assert max(result) == 100


@given(st.lists(integers, min_size=2))
def test_normalization_preserves_relative_order(items):
    assume(max(items) > 100)
    assume(max(items) != min(items))
    result = process_batch(items)
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i] <= items[j]:
                assert result[i] <= result[j]
            else:
                assert result[i] >= result[j]
