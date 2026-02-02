# Generates individual customer records

from xl9045qi.hotelgen import data
from xl9045qi.hotelgen.generators import f, r, generate_street_number, generate_us_phone

def generate_customer(customer_type: str, state: str = "MN") -> dict:
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

    # Determine how we should select city/state/zip
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

    fname = f.first_name()
    lname = f.last_name()
    email_parts = {
        "fname": fname,
        "lname": lname,
        "f_initial": fname[0],
        "l_initial": lname[0],
        "year": str(r.randrange(70, 2030)).zfill(2),
        "domain": r.choice(data.customer_email_domains)
    }
    # Email is one of the random Email addresses at the generated domain
    email_fmt = r.choice(list(data.misc['customer_email_templates']))
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
