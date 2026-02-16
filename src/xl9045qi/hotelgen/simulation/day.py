import datetime
from xl9045qi.hotelgen import data
from xl9045qi.hotelgen import log_scaled_value as lsv
from xl9045qi.hotelgen import normalized_random_bounded as rand
from xl9045qi.hotelgen.generators import generate_stay_length, r
from rich import print

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from xl9045qi.hotelgen.simulation import HGSimulationState

def get_datetime_by_day_num(inst: HGSimulationState, day_num: int) -> datetime.datetime:
    """Get the datetime object for a given day number in the simulation."""
    start_date = datetime.datetime.strptime(inst.job['generation']['dates']['start'], '%Y-%m-%d')
    return start_date + datetime.timedelta(days=day_num)

def select_room_type(inst: HGSimulationState, hotel_id: int):
    """Select a room type based on current occupation of rooms and total room counts"""

    # First, get this hotel's total room counts
    hotel = inst.state['cache']['hotels_by_id'][hotel_id]
    room_type_counts = {
        rt: hotel.rooms[rt].count
        for rt in hotel.rooms.keys()
    }

    # Now we have to figure out how many of each type of room is occupied
    all_rooms_occupied = inst.state['occupied_rooms'].get(hotel_id, {})
    # all_rooms_occupied is now a dict of lists.
    # Collapse all lists into a single list
    all_rooms_occupied = [b for b in all_rooms_occupied.values()]
    all_rooms_occupied = [item for sublist in all_rooms_occupied for item in sublist]

    # Each room occupied object consists of a tuple of (customer_id, checkout_date, stay_length, room_type_str)
    # The room occupied list is *flat* (not keyed by room type!) so we must key on index 3 of each tuple's data.
    # Get the *sum* (total count) of each room type occupied
    for room in all_rooms_occupied:
        rt = room[3]
        room_type_counts[rt] -= 1

    # If NO rooms are available, return None.
    if sum(room_type_counts.values()) <= 0:
        return None

    # For any room type is not available, remove it from the selection pool
    for rt in list(room_type_counts.keys()):
        if room_type_counts[rt] <= 0:
            del room_type_counts[rt]

    # Finally, select a random room from the remaining available types
    return r.choice(list(room_type_counts.keys()))

def get_customer_distribution(desired_count: int):

    # First, we need to figure out the right distribution for the customer and scale
    # the desired_count accordingly
    expected_counts = {
        k: v['percentage'] * desired_count
        for k, v in data.customer_archetypes.items()
    }

    while sum(expected_counts.values()) < desired_count:
        # Randomly add one to each archetype until the desired_count is reached
        incre = r.choice(list(expected_counts.keys()))
        expected_counts[incre] += 1
    while sum(expected_counts.values()) > desired_count:
        decre = r.choice(list(expected_counts.keys()))
        if expected_counts[decre] > 0:
            expected_counts[decre] -= 1

    # Round all counts
    for k in expected_counts.keys():
        expected_counts[k] = int(round(expected_counts[k]))

    return expected_counts

def process_day(inst: HGSimulationState):
    """Process a single day of simulation.

    Remarks:
        This will run one day's worth of simulation and update all of the local
        state.
    """

    if inst.state.get("last_phase", -1) < 3:
        print("[bold red]ERROR: Cannot process day before completing Phase 3.")
        return

    # Set the initial day number, or advance it
    if 'current_day_num' not in inst.state:
        inst.state['current_day_num'] = 1
    else:
        inst.state['current_day_num'] += 1

    # Advance the datetime object too
    inst.state['current_day'] += datetime.timedelta(days=1)
    day = inst.state['current_day_num']

    checkin_count = 0
    checkout_count = 0
    reactivate_count = 0

    # Step 1. Scan for any hotels that have checkouts today.
    # If found, introduce a financial transaction recording the checkout.
    # Use filtering instead of individual .remove() calls (O(n) vs O(n²))

    for hotel_id in inst.state['occupied_rooms'].keys():
        for rt in list(inst.state['occupied_rooms'][hotel_id].keys()):
            old_bookings = inst.state['occupied_rooms'][hotel_id][rt]
            # Separate into checkouts and remaining
            to_checkout = [
                b for b in old_bookings
                if get_datetime_by_day_num(inst, b[1]) <= inst.state['current_day']
            ]
            inst.state['occupied_rooms'][hotel_id][rt] = [
                b for b in old_bookings
                if get_datetime_by_day_num(inst, b[1]) > inst.state['current_day']
            ]
            # Process checkouts (room already removed from list)
            for booking in to_checkout:
                inst.checkout_finalize(hotel_id, booking)
                checkout_count += 1

    # Step 2: Determine if any customers are now available and should be removed
    # from occupied customers.

    # Occupied customers contains customer type as keys; each value is a list of tuples of (customer_id, hotel_id, available_date)
    # Use list comprehension instead of individual .remove() calls (O(n) vs O(n²))
    for cust_type in inst.state['occupied_customers'].keys():
        old_list = inst.state['occupied_customers'][cust_type]
        inst.state['occupied_customers'][cust_type] = [
            occ_cust for occ_cust in old_list
            if occ_cust[2] > inst.state['current_day']
        ]
        reactivate_count += len(old_list) - len(inst.state['occupied_customers'][cust_type])

    # Step 3: Determine today's occupancy percentage.
    ramp_up_days = inst.job['generation'].get('ramp_up_days', 45)
    target_occupancy = inst.job['generation'].get('target_occupancy', 0.3)
    ramp_factor = lsv(day, 0, ramp_up_days, -0.4) / float(ramp_up_days)  # 0 to 1
    today_occupancy = ramp_factor * target_occupancy
    # Add minor variance (SD is relative to the occupancy, e.g., 0.05 = 5% variance)
    today_occupancy = rand(
        today_occupancy,
        today_occupancy * inst.job['generation'].get('target_occupancy_sd', 0.05),
        min_val=0.0,
        max_val=0.5
    )

    #print("Today's occupancy: {:.2f}%".format(today_occupancy * 100))

    # Step 4: For each hotel, determine how many rooms to fill today.
    hotel_desired_occupancy = {}
    for hotel in inst.state['hotels']:
        hotel_desired_occupancy[hotel.id] = int(round(sum([room_info.count for room_info in hotel.rooms.values()]) * today_occupancy))

    total_customers_needed = sum(hotel_desired_occupancy.values())
    #print(f"Day {day}: Need {total_customers_needed} customers.")
    customer_counts = get_customer_distribution(total_customers_needed)
    if total_customers_needed <= 0:
        return

    # Build set of all checked-in customer IDs ONCE (O(1) lookup instead of O(n))
    all_checked_in_ids = set(
        booking[0]  # customer_id
        for hid in inst.state['occupied_rooms'].keys()
        for rt in inst.state['occupied_rooms'][hid].keys()
        for booking in inst.state['occupied_rooms'][hid][rt]
    )

    # For each group of customers, first extract out all IDs of all customers
    for ct in customer_counts.keys():
        all_customers_in_grp = inst.state['cache']['customers_by_archetype'][ct]

        # Remove all checked in ids from the all_customers_in_grp list (O(1) per lookup)
        all_customers_in_grp = [
            cid
            for cid in all_customers_in_grp
            if cid not in all_checked_in_ids
        ]

        # We also need to remove any customer who appears in the occupied customers list.
        # Use set for O(1) lookup
        occupied_customer_ids = set(
            cust[0]
            for cust in inst.state['occupied_customers'].get(ct, [])
        )
        all_customers_in_grp = [
            cid
            for cid in all_customers_in_grp
            if cid not in occupied_customer_ids
        ]

        # Do we have enough free customers?
        if len(all_customers_in_grp) <= customer_counts[ct]:
            # Not enough customers, just use 20% of what's available
            customer_counts[ct] = int(round(len(all_customers_in_grp) * 0.2))
        # Now, select the customers
        customer_ids = r.sample(all_customers_in_grp, customer_counts[ct])
        customer_counts[ct] = customer_ids  # Replace count with list of IDs

    # Now collapse the list of customer IDs into a flat random list
    all_customer_ids = []
    for ct in customer_counts.keys():
        all_customer_ids.extend(customer_counts[ct])

    # Iterate each hotel and check in some users
    for hotel in hotel_desired_occupancy.keys():
        if hotel_desired_occupancy[hotel] <= 0:
            continue
        # How many people are *currently* checked in?
        currently_checked_in = sum([
            len(inst.state['occupied_rooms'][hotel][rt])
            for rt in inst.state['occupied_rooms'][hotel].keys()
        ])
        # How many more do we need?
        needed = hotel_desired_occupancy[hotel] - currently_checked_in
        if needed > 0:
            r.shuffle(all_customer_ids)
            for _ in range(needed):
                # Check in the user
                try:
                    this_cid = all_customer_ids.pop()
                except IndexError:
                    # No more customers. Continue
                    continue
                customer_type = inst.state['cache']['customers_by_id'][this_cid].type
                customer_archetype = data.customer_archetypes[customer_type]
                customer_archetype_weights = customer_archetype['stay_duration_weights']
                stay_length = generate_stay_length(customer_archetype_weights)

                # Select room type
                rt = select_room_type(inst, hotel)
                if rt is None:
                    # No rooms available - skip.
                    continue

                inst.checkin(this_cid, hotel, rt, stay_length)
                checkin_count += 1

    print(f"Day {day} complete: {checkin_count} c-in, {checkout_count} c-out, {reactivate_count} react, {today_occupancy * 100:.2f}% occ")

    if 'day_log' not in inst.state:
        inst.state['day_log'] = []

    inst.state['day_log'].append({
        'day_num': day,
        'date': inst.state['current_day'].strftime('%Y-%m-%d'),
        'checkins': checkin_count,
        'checkouts': checkout_count,
        'reactivations': reactivate_count,
        'occupancy': today_occupancy,
    })

    return


