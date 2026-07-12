def process_batch(items: list[int]) -> list[int]:
    """
    Normalize a batch of integers to the range [0, 100].

    Uses min-max normalization (also called feature scaling), a standard
    technique in data preprocessing. The formula is:

        normalized = (x - min) / (max - min) * 100

    This maps the smallest value in the batch to 0 and the largest to 100,
    spreading everything else proportionally in between.

    Example:
        [200, 300, 400]  →  min=200, max=400, span=200
        200 → (200-200)/200*100 =   0
        300 → (300-200)/200*100 =  50
        400 → (400-200)/200*100 = 100
        Result: [0, 50, 100]

    The function only applies normalization when values exceed 100.
    If all values are already within [0, 100], they pass through unchanged.
    """
    if not items:
        return []

    if len(items) == 1:
        return [min(items[0], 100)]

    max_val = max(items)

    if max_val > 100:
        min_val = min(items)
        span = max_val - min_val
        return [int((x - min_val) / span * 100) for x in items]

    return items


# if __name__ == "__main__":
#     # These all work fine
#     print("Normalizing [200, 300, 400]:", process_batch([200, 300, 400]))
#     print("Normalizing [0, 50, 100]:   ", process_batch([0, 50, 100]))
#     print("Normalizing [150]:          ", process_batch([150]))
#     print("Normalizing []:             ", process_batch([]))
#     print("Normalizing [0, 250, 500]:  ", process_batch([0, 250, 500]))

#     # This crashes — but why?
#     print("Normalizing [200, 200, 200]:", process_batch([200, 200, 200]))