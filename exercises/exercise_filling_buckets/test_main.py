import pytest
from main import can_fill


def check(big_bucket, small_buckets, expected_can_fill, expected_fill_plan):
    result_can_fill, result_fill_plan = can_fill(big_bucket, small_buckets)
    assert result_can_fill == expected_can_fill
    assert result_fill_plan == expected_fill_plan


# ---------------------------------------------------------------------------
# CanFillSimple
# Buckets already sorted descending — bug still reorders them ascending.
# {11, {3,2}}: bug finds {2:4, 3:1} instead of {3:3, 2:1}  → FAIL
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill, expected_fill_plan", [
    (10, [2],    True,  {2: 5}),
    (8,  [3, 5], True,  {3: 1, 5: 1}),
    (11, [3, 2], True,  {3: 3, 2: 1}),
    (11, [4, 3], True,  {4: 2, 3: 1}),
    (11, [5, 3], True,  {5: 1, 3: 2}),
])
def test_can_fill_simple(big_bucket, small_buckets, expected_can_fill, expected_fill_plan):
    check(big_bucket, small_buckets, expected_can_fill, expected_fill_plan)


# ---------------------------------------------------------------------------
# CanFillUnsortedSmallBuckets
# Buckets given unsorted — correct code sorts descending, bug sorts ascending.
# {111, {4,5,3,200}}: largest bucket (200) ends up at back; early-exit check
#   `big_bucket < back` = 111 < 200 = True → returns False instead of True  → FAIL
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill, expected_fill_plan", [
    (11,  [2, 3],          True, {3: 3, 2: 1}),
    (12,  [3, 4],          True, {4: 3}),
    (111, [4, 5, 3, 200],  True, {5: 21, 3: 2}),
])
def test_can_fill_unsorted_small_buckets(big_bucket, small_buckets, expected_can_fill, expected_fill_plan):
    check(big_bucket, small_buckets, expected_can_fill, expected_fill_plan)


# ---------------------------------------------------------------------------
# CanFillUnsortedDuplicatesSmallBuckets
# Duplicates must be removed before sorting.  Same sort-order bug applies.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill, expected_fill_plan", [
    (11,  [3, 3, 2],             True, {3: 3, 2: 1}),
    (12,  [3, 4, 3, 4],          True, {4: 3}),
    (111, [200, 3, 4, 5, 3, 200], True, {5: 21, 3: 2}),
])
def test_can_fill_unsorted_duplicates_small_buckets(big_bucket, small_buckets, expected_can_fill, expected_fill_plan):
    check(big_bucket, small_buckets, expected_can_fill, expected_fill_plan)


# ---------------------------------------------------------------------------
# CanFillIgnoreZeroSmallBuckets
# Zeros must be stripped before the recursive call.  With correct (descending)
# sort zero lands at the back and is removed.  With the bug zero lands at the
# front, the back-check misses it, and the recursive helper hits `curr=0` →
# ZeroDivisionError.  → FAIL (exception, not wrong result)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill, expected_fill_plan", [
    (11,  [3, 0, 2],          True, {3: 3, 2: 1}),
    (12,  [3, 4, 0],          True, {4: 3}),
    (111, [0, 3, 4, 5, 3, 200], True, {5: 21, 3: 2}),
])
def test_can_fill_ignore_zero_small_buckets(big_bucket, small_buckets, expected_can_fill, expected_fill_plan):
    check(big_bucket, small_buckets, expected_can_fill, expected_fill_plan)


# ---------------------------------------------------------------------------
# CannotFillSimple
# These happen to produce the right False result even with the bug.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill, expected_fill_plan", [
    (10, [3],    False, {}),
    (11, [6, 3], False, {}),
])
def test_cannot_fill_simple(big_bucket, small_buckets, expected_can_fill, expected_fill_plan):
    check(big_bucket, small_buckets, expected_can_fill, expected_fill_plan)


# ---------------------------------------------------------------------------
# CanFillZeroBigBucket
# big_bucket == 0 is handled before sorting, so the bug has no effect.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill, expected_fill_plan", [
    (0, [3, 1], True, {}),
    (0, [],     True, {}),
])
def test_can_fill_zero_big_bucket(big_bucket, small_buckets, expected_can_fill, expected_fill_plan):
    check(big_bucket, small_buckets, expected_can_fill, expected_fill_plan)


# ---------------------------------------------------------------------------
# CannotFillSmallestBucketIsTooBig
# After ascending sort the largest bucket is at the back, so the early-exit
# check `big_bucket < back` still fires and returns False — correct by accident.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill, expected_fill_plan", [
    (10, [13, 11], False, {}),
    (10, [13],     False, {}),
])
def test_cannot_fill_smallest_bucket_is_too_big(big_bucket, small_buckets, expected_can_fill, expected_fill_plan):
    check(big_bucket, small_buckets, expected_can_fill, expected_fill_plan)


# ---------------------------------------------------------------------------
# CannotFillNoSmallBuckets
# Empty-list guard fires before sorting; bug has no effect.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("big_bucket, small_buckets, expected_can_fill, expected_fill_plan", [
    (10, [], False, {}),
])
def test_cannot_fill_no_small_buckets(big_bucket, small_buckets, expected_can_fill, expected_fill_plan):
    check(big_bucket, small_buckets, expected_can_fill, expected_fill_plan)
