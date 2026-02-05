import numpy as np

def normalized_random_bounded(mean, sd, min_val=None, max_val=None) -> float:
    value = np.random.normal(mean, sd)
    if min_val is not None:
        value = max(value, min_val)
    if max_val is not None:
        value = min(value, max_val)
    return value

def log_scaled_value(x: float, min: float, max: float, curve_factor: float) -> float:
    """
    Generate an approximately logarithmically-scaled value given min, max, curve_factor and point (x).

    :param x: The point between min and max to scale
    :param min: The value at the low end of the range
    :param max: The value at the high end of the range
    :param curve_factor: How steep the curve is. 0 = completely linear, 1 = always max, -1 = always min.
    """

    # Handle degenerate range
    if max == min:
        return min

    # Handle 0 factor
    if curve_factor == 0.0:
        return x

    # Normalize and clamp
    t = (x - min) / (max - min)
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t

    # Clamp factor
    if curve_factor < -1.0: curve_factor = -1.0
    if curve_factor >  1.0: curve_factor =  1.0

    # Edge factors (avoid division by zero / infinity math surprises)
    if curve_factor == 1.0:
        return min if t == 0.0 else max
    if curve_factor == -1.0:
        return max if t == 1.0 else min

    # Map factor -> exponent
    k = (1.0 - curve_factor) / (1.0 + curve_factor)

    # Curve and rescale
    return min + (max - min) * (t ** k)