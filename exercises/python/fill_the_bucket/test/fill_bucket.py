"""
Fill the bucket - add unit tests
Goal: fill the big bucket with minimum fill operations
a fill operation = using a small bucket of any size
example: using 7 twice + 2 three times = 5 operations
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


if __name__ == "__main__":
    examples = [
        (10, [2]),
        (8, [3, 5]),
        (11, [3, 2]),
        (12, [3, 4]),
        (10, [3]),
        (0, [3, 1]),
        (10, []),
    ]
    for big, smalls in examples:
        result, plan = can_fill(big, smalls)
        status = "can fill" if result else "cannot fill"
        plan_str = ", ".join(f"{k} x {v}" for k, v in plan.items())
        print(f"{big} with {smalls}: {status}" + (f" -> {{{plan_str}}}" if plan else ""))
