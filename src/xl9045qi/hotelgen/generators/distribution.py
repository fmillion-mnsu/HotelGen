from xl9045qi.hotelgen import data
from xl9045qi.hotelgen import normalized_random_bounded as rand
from xl9045qi.hotelgen.generators import r

def generate_state_distribution(count: int, sd: float = 0.0, reassignments: int = 0) -> dict:
    """Generate a distribution of how many entities to generate in each state based on a
    total desired number of entities. This is used both for hotel and customer generation.

    This uses the built in population distribution data to determine a reasonable
    number of hotels per state, with variation built in.

    Returns a dict containing state codes as key and the number of hotels as an int value.

    Args:
        count (int): The total number of entities to distribute.
        sd (float, optional): The standard deviation to deviate each population multiplier by. Defaults to 0.0 (use multipliers as-is)
        reassignments (int, optional): The number of random reassignments to perform. Defaults to 0.

    Returns:
        dict: A dictionary with state codes as keys and number of entities as values.

    Remarks:
        Even if you use sd > 0.0, the final distribution will always sum to 'count'.
        Random reassignments will always be performed to bring the total to 'count' if needed.
    """

    # 1. Get a total of all the price multipliers
    all_multipliers = sum(list(data.state_population_ratios.values()))

    # 2. Compute the scaling factor
    scaling_factor = count / all_multipliers

    # 3. Generate baseline distribution
    if sd <= 0.0:
        distribution = {
            state: int(round(multiplier * scaling_factor))
            for state, multiplier in data.state_population_ratios.items()
        }
    else:
        distribution = {
            state: int(round(multiplier * rand(scaling_factor, sd, min_val=0.0)))
            for state, multiplier in data.state_population_ratios.items()
        }

    # 4.1. Ensure the total distribution has the correct number of hotels
    while sum(distribution.values()) < count:
        # add one to a random state
        state = r.choice(list(distribution.keys()))
        distribution[state] += 1

    # 4.2. If we ended up with too many, subtract from random states.
    while sum(distribution.values()) > count:
        state = r.choice(list(distribution.keys()))
        if distribution[state] > 0:
            distribution[state] -= 1

    # 5. Run random reassignments
    for _ in range(reassignments):
        while True:
            # Pick two different states
            state_from, state_to = r.sample(list(distribution.keys()), 2)
            # If the "from" state has at least one hotel, move it to the "to" state
            if distribution[state_from] > 0:
                distribution[state_from] -= 1
                distribution[state_to] += 1
                break
            continue # Try again if we couldn't reassign

    return distribution
