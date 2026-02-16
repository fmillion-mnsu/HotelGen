# Phase 0: Initial setup for hotel generation
# - Select corporation name
# - Determine number of hotels to generate per class

from xl9045qi.hotelgen import data
from xl9045qi.hotelgen import normalized_random_bounded as rand
from xl9045qi.hotelgen.generators import r
from rich import print

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from xl9045qi.hotelgen.simulation import HGSimulationState

def phase0(inst: HGSimulationState) -> bool:
    """Initial phase of the hotel generation simulation.

    This phase sets up the initial parameters for hotel generation.

    Args:
        state (HGSimulationState): The current state of the simulation.
    """

    if inst.state.get("last_phase", -1) >= 0:
        print("[bold]Phase 0 already completed, skipping.")
        return False

    # This is the bulk of the code that actually does the generation.
    print("[bold]Start Hotel Database Generation.")

    inst.state['corporation'] = r.choice(data.nouns) + " " + r.choice(data.corporation_suffixes)

    print("Corporation name: " + inst.state.get('corporation', ""))

    # Phase 0: Figure out how many hotels of each type to generate
    hotel_count_mean = inst.job['generation']['hotels']['count']
    hotel_count_sd = inst.job['generation']['hotels']['sd']

    total_property_count = int(rand(hotel_count_mean, hotel_count_sd, min_val=10))
    print(f"Will generate [bold]{total_property_count}[/bold] hotels (requested {hotel_count_mean} with SD {hotel_count_sd}).")

    # How many resorts?
    resorts_fraction = inst.job['generation']['ratios'].get('resorts', 0.05)
    resort_count = int(total_property_count * resorts_fraction)
    hotel_fraction = inst.job['generation']['ratios'].get('hotels', 0.55)
    hotel_count = int(total_property_count * hotel_fraction)
    motel_fraction = inst.job['generation']['ratios'].get('motels', 0.4)
    motel_count = int(total_property_count * motel_fraction)
    if resort_count + hotel_count + motel_count < total_property_count:
        resort_count += total_property_count - (resort_count + hotel_count + motel_count)

    print(f"  - {resort_count:4d} resorts")
    print(f"  - {hotel_count:4d} hotels")
    print(f"  - {motel_count:4d} motels")
    inst.state['gen_params']['property_distribution'] = {
        "resorts": resort_count,
        "hotels": hotel_count,
        "motels": motel_count
    }

    return True