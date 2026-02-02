import numpy as np

def normalized_random_bounded(mean, sd, min_val=None, max_val=None) -> float:
    value = np.random.normal(mean, sd)
    if min_val is not None:
        value = max(value, min_val)
    if max_val is not None:
        value = min(value, max_val)
    return value
