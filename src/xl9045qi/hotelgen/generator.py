import json
import os
import os.path
import pickle
import random

from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from rich import print
import numpy as np
import tqdm

from faker import Faker
from yaml import safe_load

from xl9045qi.hotelgen import normalized_random_bounded as rand

r = random.Random()
f = Faker()

THREAD_LOCK = Lock()

HOTEL_NAME_TEMPLATES = [
    "{adj} {noun} {type}",
    "{adj} {noun} {type}",
    "{adj} {noun} {type}",
    "{adj} {noun} {type}",
    "{adj} {noun} {type}",
    "{adj} {noun} {type}",
    "{adj} {noun} {type}",
    "{adj} {noun} {type}",
    "The {adj} {noun}",
    "The {adj} {noun}",
    "The {adj} {noun}",
    "The {adj} {noun} {type}",
    "The {noun} at {loc}",
    "The {adj} {noun} at {loc}",
    "The {type} {noun} at {loc}"
    "{noun} {type} of {loc}",
    "The {type} {adj} {noun}",
]
CUSTOMER_EMAIL_TEMPLATES = {
    "{fname}.{lname}@{domain}",
    "{fname}{lname}@{domain}",
    "{f_initial}{lname}@{domain}",
    "{fname}{l_initial}@{domain}",
    "{lname}{fname}@{domain}",
    "{lname}.{fname}@{domain}",
    "{fname}{year}@{domain}",
    "{lname}{year}@{domain}",
    "{f_initial}{lname}{year}@{domain}",
    "{fname}{l_initial}{year}@{domain}"
}
HOTEL_DOMAIN_TEMPLATES = [
    "{adj}{noun}{type}",
    "{adj}{noun}",
    "{noun}{type}",
    "{noun}at{loc}"
]
HOTEL_DOMAIN_TLDS = [
    ".com",
    ".com",
    ".com",
    ".com",
    ".com",
    ".net",
    ".net",
    ".hotel",
    ".travel",
    ".vacations"
]

ZIPCODES = json.load(open(os.path.dirname(__file__) + "/data/zipcodes.json","r"))
ZIPCODES_FLAT = {zc: state_code for state_code, zc_dict in ZIPCODES.items() for zc, city in zc_dict.items()}

EMAILS = ['info','contact','reservations','booking','stay','help','guestservices','reserve','book','support','frontdesk','service','customerservice','events','office']
URL_STEMS = ['home','?lang=en_US','index.html','welcome','book']
NOUNS = open(os.path.dirname(__file__) + "/data/noun.txt","r").read().splitlines()
ADJS = open(os.path.dirname(__file__) + "/data/adj.txt","r").read().splitlines()
PARAMS = safe_load(open(os.path.dirname(__file__) + "/data/parameters.yaml","r"))

class HotelGen():
    """Implements a full HotelGen job run. Instances of this class store data relevant to each individual generation run during the process."""

    def __init__(self, job: dict):
        self.job = job
        # Store hotels here
        self.hotels = []
        self.customers = []
        self.gen_params = {}
        self.state = {}

    def export(self, path: str):
        """Export the generated hotel data to a specified path as a pickle file.

        Args:
            path (str): The file path where the hotel data should be saved.
        """
        with open(path, "wb") as f:
            data = {
                "params": self.gen_params,
                "jobfile": self.job,
                "hotels": self.hotels,
                "customers": self.customers,
                "state": self.state
            }
            pickle.dump(data, f)

        #print(f"Exported {len(self.hotels)} hotels to {path}.")
    
    def import_pkl(self, path: str):
        """Import generated hotel data from a specified pickle file.

        Args:
            path (str): The file path from which the hotel data should be loaded.
        """
        with open(path, "rb") as f:
            data = pickle.load(f)
            self.gen_params = data.get("params", {})
            self.job = data.get("jobfile", {})
            self.hotels = data.get("hotels", [])
            self.customers = data.get("customers", [])
            self.state = data.get("state", {})

    def start(self):

        # This is the bulk of the code that actually does the generation.
        print("[bold]Start Hotel Database Generation.")

        self.state['corporation'] = random.choice(NOUNS) + " " + random.choice(PARAMS["corporation_suffixes"])

        print("Corporation name: " + self.state.get('corporation', ""))

        # Phase 0: Figure out how many hotels of each type to generate
        hotel_count_mean = self.job['generation']['hotels']['count']
        hotel_count_sd = self.job['generation']['hotels']['sd']

        total_property_count = int(rand(hotel_count_mean, hotel_count_sd, min_val=10))
        print(f"Will generate [bold]{total_property_count}[/bold] hotels (requested {hotel_count_mean} with SD {hotel_count_sd}).")

        # How many resorts?
        resorts_fraction = self.job['generation']['ratios'].get('resorts', 0.05)
        resort_count = int(total_property_count * resorts_fraction)
        hotel_fraction = self.job['generation']['ratios'].get('hotels', 0.55)
        hotel_count = int(total_property_count * hotel_fraction)
        motel_fraction = self.job['generation']['ratios'].get('motels', 0.4)
        motel_count = int(total_property_count * motel_fraction)
        if resort_count + hotel_count + motel_count < total_property_count:
            resort_count += total_property_count - (resort_count + hotel_count + motel_count)
        
        print(f"  - {resort_count:4d} resorts")
        print(f"  - {hotel_count:4d} hotels")
        print(f"  - {motel_count:4d} motels")
        self.gen_params['property_distribution'] = {
            "resorts": resort_count,
            "hotels": hotel_count,
            "motels": motel_count
        }

        # Phase 1.1: Generate resorts

        # Logic: We'll ensure to try to generate at least one resort
        # per region, but after that we'll just scatter them randomly.
        tourist_regions = list(PARAMS['tourist_regions'].keys())
        r.shuffle(tourist_regions)

        for _ in tqdm.tqdm(range(resort_count), desc="Generating resorts"):
            if len(tourist_regions) > 0:
                region = tourist_regions.pop()
            else:
                region = r.choice(list(PARAMS['tourist_regions'].keys()))
            
            hotel = generate_hotel("resort", tourist_region=region, state="")
            self.hotels.append(hotel)

        # Phase 1.2: Generate hotels
        dist = generate_state_distribution(hotel_count, reassignments=total_property_count//25)
        with tqdm.tqdm(total=hotel_count, desc="Generating hotels") as pbar:
            for state, count in dist.items():
                for _ in range(count):
                    hotel = generate_hotel("hotel", state=state)
                    self.hotels.append(hotel)
                    pbar.update(1)
        # Phase 1.3: Generate motels
        dist = generate_state_distribution(motel_count, reassignments=total_property_count//25)
        with tqdm.tqdm(total=motel_count, desc="Generating motels") as pbar:
            for state, count in dist.items():
                for _ in range(count):
                    hotel = generate_hotel("motel", state=state)
                    self.hotels.append(hotel)
                    pbar.update(1)

        # Assign an incrementing ID to each hotel
        r.shuffle(self.hotels)
        for idx, hotel in enumerate(self.hotels):
            hotel['id'] = idx + 1

        print(f"{len(self.hotels)} hotels generated successfully.")
        self.state['last_phase'] = 1
        self.export("01-hotels-generated.pkl")

        # Phase 2: Figure out how many customers to generate
        customer_count_mean = self.job['generation']['customers']['count']
        customer_count_sd = self.job['generation']['customers']['sd']
        customer_count_state_sd = self.job['generation']['customers'].get('state_sd', 0.2)

        total_customer_count = int(rand(customer_count_mean, customer_count_sd, min_val=10))
        print(f"Will generate [bold]{total_customer_count}[/bold] customers (requested {customer_count_mean} with SD {customer_count_sd}).")

        # Generate a distribution of customers per state
        cdist = generate_state_distribution(total_customer_count, sd = customer_count_state_sd, reassignments=total_customer_count//500)
        self.gen_params['customer_state_distribution'] = dict(cdist) # make a copy
        
        # Generate distribution of customers per customer class
        c_classes = list(PARAMS['customer_archetypes'].keys())
        c_class_probs = [PARAMS['customer_archetypes'][c]['percentage'] for c in c_classes]
        total_probs = sum(c_class_probs)
        c_class_probs = [p / total_probs for p in c_class_probs]
        # Scale c_class_probs up to counts
        c_class_counts = {k: v for k, v in zip(c_classes, [int(round(p * total_customer_count)) for p in c_class_probs])}

        self.gen_params['customer_class_distribution'] = dict(c_class_counts) # make a copy

        # Generate customers using concurrent.futures

        with tqdm.tqdm(total=total_customer_count, desc="Generating customers") as pbar:
            for _ in range(total_customer_count):
                while True:
                    this_state = r.choice(list(cdist.keys()))
                    with THREAD_LOCK:
                        if cdist[this_state] <= 0:
                            continue
                    break
                # Pick type based on c_class_counts
                while True:
                    this_type = r.randint(1, len(c_classes))
                    
                    this_type = c_classes[this_type - 1]

                    with THREAD_LOCK:                    
                        if c_class_counts[this_type] <= 0:
                            continue
                    break
                customer = generate_customer(this_type, state=this_state)
                with THREAD_LOCK:
                    self.customers.append(customer)
                    cdist[this_state] -= 1
                    c_class_counts[this_type] -= 1
                pbar.update(1)
            
        r.shuffle(self.customers)
        for idx, customer in enumerate(self.customers):
            customer['id'] = idx + 1

        print(f"{len(self.customers)} customers generated successfully.")
        self.state['last_phase'] = 2
        self.export("02-customers-generated.pkl")

        # Total of all hotel rooms
        total_room_count = sum([sum(hotel['rooms'].values()) for hotel in self.hotels])
        print(f"There are a total of {total_room_count} rooms across all hotels generated.")

        print("Preparing for simulation...")
        self.prepare_simulation()

    def prepare_simulation(self):
        """Prepare the generated data for simulation use.

        This involves precomputing certain data structures to make simulation runs faster.
        """
        
        self.state['rooms'] = {}
        # Populate room matrix per hotel
        for hotel in self.hotels:
            room_matrix = {}
            for room_type, count in hotel['rooms'].items():
                room_matrix[room_type] = [None] * count
            self.state['rooms'][hotel['id']] = room_matrix
        
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
    all_multipliers = sum(list(PARAMS['state_population_ratios'].values()))

    # 2. Compute the scaling factor
    scaling_factor = count / all_multipliers

    # 3. Generate baseline distribution
    if sd <= 0.0:
        distribution = {
            state: int(round(multiplier * scaling_factor))
            for state, multiplier in PARAMS['state_population_ratios'].items()
        }
    else:
        distribution = {
            state: int(round(multiplier * rand(scaling_factor, sd, min_val=0.0)))
            for state, multiplier in PARAMS['state_population_ratios'].items()
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

def generate_hotel(hotel_type: str, state: str = "MN", tourist_region: str = "") -> dict:
    """Generate a single random hotel.

    Args:
        hotel_type (str): The type of hotel to generate. Must be one of the keys in PARAMS["hotel_types"].
        state (str, optional): The US state code to generate the hotel in. Defaults to "MN".
        tourist_region (str, optional): The tourist region to generate the hotel in. Defaults to "". If set, supersedes 'state'.

    Returns:
        dict: A dictionary containing the generated hotel's details.
"""

    # The hotel type must be a valid type - generally "resort", "hotel", or "motel"
    try:
        hotel_type_obj = PARAMS["hotel_types"][hotel_type]
    except KeyError:
        raise ValueError(f"Invalid hotel type: {hotel_type}")

    ### --- HOTEL NAME, LOCATION, CONTACT INFO --- ###

    # Determine how we should select city/state/zip
    if tourist_region:
        # Region takes precedence - if given, state is ignored.
        if tourist_region not in PARAMS['tourist_regions']:
            raise ValueError(f"Invalid region: {tourist_region}")
        if 'zip_prefixes' not in PARAMS['tourist_regions'][tourist_region]:
            # There must be a state defined.
            if "main_state" not in PARAMS['tourist_regions'][tourist_region]:
                raise ValueError(f"Region {tourist_region} must define either 'zip_prefixes' or 'main_state'")
            state = PARAMS['tourist_regions'][tourist_region]['main_state']
            zc = r.choice(list(ZIPCODES[state].keys()))
            csz = (ZIPCODES[state][zc], state.upper(), zc)
        else:
            possible_prefixes = PARAMS['tourist_regions'][tourist_region]['zip_prefixes']
            #print(possible_prefixes)
            this_prefix = r.choice(possible_prefixes)
            #print(this_prefix)
            possible_zipcodes = [zc for zc, state in ZIPCODES_FLAT.items() if zc.startswith(this_prefix)]
            #print(possible_zipcodes)
            zc = r.choice(possible_zipcodes)
            state = ZIPCODES_FLAT[zc]
            csz = (ZIPCODES[state][zc], state.upper(), zc)
    else:
        if state:
            # If state was given, use that
            try:
                zc = r.choice(list(ZIPCODES[state].keys()))
                csz = (ZIPCODES[state][zc], state.upper(), zc)
            except KeyError:
                raise ValueError(f"Invalid state code: {state}")
        else:
            # Totally random zipcode
            zc = r.choice(list(ZIPCODES[state].keys()))
            csz = (ZIPCODES[state][zc], state.upper(), zc)

    # Select the adjective and verb for this hotel's name
    hotel_name_parts = [
        random.choice(ADJS),
        random.choice(NOUNS),
    ]

    # Hotel name generation
    hotel_name_fmt = random.choice(HOTEL_NAME_TEMPLATES)
    hotel_name = hotel_name_fmt.format(
        adj=hotel_name_parts[0],
        noun=hotel_name_parts[1],
        type=hotel_type_obj['name'],
        loc=csz[0])

    # Handle things that the hotel name didn't use so they won't appear in the generated domain
    if "{adj}" not in hotel_name_fmt:
        hotel_name_parts[0]=""
    if "{type}" not in hotel_name_fmt:
        hotel_type_str=""
    else:
        hotel_type_str=hotel_type_obj['name']

    # Domain generation works by reusing parts of the hotel name and lowercasing them
    # while removing all spaces and non-domain-valid chars
    _domain = random.choice(HOTEL_DOMAIN_TEMPLATES).format(
        adj=hotel_name_parts[0].lower(),
        noun=hotel_name_parts[1].lower(),
        type=hotel_type_str.lower(),
        loc=csz[0].replace(" ","").lower()
    ) + random.choice(HOTEL_DOMAIN_TLDS)
    _domain = _domain.replace("--","-").replace("..",".").replace(" ","")

    # Email is one of the random Email addresses at the generated domain
    email = f"{random.choice(EMAILS)}@{_domain}"

    # Website is the domain, sometimes with www., sometimes with a URL stem
    website = f"https://{'www.' if r.random() < 0.25 else ''}{_domain}{'/' + random.choice(URL_STEMS) if r.random() < 0.1 else ''}"

    ### --- ROOM ASSIGNMENTS --- ###

    # Determine the number of rooms and room types.
    # First, are we a resort in a resort region?
    if tourist_region and hotel_type_obj['name'].lower() == "resort":
        room_count_data = PARAMS['tourist_regions'][tourist_region].get('rooms', {}).get('total_rooms', {})
        if len(room_count_data) == 0:
            # Fallback
            room_count_mean = 2000
            room_count_sd = 500
            room_count_min = 1000
            room_count_max = 4000
        else:
            room_count_mean = room_count_data.get('mean', 2000)
            room_count_sd = room_count_data.get('sd', 500)
            room_count_min = room_count_data.get('min', 1000)
            room_count_max = room_count_data.get('max', 4000)
        room_count = rand(room_count_mean, room_count_sd, min_val=room_count_min, max_val=room_count_max)

    else:
        # Select based on the hotel type
        room_count_data = hotel_type_obj.get('rooms', {}).get('total_rooms', {})
        if len(room_count_data) == 0:
            # Fallback
            room_count_mean = 150
            room_count_sd = 50
            room_count_min = 50
            room_count_max = 300
        else:
            room_count_mean = room_count_data.get('mean', 150)
            room_count_sd = room_count_data.get('sd', 50)
            room_count_min = room_count_data.get('min', 50)
            room_count_max = room_count_data.get('max', 300)
        room_count = rand(room_count_mean, room_count_sd, min_val=room_count_min, max_val=room_count_max)
    
    # Ok, now figure out the distribution of rooms
    room_dist_data = hotel_type_obj.get('rooms', {}).get('distribution', {})
    room_distribution = {}
    for room_type in room_dist_data.keys():
        m = room_dist_data[room_type].get('mean', 0.5)
        sd = room_dist_data[room_type].get('sd', 0.1)
        prob = rand(m, sd, min_val=0.0, max_val=1.0)
        room_distribution[room_type] = int(round(prob * room_count))
        
    # Ensure we have exactly room_count items; if not, add or remove from random types
    while sum(room_distribution.values()) < room_count:
        rt = r.choice(list(room_distribution.keys()))
        room_distribution[rt] += 1
    while sum(room_distribution.values()) > room_count:
        rt = r.choice(list(room_distribution.keys()))
        if room_distribution[rt] > 0:
            room_distribution[rt] -= 1
    
    # Now we know the room distribution

    ### --- PRICING --- ###

    # Determine hotel base price
    # If we are doing a resort, get its multiplier
    base_price = hotel_type_obj.get('base_price', {}).get("mean", 79.00)
    base_price_sd = hotel_type_obj.get('base_price', {}).get("sd", 5.00)
    base_price = rand(base_price, base_price_sd, min_val=40.00)

    if tourist_region and hotel_type_obj['name'].lower() == "resort":
        price_multiplier_m = PARAMS['tourist_regions'][tourist_region].get('multiplier', {}).get('mean', 1.5)
        price_multiplier_sd = PARAMS['tourist_regions'][tourist_region].get('multiplier', {}).get('sd', 0.15)
        price_multiplier = rand(price_multiplier_m, price_multiplier_sd, min_val=0.5)
    else:
        # Get state multiplier
        state_multiplier_m = PARAMS['state_price_multipliers'].get(state.upper(), {}).get('mean', 1.0)
        state_multiplier_sd = PARAMS['state_price_multipliers'].get(state.upper(), {}).get('sd', 0.0)
        price_multiplier = rand(state_multiplier_m, state_multiplier_sd, min_val=0.5)
    
    base_price = base_price * price_multiplier

    # If we have a resort fee, determine what it will be
    if tourist_region and hotel_type_obj['name'].lower() == "resort":
        resort_fee_data = PARAMS['tourist_regions'][tourist_region].get('resort_fee', {})
        if len(resort_fee_data) == 0:
            resort_fee_mean = 30.00
            resort_fee_sd = 5.00
            resort_fee_probability = 0.8
        else:
            resort_fee_mean = resort_fee_data.get('mean', 30.00)
            resort_fee_sd = resort_fee_data.get('sd', 5.00)
            resort_fee_probability = resort_fee_data.get('probability', 0.8)
        if r.random() < resort_fee_probability:
            resort_fee = rand(resort_fee_mean, resort_fee_sd, min_val=5.00)
        else:
            resort_fee = 0.0

    # Final response assembly
    response = {
        "name": hotel_name,
        "street": f"{generate_street_number()} {f.street_name()}",
        "city": csz[0],
        "state": csz[1],
        "zip": csz[2],
        "email": email,
        "website": website,
        "phone": generate_us_phone(),
        "type": hotel_type_obj['name'],
        "tourist_region": tourist_region or None,
        "rooms": room_distribution,
        "base_price": base_price,
        "resort_fee": resort_fee if tourist_region and hotel_type_obj['name'].lower() == "resort" else 0.0
    }

    return response

def generate_customer(customer_type: str, state: str = "MN") -> dict:
    """Generate a single random customer.

    Args:
        customer_type (str): The type of customer to generate. Must be one of the keys in PARAMS["hotel_types"].
        state (str, optional): The US state code to generate the customer in. Defaults to "MN".

    Returns:
        dict: A dictionary containing the generated customer's details.
"""

    # The customer type must be a valid type - default from "rare_leisure", "regular_leisure", "business", "corporate", "road_warrior"
    try:
        customer_type_obj = PARAMS["customer_archetypes"][customer_type]
    except KeyError:
        raise ValueError(f"Invalid customer type: {customer_type}")

    ### --- CUSTOMER NAME, LOCATION, CONTACT INFO --- ###

    # Determine how we should select city/state/zip
    if state:
        # If state was given, use that
        try:
            zc = r.choice(list(ZIPCODES[state].keys()))
            csz = (ZIPCODES[state][zc], state.upper(), zc)
        except KeyError:
            raise ValueError(f"Invalid state code: {state}")
    else:
        # Totally random zipcode
        zc = r.choice(list(ZIPCODES[state].keys()))
        csz = (ZIPCODES[state][zc], state.upper(), zc)

    fname = f.first_name()
    lname = f.last_name()
    email_parts = {
        "fname": fname,
        "lname": lname,
        "f_initial": fname[0],
        "l_initial": lname[0],
        "year": str(r.randrange(70, 2030)).zfill(2),
        "domain": random.choice(PARAMS['customer_email_domains'])
    }
    # Email is one of the random Email addresses at the generated domain
    email_fmt = random.choice(list(CUSTOMER_EMAIL_TEMPLATES))
    email = email_fmt.format(**email_parts).lower()

    # Final response assembly
    response = {
        "fname": fname,
        "lname": lname,
        "street": f"{generate_street_number()} {f.street_name()}",
        "city": csz[0],
        "state": csz[1],
        "zip": csz[2],
        "email": email,
        "phone": generate_us_phone(),
        "type": customer_type,
    }

    return response

def render_hotel_address(hotel: dict) -> str:
    return f"{hotel['name']}\n{hotel['street']}\n{hotel['city']}, {hotel['state']} {hotel['zip']}\nEmail: {hotel['email']}\nWebsite: {hotel['website']}\nPhone: {hotel['phone']}"

def generate_us_phone():
    # Valid US area codes don't start with 0 or 1
    # Exchange codes (middle 3) also don't start with 0 or 1
    area_code = r.randint(200, 999)
    exchange = r.randint(200, 999)
    subscriber = r.randint(0, 9999)
    return f"{area_code}-{exchange}-{subscriber:04d}"

def generate_street_number():
    street_range = r.randrange(0, 3)
    if street_range == 0:
        street = r.randrange(1,10)
    elif street_range == 1:
        street = r.randrange(10,100)
    else:
        street = r.randrange(100,10000)
    return street

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