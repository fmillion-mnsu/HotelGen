import tqdm

from xl9045qi.hotelgen import data
from xl9045qi.hotelgen import normalized_random_bounded as rand
from xl9045qi.hotelgen.generators import r
from rich import print

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from xl9045qi.hotelgen.simulation import HGSimulationState

def phase1(inst: HGSimulationState):
    """Phase 1 of the hotel generation simulation.

    This phase generates the hotels based on the parameters set in phase 0.

    Args:
        state (HGSimulationState): The current state of the simulation.
    """

    if inst.state.get("last_phase", -1) >= 1:
        print("[bold]Phase 1 already completed, skipping.")
        return

    from xl9045qi.hotelgen.generators.hotel import generate_hotel
    from xl9045qi.hotelgen.generators.distribution import generate_state_distribution

    # Phase 1.1: Generate resorts

    # Logic: We'll ensure to try to generate at least one resort
    # per region, but after that we'll just scatter them randomly.
    tourist_regions = list(data.tourist_regions.keys())
    r.shuffle(tourist_regions)

    for _ in tqdm.tqdm(range(inst.state['gen_params']['property_distribution']['resorts']), desc="Generating resorts"):
        if len(tourist_regions) > 0:
            region = tourist_regions.pop()
        else:
            region = r.choice(list(data.tourist_regions.keys()))
        
        hotel = generate_hotel("resort", tourist_region=region, state="")
        inst.state['hotels'].append(hotel)

    # Phase 1.2: Generate hotels
    dist = generate_state_distribution(inst.state['gen_params']['property_distribution']['hotels'], reassignments=inst.state['gen_params']['property_distribution']['hotels']//25)
    with tqdm.tqdm(total=inst.state['gen_params']['property_distribution']['hotels'], desc="Generating hotels") as pbar:
        for state, count in dist.items():
            for _ in range(count):
                hotel = generate_hotel("hotel", state=state)
                inst.state['hotels'].append(hotel)
                pbar.update(1)
    # Phase 1.3: Generate motels
    dist = generate_state_distribution(inst.state['gen_params']['property_distribution']['motels'], reassignments=inst.state['gen_params']['property_distribution']['motels']//25)
    with tqdm.tqdm(total=inst.state['gen_params']['property_distribution']['motels'], desc="Generating motels") as pbar:
        for state, count in dist.items():
            for _ in range(count):
                hotel = generate_hotel("motel", state=state)
                inst.state['hotels'].append(hotel)
                pbar.update(1)

    # Assign an incrementing ID to each hotel
    r.shuffle(inst.state['hotels'])
    for idx, hotel in enumerate(inst.state['hotels']):
        hotel.id = idx + 1

    print(f"{len(inst.state['hotels'])} hotels generated successfully.")
    inst.state['last_phase'] = 1
