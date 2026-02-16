 # Migrate pickles to newer versions

from dataclasses import dataclass, field, is_dataclass
from datetime import datetime
from typing import Optional

import argparse
import pickle
import os.path
import sys

import xl9045qi.hotelgen.models as models

import tqdm

# Legacy Classes
@dataclass
class LegacyRoomInfo:
    """Information about a room type in a hotel."""
    count: int
    price: float

@dataclass
class LegacyCustomer:
    """A customer record."""
    fname: str
    lname: str
    street: str
    city: str
    state: str  # 2 char max
    zip: str  # 10 char max
    email: str
    phone: str  # 12 char max
    type: str  # customer archetype: 'rare_leisure', 'regular_leisure', 'business', 'corporate', 'road_warrior'
    id: Optional[int] = None

@dataclass
class LegacyHotel:
    """A hotel property."""
    name: str
    street: str
    city: str
    state: str  # 2 char max
    zip: str  # 10 char max
    email: str
    website: str
    phone: str  # 12 char max
    type: str  # 'resort', 'hotel', or 'motel'
    tourist_region: Optional[str]
    rooms: dict[str, LegacyRoomInfo]
    base_price: float
    resort_fee: float
    id: Optional[int] = None

@dataclass
class LegacyLineItem:
    """A line item on a transaction."""
    description: str
    amount_per: float
    quantity: int

@dataclass
class LegacyPayment:
    """Payment information for a transaction."""
    method: str  # e.g., "Visa xxxx-1234"
    amount: float
    status: str  # 'APPROVED' or 'DECLINED'

@dataclass
class LegacyTransaction:
    """A financial transaction for a hotel stay."""
    customer_id: int
    hotel_id: int
    check_in_date: str  # formatted as YYYY-MM-DD
    check_out_date: datetime
    line_items: list[LegacyLineItem]
    total: float
    payment: LegacyPayment
    id: Optional[int] = None

@dataclass
class LegacyGiftShop:
    """A gift shop."""
    name: str
    street: str
    city: str
    state: str  # 2 char max
    zip: str  # 10 char max
    id: Optional[int] = None

@dataclass
class LegacyProduct:
    """A product sold in a gift shop."""
    name: str
    price: float
    category: str
    id: Optional[int] = None


class_map = {
    "Hotel": LegacyHotel,
    "Customer": LegacyCustomer,
    "RoomInfo": LegacyRoomInfo,
    "LineItem": LegacyLineItem,
    "Payment": LegacyPayment,
    "Transaction": LegacyTransaction,
    "GiftShop": LegacyGiftShop,
    "Product": LegacyProduct,
}

# Redirect pickle lookups to legacy module
class LegacyUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if name in class_map:
            return class_map[name]
        return super().find_class(module, name)

def to_dict(obj):
    """Recursively convert legacy dataclasses to plain dicts."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: to_dict(v) for k, v in vars(obj).items()}
    elif isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_dict(v) for v in obj]
    return obj

def find_legacy_objects(obj, path="root"):
    """Find any objects whose module is __main__ (legacy stragglers)."""
    if hasattr(obj, '__module__') and obj.__module__ == '__main__':
        print(f"  LEGACY OBJECT at {path}: {type(obj).__name__}")
    if isinstance(obj, dict):
        for k, v in obj.items():
            find_legacy_objects(v, f"{path}[{k!r}]")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            find_legacy_objects(v, f"{path}[{i}]")
    elif is_dataclass(obj) and not isinstance(obj, type):
        for k, v in vars(obj).items():
            find_legacy_objects(v, f"{path}.{k}")

def main():

    print()
    print("  Hospitality Chain Simulation Generator  --  Export Migration Tool  v0.1")
    print("  (C)  2025-2026 Flint Million PhD")
    print("  For use in CIS 444/544 courses at Minnesota State University, Mankato")
    print()

    parser = argparse.ArgumentParser()

    parser.add_argument("INPUT", nargs=1, type=str, help="Input .pkl HotelGen data file")

    args = parser.parse_args()

    input_path = os.path.abspath(args.INPUT[0])
    output_path = input_path.replace(".pkl", "_v1.pkl")

    print(f"Attempting to load dump file: {input_path}")
    try:
        with open(input_path,"rb") as f:
            source_obj = LegacyUnpickler(f).load()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print("Input loaded successfully.")
    # Test if we have a data version
    if source_obj.get("data_version",0) >= 1:
        print("Data version already 1. No migration needed.")
        sys.exit(0)
    
    print("Data version not found - data is version 0. Migrating...")

    # print(source_obj['state'].keys())
    print("Converting objects...")

    new_hotels = [models.Hotel(**to_dict(h)) for h in tqdm.tqdm(source_obj['state']['hotels'],desc="Hotels")]
    source_obj['state']['hotels'] = new_hotels

    new_customers = [models.Customer(**to_dict(c)) for c in tqdm.tqdm(source_obj['state']['customers'],desc="Customers")]
    source_obj['state']['customers'] = new_customers

    new_transactions = [models.Transaction(**to_dict(t)) for t in tqdm.tqdm(source_obj['state']['transactions'],desc="Transactions")]
    source_obj['state']['transactions'] = new_transactions

    # new_lineitems = [LineItem(**vars(l)) for l in tqdm.tqdm(source_obj['state']['line_items'],desc="LineItems")]
    # source_obj['state']['lineitems'] = new_lineitems

    # new_payments = [Payment(**vars(p)) for p in tqdm.tqdm(source_obj['state']['payments'],desc="Payments")]
    # source_obj['state']['payments'] = new_payments

    new_giftshops = [models.GiftShop(**to_dict(g)) for g in tqdm.tqdm(source_obj.get('state',{}).get('giftshops',[]),desc="GiftShops")]
    source_obj['state']['giftshops'] = new_giftshops

    new_products = [models.Product(**to_dict(p)) for p in tqdm.tqdm(source_obj.get('state',{}).get('products',[]),desc="Products")]
    source_obj['state']['products'] = new_products

    new_cache = {k: models.Customer(**to_dict(p)) for k,p in tqdm.tqdm(source_obj.get('state').get('cache',{}).get('customers_by_id',{}).items(),desc="Customers cache")}
    source_obj['state']['cache']['customers_by_id'] = new_cache

    new_cache = {k: models.Hotel(**to_dict(p)) for k,p in tqdm.tqdm(source_obj.get('state').get('cache',{}).get('hotels_by_id',{}).items(),desc="Hotels cache")}
    source_obj['state']['cache']['hotels_by_id'] = new_cache

    source_obj['state']["data_version"] = 1
    print("Migration OK - writing new file...")

    with open(output_path, "wb") as f:
        pickle.dump(source_obj, f)
    print(f"Migration to data version 1 completed. Results are in {output_path}")

if __name__ == "__main__":
    main()















