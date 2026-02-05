import json
import os

from yaml import safe_load

_data = safe_load(open(os.path.dirname(__file__) + "/parameters.yaml","r"))

_data['nouns'] = open(os.path.dirname(__file__) + "/noun.txt","r").read().splitlines()
_data['adjs'] = open(os.path.dirname(__file__) + "/adj.txt","r").read().splitlines()
_data['zipcodes'] = json.load(open(os.path.dirname(__file__) + "/zipcodes.json","r"))
_data['zipcodes_flat'] = {zc: state_code for state_code, zc_dict in _data['zipcodes'].items() for zc, city in zc_dict.items()}

# Make all keys of _data available as attributes on this module (e.g. '_data['states'] -> xl9045qi.hotelgen.data.states')
for key, value in _data.items():
    globals()[key] = value

def render_hotel_address(hotel) -> str:
    """Render a hotel's address as a formatted string."""
    return f"{hotel.name}\n{hotel.street}\n{hotel.city}, {hotel.state} {hotel.zip}\nEmail: {hotel.email}\nWebsite: {hotel.website}\nPhone: {hotel.phone}"
