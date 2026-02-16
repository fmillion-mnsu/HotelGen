import datetime
import random

import tqdm
from rich import print

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from xl9045qi.hotelgen.simulation import HGSimulationState

import xl9045qi.hotelgen.simulation as sim
from xl9045qi.hotelgen.generators import giftshop
from xl9045qi.hotelgen.generators.transaction import generate_retail_transaction

def phase5(inst: HGSimulationState) -> bool:
    """Phase 5: Generate gift shops and products"""
    
    if inst.state.get("last_phase", -1) >= 5:
        print("[bold]Phase 5 already completed, skipping.")
        return False

    # Get the number of dats in the generation range, and find the midpoint
    # as number of days from the start
    days_in_range = \
        (datetime.datetime.strptime(inst.job['generation']['dates']['end'], "%Y-%m-%d") - \
        datetime.datetime.strptime(inst.job['generation']['dates']['start'], "%Y-%m-%d")).days
    midpoint_days = int(days_in_range / 2)

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
    all_active = active_resorts + active_hotels

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

        # Assign ID to the gift shop first (needed for product references)
        this_gs[0].id = len(inst.state['giftshops'])

        # Assign IDs to products and set their store location
        for idx, product in enumerate(this_gs[1]):
            product.sold_at = this_gs[0].id  # Use gift shop ID, not hotel ID
            product.id = len(inst.state['products']) + idx

        # Set opening dates for each store
        # All stores should be opened by halfway through the date range.
        day_curve = (random.random() * 0.5) ** 3
        days_since_start = day_curve * midpoint_days
        start_date = datetime.datetime.strptime(inst.job['generation']['dates']['start'], "%Y-%m-%d") + datetime.timedelta(days=days_since_start)
        this_gs[0].date_opened = start_date

        inst.state['giftshops'].append(this_gs[0])
        inst.state['products'].extend(this_gs[1])
    
    print(f"Generated {len(inst.state['giftshops'])} gift shops and {len(inst.state['products'])} products.")
    
    # Now, we need to iterate over events to determine which events involve
    # people checking into each hotel.

    hotel_ids = [h.id for h in all_active]

    customers_stayed = [
        c for c in inst.state['events']
        if c['event'] == 'checkin'
        and c['property_id'] in hotel_ids
    ]
    # Filter down so that any event that occurred at a hotel where its
    # store isn't open yet is removed.
    # Store opening date is in GiftShop.date_opened. The hotel ID associated
    #  with the store is in GiftShop.
    candidates = [
        x for x in customers_stayed
        if any(
            x['checkin_date'] >= g.date_opened
            for g in inst.state['giftshops']
            if g.located_at == x['property_id']
        )
    ]

    # Sample and randomize the list
    candidates = random.sample(candidates, int(len(candidates) * (1/3)))

    print(f"There are {len(candidates)} candidates for transactions.")
    
    # Generate transactions
    transactions = [generate_retail_transaction(inst, hotel_id=c['property_id'], date=c['checkin_date'].date(), customer_id=c['customer_id']) for c in tqdm.tqdm(candidates,desc="Generate gift shop transactions")]
    transactions = [x for x in transactions if x is not None]

    inst.state.setdefault("retail_transactions",[]).extend(transactions)
    print(f"Generated {len(transactions)} retail transactions.")

    random.shuffle(inst.state['retail_transactions'])

    inst.state['last_phase'] = 5

    return True