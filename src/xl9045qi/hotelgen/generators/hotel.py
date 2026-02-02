# Generates individual hotel records

from xl9045qi.hotelgen import data
from xl9045qi.hotelgen import normalized_random_bounded as rand
from xl9045qi.hotelgen.generators import generate_street_number, generate_us_phone, r, f
from xl9045qi.hotelgen.models import Hotel, RoomInfo

def generate_hotel(hotel_type: str, state: str = "MN", tourist_region: str = "") -> dict:
    """Generate a single random hotel.

    Args:
        hotel_type (str): The type of hotel to generate. Must be one of the keys in data.hotel_types.
        state (str, optional): The US state code to generate the hotel in. Defaults to "MN".
        tourist_region (str, optional): The tourist region to generate the hotel in. Defaults to "". If set, supersedes 'state'.

    Returns:
        dict: A dictionary containing the generated hotel's details.
"""

    # The hotel type must be a valid type - generally "resort", "hotel", or "motel"
    try:
        hotel_type_obj = data.hotel_types[hotel_type]
    except KeyError:
        raise ValueError(f"Invalid hotel type: {hotel_type}")

    ### --- HOTEL NAME, LOCATION, CONTACT INFO --- ###

    # Determine how we should select city/state/zip
    if tourist_region:
        # Region takes precedence - if given, state is ignored.
        if tourist_region not in data.tourist_regions:
            raise ValueError(f"Invalid region: {tourist_region}")
        if 'zip_prefixes' not in data.tourist_regions[tourist_region]:
            # There must be a state defined.
            if "main_state" not in data.tourist_regions[tourist_region]:
                raise ValueError(f"Region {tourist_region} must define either 'zip_prefixes' or 'main_state'")
            state = data.tourist_regions[tourist_region]['main_state']
            zc = r.choice(list(data.zipcodes[state].keys()))
            csz = (data.zipcodes[state][zc], state.upper(), zc)
        else:
            possible_prefixes = data.tourist_regions[tourist_region]['zip_prefixes']
            #print(possible_prefixes)
            this_prefix = r.choice(possible_prefixes)
            #print(this_prefix)
            possible_zipcodes = [zc for zc, state in data.zipcodes_flat.items() if zc.startswith(this_prefix)]
            #print(possible_zipcodes)
            zc = r.choice(possible_zipcodes)
            state = data.zipcodes_flat[zc]
            csz = (data.zipcodes[state][zc], state.upper(), zc)
    else:
        if state:
            # If state was given, use that
            try:
                zc = r.choice(list(data.zipcodes[state].keys()))
                csz = (data.zipcodes[state][zc], state.upper(), zc)
            except KeyError:
                raise ValueError(f"Invalid state code: {state}")
        else:
            # Totally random zipcode
            zc = r.choice(list(data.zipcodes[state].keys()))
            csz = (data.zipcodes[state][zc], state.upper(), zc)

    # Select the adjective and verb for this hotel's name
    hotel_name_parts = [
        r.choice(data.adjs),
        r.choice(data.nouns),
    ]

    # Hotel name generation
    hotel_name_fmt = r.choice(data.misc['hotel_name_templates'])
    
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
    _domain = r.choice(data.misc['hotel_name_templates']).format(
        adj=hotel_name_parts[0].lower(),
        noun=hotel_name_parts[1].lower(),
        type=hotel_type_str.lower(),
        loc=csz[0].replace(" ","").lower()
    ) + r.choice(data.misc['hotel_domain_tlds'])
    _domain = _domain.replace("--","-").replace("..",".").replace(" ","")

    # Email is one of the random Email addresses at the generated domain
    email = f"{r.choice(data.misc['email_users'])}@{_domain}"
    # Website is the domain, sometimes with www., sometimes with a URL stem
    website = f"https://{'www.' if r.random() < 0.25 else ''}{_domain}{'/' + r.choice(data.misc['url_stems']) if r.random() < 0.1 else ''}"

    ### --- ROOM ASSIGNMENTS --- ###

    # Determine the number of rooms and room types.
    # First, are we a resort in a resort region?
    if tourist_region and hotel_type_obj['name'].lower() == "resort":
        room_count_data = data.tourist_regions[tourist_region].get('rooms', {}).get('total_rooms', {})
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
        price_multiplier_m = data.tourist_regions[tourist_region].get('multiplier', {}).get('mean', 1.5)
        price_multiplier_sd = data.tourist_regions[tourist_region].get('multiplier', {}).get('sd', 0.15)
        price_multiplier = rand(price_multiplier_m, price_multiplier_sd, min_val=0.5)
    else:
        # Get state multiplier
        state_multiplier_m = data.state_data.get(state.upper(), {}).get('price_multipliers', {}).get('mean', 1.0)
        state_multiplier_sd = data.state_data.get(state.upper(), {}).get('price_multipliers', {}).get('sd', 0.0)
        price_multiplier = rand(state_multiplier_m, state_multiplier_sd, min_val=0.5)
    
    base_price = base_price * price_multiplier

    # For each room type, figure out its actual cost.
    for room_type in list(room_distribution.keys()):
        room_type_obj = data.room_types.get(room_type, {})
        room_type_multiplier = room_type_obj.get('price_multiplier', {}).get('mean', 1)
        room_type_multiplier_sd = room_type_obj.get('price_multiplier', {}).get('sd', 0.0)
        room_type_multiplier_val = rand(room_type_multiplier, room_type_multiplier_sd, min_val=0.5)
        # Store the final price for this room type as RoomInfo
        room_distribution[room_type] = RoomInfo(
            count=room_distribution[room_type],
            price=round(base_price * room_type_multiplier_val, 2)
        )

    # If we have a resort fee, determine what it will be
    if tourist_region and hotel_type_obj['name'].lower() == "resort":
        resort_fee_data = data.tourist_regions[tourist_region].get('resort_fee', {})
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
    return Hotel(
        name=hotel_name,
        street=f"{generate_street_number()} {f.street_name()}",
        city=csz[0],
        state=csz[1],
        zip=csz[2],
        email=email,
        website=website,
        phone=generate_us_phone(),
        type=hotel_type_obj['name'],
        tourist_region=tourist_region or None,
        rooms=room_distribution,
        base_price=base_price,
        resort_fee=resort_fee if tourist_region and hotel_type_obj['name'].lower() == "resort" else 0.0
    )
