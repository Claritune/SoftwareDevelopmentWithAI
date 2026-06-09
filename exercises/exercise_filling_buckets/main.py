from typing import List, Tuple, Dict

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
