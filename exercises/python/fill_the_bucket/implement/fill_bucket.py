"""
Fill the bucket - implement the solution

Goal: fill the big bucket using small buckets with the
minimum number of fill operations.
A fill operation = using a small bucket of any size once.
Example: using bucket 7 twice and bucket 2 three times
         = 5 fill operations

Requirements:
- Handle unsorted input (sort internally)
- Handle duplicate bucket sizes (treat as unique)
- Handle zeros in small_buckets (ignore them)
- big_bucket == 0 -> always fillable with empty plan
- empty small_buckets with big_bucket > 0 -> not fillable

Examples:
  can_fill(10, [2])       -> (True,  {2: 5})
  can_fill(8,  [3, 5])    -> (True,  {3: 1, 5: 1})
  can_fill(11, [3, 2])    -> (True,  {3: 3, 2: 1})
  can_fill(12, [3, 4])    -> (True,  {4: 3})
  can_fill(10, [3])       -> (False, {})
  can_fill(0,  [3, 1])    -> (True,  {})
  can_fill(10, [])        -> (False, {})
"""

from typing import Dict, Tuple

FillPlan = Dict[int, int]
FillResult = Tuple[bool, FillPlan]


def can_fill(big_bucket: int, small_buckets) -> FillResult:
    # TODO: implement
    return False, {}


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
