import random

import tqdm
from rich import print

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from xl9045qi.hotelgen.simulation import HGSimulationState

import xl9045qi.hotelgen.simulation as sim
from xl9045qi.hotelgen.generators import giftshop

def phase5(inst: HGSimulationState) -> bool:
    """Phase 5: Generate gift shops and products"""
    
    if inst.state.get("last_phase", -1) >= 5:
        print("[bold]Phase 5 already completed, skipping.")
        return False

    # Determine which hotels get gift shops
    # All resorts do
    all_resorts = [h for h in inst.state['hotels'] if h.type == 'Resort']
    
    # Get all hotels as well:
    all_hotels = [h for h in inst.state['hotels'] if h.type == "Hotel"]

    if len(all_resorts) == 0 or len(all_hotels) == 0:
        print(f"ERROR: Can't proceed - there are {len(all_resorts)} resorts and {len(all_hotels)} hotels.")
        return False
    print(f"There are {len(all_resorts)} resorts and {len(all_hotels)} hotels.")

    resort_chance = inst.job['generation']['giftshops']['resorts']
    hotel_chance = inst.job['generation']['giftshops']['hotels']
    resort_count = int(len(all_resorts) * resort_chance)
    hotel_count = int(len(all_hotels) * hotel_chance)

    print(f"Will generate {resort_count} resort gift shops and {hotel_count} hotel gift shops.")

    active_resorts = random.sample(all_resorts, resort_count)
    active_hotels = random.sample(all_hotels, hotel_count)

    # shuffle lists in place
    random.shuffle(active_resorts)
    random.shuffle(active_hotels)

    for _ in tqdm.trange(hotel_count+resort_count):
        if len(active_resorts) > 0:
            hotel = active_resorts.pop()
        elif len(active_hotels) > 0:
            hotel = active_hotels.pop()
        else:
            break

        this_gs = giftshop.generate_giftshop(hotel)
        inst.state['giftshops'].append(this_gs[0])
        inst.state['products'].extend(this_gs[1])

    inst.state['last_phase'] = 5

    return True