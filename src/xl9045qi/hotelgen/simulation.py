import datetime
import pickle

import tqdm

from xl9045qi.hotelgen import data
from xl9045qi.hotelgen.generators import r
from xl9045qi.hotelgen import normalized_random_bounded as rand
from xl9045qi.hotelgen import log_scaled_value as lsv
from rich import print

class HGSimulationState:

    def __init__(self, job):
        self.job = job
        # Store hotels here
        self.state = {}
        self.state['hotels'] = []
        self.state['customers'] = []
        self.state['gen_params'] = {}

    def export(self, path: str):
        """Export the generated hotel data to a specified path as a pickle file.

        Args:
            path (str): The file path where the hotel data should be saved.
        """
        with open(path, "wb") as f:
            data = {
                "params": self.state['gen_params'],
                "jobfile": self.job,
                "state": self.state
            }
            pickle.dump(data, f)

        #print(f"Exported {len(inst.state['hotels'])} hotels to {path}.")
    
    def import_pkl(self, path: str):
        """Import generated hotel data from a specified pickle file.

        Args:
            path (str): The file path from which the hotel data should be loaded.
        """
        with open(path, "rb") as f:
            data = pickle.load(f)
            self.job = data.get("jobfile", {})
            self.state = data.get("state", {})

def phase0(inst: HGSimulationState):
    """Initial phase of the hotel generation simulation.

    This phase sets up the initial parameters for hotel generation.

    Args:
        state (HGSimulationState): The current state of the simulation.
    """

    if inst.state.get("last_phase", -1) >= 0:
        print("[bold]Phase 0 already completed, skipping.")
        return

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
        hotel['id'] = idx + 1

    print(f"{len(inst.state['hotels'])} hotels generated successfully.")
    inst.state['last_phase'] = 1

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
    from xl9045qi.hotelgen.generators.customer import generate_customer

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
            while True:
                this_state = r.choice(list(cdist.keys()))
                if cdist[this_state] <= 0:
                    continue
                break
            # Pick type based on c_class_counts
            while True:
                this_type = r.randint(1, len(c_classes))
                
                this_type = c_classes[this_type - 1]

                if c_class_counts[this_type] <= 0:
                    continue
                break
            customer = generate_customer(this_type, state=this_state)
            inst.state['customers'].append(customer)
            cdist[this_state] -= 1
            c_class_counts[this_type] -= 1
            pbar.update(1)
        
    r.shuffle(inst.state['customers'])
    for idx, customer in enumerate(inst.state['customers']):
        customer['id'] = idx + 1

    print(f"{len(inst.state['customers'])} customers generated successfully.")

    # Total of all hotel rooms
    total_room_count = sum([sum([room_info['count'] for room_info in hotel['rooms'].values()]) for hotel in inst.state['hotels']])
    print(f"There are a total of {total_room_count} rooms across all hotels generated.")

    inst.state['last_phase'] = 2
    inst.state['gen_params']['total_rooms'] = total_room_count
    inst.state['gen_params']['total_customers'] = len(inst.state['customers'])

def phase3(inst: HGSimulationState):
    """Prepare the generated data for simulation use.

    This involves precomputing certain data structures to make simulation runs faster.
    """

    if inst.state.get("last_phase", -1) >= 3:
        print("[bold]Phase 3 already completed, skipping.")
        return    

    # First, we need a simple dict consisting of key = id, value = dict with key = room type, value = empty list.
    inst.state['occupied_rooms'] = {
        hotel['id']: {room_type: [] for room_type in hotel['rooms'].keys()}
        for hotel in inst.state['hotels']
    }
    # Lists will contain tuples of (customer_id, checkout_date, stay_length)

    # We also need a list to manage currently occupied *Customers*
    # The values in these lists will be tuples of (id, available_date).
    inst.state['occupied_customers'] = {
        x: []
        for x in data.customer_archetypes.keys()
    }

    # We also want to cache some things in memory.
    # First: A dict of key = archetype, value = list of all customer ID numbers
    inst.state['cache'] = {
        'customers_by_archetype': {}
    }
    for archetype in data.customer_archetypes.keys():
        inst.state['cache']['customers_by_archetype'][archetype] = [
            customer['id']
            for customer in inst.state['customers']
            if customer['type'] == archetype
        ]
    
    # All hotels by ID
    inst.state['cache']['hotels_by_id'] = {
        hotel['id']: hotel
        for hotel in inst.state['hotels']
    }

    inst.state['current_day'] = datetime.datetime.strptime(inst.job['generation']['dates']['start'], "%Y-%m-%d")
    end_day = datetime.datetime.strptime(inst.job['generation']['dates']['end'], "%Y-%m-%d")
    inst.state['days_left'] = (end_day - inst.state['current_day']).days + 1 

    # Will hold transaction events.
    # Transactions will be stored as dicts and normalized when database insert is
    # performed.
    inst.state['transactions'] = []

    print(f"Preparation ready. Will generate {inst.state['days_left']} days of simulated transactions.")

    inst.state['last_phase'] = 3

def process_day(inst: HGSimulationState, day: int = 0):
    """Process a single day of simulation.

    Remarks:
        This will run one day's worth of simulation and update all of the local
        state.
    """

    # Step 1. Scan for any hotels that have checkouts today.
    # If found, introduce a financial transaction recording the checkout.

    # hotel_state contains hotel ID as keys; each value has room type as key, booking as value

    for hotel_id in inst.state['occupied_rooms'].keys():
        hotel = inst.state['cache']['hotels_by_id'][hotel_id]
        for rt in inst.state['occupied_rooms'][hotel_id]:
            for booking in inst.state['occupied_rooms'][hotel_id][rt]:
                if booking[1] <= inst.state['current_day']:
                    # Checkout today
                    # Record transaction                        
                    trans = inst.generate_transaction(hotel_id, booking[0], booking[2], rt)
                    inst.state['transactions'].append(trans)
                    # Free up room
                    inst.state['occupied_rooms'][hotel_id][rt].remove(booking)

    # Step 2: Determine today's occupancy percentage.
    today_occupancy = lsv(day, 0, 45, -0.4) / 45.0

    # Step 3: For each hotel, determine how many rooms to fill today.
    hotel_desired_occupancy = {}
    for hotel in inst.state['hotels']:
        hotel_desired_occupancy[hotel['id']] = int(round(sum([room_info['count'] for room_info in hotel['rooms'].values()]) * today_occupancy))

    print(hotel_desired_occupancy)
    exit(1)

