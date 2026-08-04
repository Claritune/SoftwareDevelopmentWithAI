"""
Fill the bucket - find and fix the bugs
Goal: fill the big bucket with minimum fill operations
a fill operation = using a small bucket of any size
example: using 7 twice + 2 three times = 5 operations
@Author: Amir Kirsh
"""

from typing import List, Dict, Tuple

FillPlan = Dict[int, int]
FillResult = Tuple[bool, FillPlan]


def _can_fill_recursive(big_bucket: int, small_buckets: List[int], index: int) -> FillResult:
    if big_bucket < small_buckets[-1]:
        return False, {}
    curr = small_buckets[index]
    if big_bucket % curr == 0:
        return True, {curr: big_bucket // curr}
    if index < len(small_buckets) - 1:
        times = big_bucket // curr + 1
        while times > 0:
            times -= 1
            rest = big_bucket - times * curr
            can, fill_plan = _can_fill_recursive(rest, small_buckets, index + 1)
            if can:
                if times > 0:
                    fill_plan[curr] = times
                return True, fill_plan
    return False, {}


def can_fill(big_bucket: int, small_buckets) -> FillResult:
    if big_bucket == 0:
        return True, {}
    buckets_list = list(small_buckets)
    if not buckets_list:
        return False, {}
    buckets_sorted = sorted(set(buckets_list))
    if buckets_sorted[-1] == 0:
        buckets_sorted.pop()
    return _can_fill_recursive(big_bucket, buckets_sorted, 0)


# ============================================================
# Test cases
# ============================================================
import pytest


@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill, expected_plan", [
    (10, [2], True, {2: 5}),
    (8, [3, 5], True, {3: 1, 5: 1}),
    (11, [3, 2], True, {3: 3, 2: 1}),
    (11, [4, 3], True, {4: 2, 3: 1}),
    (11, [5, 3], True, {5: 1, 3: 2}),
])
def test_can_fill_simple(big_bucket, small_buckets, expected_can_fill, expected_plan):
    result_can_fill, result_plan = can_fill(big_bucket, small_buckets)
    assert result_can_fill == expected_can_fill
    assert result_plan == expected_plan


@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill, expected_plan", [
    (11, [2, 3], True, {3: 3, 2: 1}),
    (12, [3, 4], True, {4: 3}),
    (111, [4, 5, 3, 200], True, {5: 21, 3: 2}),
])
def test_can_fill_unsorted_small_buckets(big_bucket, small_buckets, expected_can_fill, expected_plan):
    result_can_fill, result_plan = can_fill(big_bucket, small_buckets)
    assert result_can_fill == expected_can_fill
    assert result_plan == expected_plan


@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill, expected_plan", [
    (11, [3, 3, 2], True, {3: 3, 2: 1}),
    (12, [3, 4, 3, 4], True, {4: 3}),
    (111, [200, 3, 4, 5, 3, 200], True, {5: 21, 3: 2}),
])
def test_can_fill_unsorted_duplicates_small_buckets(big_bucket, small_buckets, expected_can_fill, expected_plan):
    result_can_fill, result_plan = can_fill(big_bucket, small_buckets)
    assert result_can_fill == expected_can_fill
    assert result_plan == expected_plan


@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill, expected_plan", [
    (11, [3, 0, 2], True, {3: 3, 2: 1}),
    (12, [3, 4, 0], True, {4: 3}),
    (111, [0, 3, 4, 5, 3, 200], True, {5: 21, 3: 2}),
])
def test_can_fill_ignore_zero_small_buckets(big_bucket, small_buckets, expected_can_fill, expected_plan):
    result_can_fill, result_plan = can_fill(big_bucket, small_buckets)
    assert result_can_fill == expected_can_fill
    assert result_plan == expected_plan


@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill, expected_plan", [
    (10, [3], False, {}),
    (11, [6, 3], False, {}),
])
def test_cannot_fill_simple(big_bucket, small_buckets, expected_can_fill, expected_plan):
    result_can_fill, result_plan = can_fill(big_bucket, small_buckets)
    assert result_can_fill == expected_can_fill
    assert result_plan == expected_plan


@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill, expected_plan", [
    (0, [3, 1], True, {}),
    (0, [], True, {}),
])
def test_can_fill_zero_big_bucket(big_bucket, small_buckets, expected_can_fill, expected_plan):
    result_can_fill, result_plan = can_fill(big_bucket, small_buckets)
    assert result_can_fill == expected_can_fill
    assert result_plan == expected_plan


@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill, expected_plan", [
    (10, [13, 11], False, {}),
    (10, [13], False, {}),
])
def test_cannot_fill_smallest_bucket_is_too_big(big_bucket, small_buckets, expected_can_fill, expected_plan):
    result_can_fill, result_plan = can_fill(big_bucket, small_buckets)
    assert result_can_fill == expected_can_fill
    assert result_plan == expected_plan


@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill, expected_plan", [
    (10, [], False, {}),
])
def test_cannot_fill_no_small_buckets(big_bucket, small_buckets, expected_can_fill, expected_plan):
    result_can_fill, result_plan = can_fill(big_bucket, small_buckets)
    assert result_can_fill == expected_can_fill
    assert result_plan == expected_plan
