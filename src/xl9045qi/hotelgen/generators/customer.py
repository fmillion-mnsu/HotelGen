# Generates individual customer records

from xl9045qi.hotelgen import data
from xl9045qi.hotelgen.generators import r, generate_street_number, generate_us_phone
from xl9045qi.hotelgen.generators import get_first_name, get_last_name, get_street_name

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from xl9045qi.hotelgen.simulation import HGSimulationState


def init_customer_cache(inst: 'HGSimulationState'):
    """Initialize customer generation caches in inst.state['cache']."""
    inst.state['cache']['zipcode_lists_by_state'] = {
        state: list(zips.keys())
        for state, zips in data.zipcodes.items()
    }
    inst.state['cache']['email_templates'] = list(data.misc['customer_email_templates'])
    inst.state['cache']['email_domains'] = data.customer_email_domains


def generate_customer(inst: 'HGSimulationState', customer_type: str, state: str = "MN") -> dict:
    """Generate a single random customer.

    Args:
        customer_type (str): The type of customer to generate. Must be one of the keys in ["hotel_types"].
        state (str, optional): The US state code to generate the customer in. Defaults to "MN".

    Returns:
        dict: A dictionary containing the generated customer's details.
"""

    # The customer type must be a valid type - default from "rare_leisure", "regular_leisure", "business", "corporate", "road_warrior"
    try:
        customer_type_obj = data.customer_archetypes[customer_type]
    except KeyError:
        raise ValueError(f"Invalid customer type: {customer_type}")

    ### --- CUSTOMER NAME, LOCATION, CONTACT INFO --- ###

    # Get cached lists from inst.state['cache']
    cache = inst.state['cache']

    # Determine how we should select city/state/zip (use cached list)
    if state:
        try:
            zc = r.choice(cache['zipcode_lists_by_state'][state])
            csz = (data.zipcodes[state][zc], state.upper(), zc)
        except KeyError:
            raise ValueError(f"Invalid state code: {state}")
    else:
        zc = r.choice(cache['zipcode_lists_by_state'][state])
        csz = (data.zipcodes[state][zc], state.upper(), zc)

    # Use pre-generated name pools instead of slow Faker calls
    fname = get_first_name()
    lname = get_last_name()
    email_parts = {
        "fname": fname,
        "lname": lname,
        "f_initial": fname[0],
        "l_initial": lname[0],
        "year": str(r.randrange(70, 2030)).zfill(2),
        "domain": r.choice(cache['email_domains'])
    }
    # Email is one of the random Email addresses at the generated domain
    email_fmt = r.choice(cache['email_templates'])
    email = email_fmt.format(**email_parts).lower()

    # Final response assembly
    response = {
        "fname": fname,
        "lname": lname,
        "street": f"{generate_street_number()} {get_street_name()}",
        "city": csz[0],
        "state": csz[1],
        "zip": csz[2],
        "email": email,
        "phone": generate_us_phone(),
        "type": customer_type,
    }

    return response
