import random
from faker import Faker

r = random.Random()
f = Faker()

# Pre-generate name pools to avoid slow Faker calls during bulk generation
# 10K of each gives good variety with minimal memory (~1MB total)
_POOL_SIZE = 10000
_first_names = None
_last_names = None
_street_names = None

def _init_name_pools():
    """Lazily initialize name pools on first use."""
    global _first_names, _last_names, _street_names
    if _first_names is None:
        _first_names = [f.first_name() for _ in range(_POOL_SIZE)]
        _last_names = [f.last_name() for _ in range(_POOL_SIZE)]
        _street_names = [f.street_name() for _ in range(_POOL_SIZE)]

def get_first_name():
    """Get a random first name from pre-generated pool."""
    _init_name_pools()
    return r.choice(_first_names)

def get_last_name():
    """Get a random last name from pre-generated pool."""
    _init_name_pools()
    return r.choice(_last_names)

def get_street_name():
    """Get a random street name from pre-generated pool."""
    _init_name_pools()
    return r.choice(_street_names)

def generate_us_phone():
    """Generate a standard, valid US phone number in the format NXX-NXX-XXXX"""
    # Valid US area codes don't start with 0 or 1
    # Exchange codes (middle 3) also don't start with 0 or 1
    area_code = r.randint(200, 999)
    exchange = r.randint(200, 999)
    subscriber = r.randint(0, 9999)
    return f"{area_code}-{exchange}-{subscriber:04d}"

def generate_street_number():
    """Generate a street number between 1 and 9999, with realistic distribution."""
    street_range = r.randrange(0, 3)
    if street_range == 0:
        street = r.randrange(1,10)
    elif street_range == 1:
        street = r.randrange(10,100)
    else:
        street = r.randrange(100,10000)
    return street

def generate_stay_length(stay_weights: dict) -> int:
    """Generates a number of days for a hotel stay, based on the random factors for a customer archetype.
    
    Args:
        stay_weights (dict): A dictionary containing weightsfor stay length.
    
    Returns:
        int: The generated number of days for the stay.
    
    Remarks:
        The weights dict consists of keys that are strings representing either a
        single integer (e.g. '5') or a range of values, max-exclusive (same as range()
        behavior), with a hyphen between them (e.g. '5-8' means 5, 6 or 7 nights). The
        values for the keys are floating point probabilities betweeen 0 and 1."""

    # First, we add up all the *values* in the dict to get a total for the weights.
    # The total may not be 1, so if not we scale all values so that they total 1.
    total_weight = sum(stay_weights.values())
    if total_weight != 1.0:
        stay_weights = {k: v / total_weight for k, v in stay_weights.items()}
    
    # Next, generate a random float between 0 and 1.
    rand_val = r.random()

    # Now, we iterate through the weights, summing them up until we exceed rand_val.
    cumulative_weight = 0.0
    for k, v in stay_weights.items():
        cumulative_weight += v
        if rand_val <= cumulative_weight:
            # We found our key!
            if '-' in k:
                # It's a range
                parts = k.split('-')
                start = int(parts[0])
                end = int(parts[1])
                return r.randrange(start, end)
            else:
                # It's a single value
                return int(k)

