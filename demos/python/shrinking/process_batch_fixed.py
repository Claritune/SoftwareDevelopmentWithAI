def process_batch(items: list[int]) -> list[int]:
    """
    Normalize a batch of integers to the range [0, 100].

    Fixed version, after the demo's findings:
      - equal values out of range no longer divide by zero: they are clamped
      - integer arithmetic replaces float division, so 29/100*100 is 29, not 28
      - HUMAN DECISION: the output range [0, 100] wins over pass-through,
        so a batch is normalized whenever any value falls outside [0, 100]
    """
    if not items:
        return []

    lo, hi = min(items), max(items)

    if 0 <= lo and hi <= 100:
        return list(items)

    if lo == hi:
        return [min(max(lo, 0), 100)] * len(items)

    span = hi - lo
    return [(x - lo) * 100 // span for x in items]
