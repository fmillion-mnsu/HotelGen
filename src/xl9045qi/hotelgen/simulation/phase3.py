import datetime

from xl9045qi.hotelgen import data
from rich import print

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from xl9045qi.hotelgen.simulation import HGSimulationState

def phase3(inst: HGSimulationState) -> bool:
    """Phase 3 of HotelGen.
    
    Prepare the generated data for simulation use.

    This involves precomputing certain data structures to make simulation runs faster.
    """

    if inst.state.get("last_phase", -1) >= 3:
        print("[bold]Phase 3 already completed, skipping.")
        return False

    # First, we need a simple dict consisting of
    #   key: dict
    # with key = room type, value = empty list.
    inst.state['occupied_rooms'] = {
        hotel.id: {room_type: [] for room_type in hotel.rooms.keys()}
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
    if 'cache' not in inst.state:
        inst.state['cache'] = {}
    inst.state['cache']['customers_by_archetype'] = {}
    for archetype in data.customer_archetypes.keys():
        inst.state['cache']['customers_by_archetype'][archetype] = [
            customer.id
            for customer in inst.state['customers']
            if customer.type == archetype
        ]

    # All customers by ID
    inst.state['cache']['customers_by_id'] = {
        customer.id: customer
        for customer in inst.state['customers']
    }

    # All hotels by ID
    inst.state['cache']['hotels_by_id'] = {
        hotel.id: hotel
        for hotel in inst.state['hotels']
    }

    # Prepare the current day state
    inst.state['current_day'] = datetime.datetime.strptime(inst.job['generation']['dates']['start'], "%Y-%m-%d")
    end_day = datetime.datetime.strptime(inst.job['generation']['dates']['end'], "%Y-%m-%d")
    inst.state['days_left'] = (end_day - inst.state['current_day']).days + 1

    # Will hold transaction events.
    # Transactions will be stored as dicts and normalized when database insert is
    # performed.

    print(f"Preparation ready. Will generate {inst.state['days_left']} days of simulated transactions.")

    inst.state['last_phase'] = 3

    return True