"""
Fill the bucket - find weak tests with mutation testing
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
    buckets_sorted = sorted(set(buckets_list), reverse=True)
    if buckets_sorted[-1] == 0:
        buckets_sorted.pop()
    return _can_fill_recursive(big_bucket, buckets_sorted, 0)


# ============================================================
# Test cases
# ============================================================
import pytest


# Full tests - check both boolean and fill plan
@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill, expected_plan", [
    (10, [2], True, {2: 5}),
    (12, [3, 4], True, {4: 3}),
])
def test_can_fill_basic(big_bucket, small_buckets, expected_can_fill, expected_plan):
    result_can_fill, result_plan = can_fill(big_bucket, small_buckets)
    assert result_can_fill == expected_can_fill
    assert result_plan == expected_plan


@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill, expected_plan", [
    (10, [3], False, {}),
    (10, [13, 11], False, {}),
])
def test_cannot_fill_basic(big_bucket, small_buckets, expected_can_fill, expected_plan):
    result_can_fill, result_plan = can_fill(big_bucket, small_buckets)
    assert result_can_fill == expected_can_fill
    assert result_plan == expected_plan


# Weak tests - only check the boolean result, not the plan
@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill", [
    (8, [3, 5], True),
    (11, [4, 3], True),
    (11, [5, 3], True),
    (111, [4, 5, 3, 200], True),
])
def test_can_fill_multi_bucket(big_bucket, small_buckets, expected_can_fill):
    result_can_fill, _ = can_fill(big_bucket, small_buckets)
    assert result_can_fill == expected_can_fill


@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill", [
    (11, [6, 3], False),
])
def test_cannot_fill_multi_bucket(big_bucket, small_buckets, expected_can_fill):
    result_can_fill, _ = can_fill(big_bucket, small_buckets)
    assert result_can_fill == expected_can_fill
