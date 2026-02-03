import tqdm

from xl9045qi.hotelgen import data
from xl9045qi.hotelgen import normalized_random_bounded as rand
from xl9045qi.hotelgen.generators import r
from rich import print

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from xl9045qi.hotelgen.simulation import HGSimulationState

def phase2(inst: HGSimulationState):
    """Phase 2 of the hotel generation simulation.

    This phase generates customers for the hotels.

    Args:
        state (HGSimulationState): The current state of the simulation.
    """

    if inst.state.get("last_phase", -1) >= 2:
        print("[bold]Phase 2 already completed, skipping.")
        return

    from xl9045qi.hotelgen.generators.distribution import generate_state_distribution
    from xl9045qi.hotelgen.generators.customer import generate_customer, init_customer_cache

    # Initialize cache if not already present
    if 'cache' not in inst.state:
        inst.state['cache'] = {}

    # Initialize customer generation caches (zipcode lists, email templates)
    init_customer_cache(inst)

    # Phase 2: Figure out how many customers to generate
    customer_count_mean = inst.job['generation']['customers']['count']
    customer_count_sd = inst.job['generation']['customers']['sd']
    customer_count_state_sd = inst.job['generation']['customers'].get('state_sd', 0.2)
    total_customer_count = int(rand(customer_count_mean, customer_count_sd, min_val=10))
    print(f"Will generate [bold]{total_customer_count}[/bold] customers (requested {customer_count_mean} with SD {customer_count_sd}).")

    # Generate a distribution of customers per state
    cdist = generate_state_distribution(total_customer_count, sd = customer_count_state_sd, reassignments=total_customer_count//500)
    inst.state['gen_params']['customer_state_distribution'] = dict(cdist) # make a copy

    # Generate distribution of customers per customer class
    c_classes = list(data.customer_archetypes.keys())
    c_class_probs = [data.customer_archetypes[c]['percentage'] for c in c_classes]
    total_probs = sum(c_class_probs)
    c_class_probs = [p / total_probs for p in c_class_probs]
    # Scale c_class_probs up to counts
    c_class_counts = {k: v for k, v in zip(c_classes, [int(round(p * total_customer_count)) for p in c_class_probs])}

    inst.state['gen_params']['customer_class_distribution'] = dict(c_class_counts) # make a copy

    # Generate customers using concurrent.futures

    with tqdm.tqdm(total=total_customer_count, desc="Generating customers") as pbar:
        for _ in range(total_customer_count):
            # Get available states (count > 0), fallback to all states if exhausted
            available_states = [s for s, count in cdist.items() if count > 0]
            if available_states:
                this_state = r.choice(available_states)
            else:
                this_state = r.choice(list(cdist.keys()))

            # Get available types (count > 0), fallback to all types if exhausted
            available_types = [t for t, count in c_class_counts.items() if count > 0]
            if available_types:
                this_type = r.choice(available_types)
            else:
                this_type = r.choice(c_classes)
            customer = generate_customer(inst, this_type, state=this_state)
            inst.state['customers'].append(customer)
            cdist[this_state] -= 1
            c_class_counts[this_type] -= 1
            pbar.update(1)

    r.shuffle(inst.state['customers'])
    for idx, customer in enumerate(inst.state['customers']):
        customer.id = idx + 1

    print(f"{len(inst.state['customers'])} customers generated successfully.")

    # Total of all hotel rooms
    total_room_count = sum([sum([room_info.count for room_info in hotel.rooms.values()]) for hotel in inst.state['hotels']])
    print(f"There are a total of {total_room_count} rooms across all hotels generated.")

    inst.state['last_phase'] = 2
    inst.state['gen_params']['total_rooms'] = total_room_count
    inst.state['gen_params']['total_customers'] = len(inst.state['customers'])
