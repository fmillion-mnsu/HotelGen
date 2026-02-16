# Migrate pickles to newer versions

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import argparse
import pickle
import os.path
import sys

from xl9045qi.hotelgen.simulation import HGSimulationState
from xl9045qi.hotelgen.models import RoomInfo, Customer, Hotel, LineItem, Payment, Transaction, GiftShop, Product

import tqdm

# Legacy Classes
@dataclass
class RoomInfo:
    """Information about a room type in a hotel."""
    count: int
    price: float

@dataclass
class Customer:
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
class Hotel:
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
    rooms: dict[str, RoomInfo]
    base_price: float
    resort_fee: float
    id: Optional[int] = None

@dataclass
class LineItem:
    """A line item on a transaction."""
    description: str
    amount_per: float
    quantity: int

@dataclass
class Payment:
    """Payment information for a transaction."""
    method: str  # e.g., "Visa xxxx-1234"
    amount: float
    status: str  # 'APPROVED' or 'DECLINED'

@dataclass
class Transaction:
    """A financial transaction for a hotel stay."""
    customer_id: int
    hotel_id: int
    check_in_date: str  # formatted as YYYY-MM-DD
    check_out_date: datetime
    line_items: list[LineItem]
    total: float
    payment: Payment
    id: Optional[int] = None


class_map = {
    "Hotel": Hotel,
    "Customer": Customer,
    "RoomInfo": RoomInfo,
    "LineItem": LineItem,
    "Payment": Payment,
    "Transaction": Transaction,
    "GiftShop": GiftShop,
    "Product": Product,
}

# Redirect pickle lookups to legacy module
class LegacyUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        # Remap old module paths to legacy_models
        if name in ('Hotel', 'Customer', 'RoomInfo', 'LineItem', 'Payment', 'Transaction', 'GiftShop', 'Product'):
            return class_map.get(name)
        return super().find_class(module, name)

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

    new_hotels = [Hotel(**vars(h)) for h in tqdm.tqdm(source_obj['state']['hotels'],desc="Hotels")]
    source_obj['state']['hotels'] = new_hotels

    new_customers = [Customer(**vars(c)) for c in tqdm.tqdm(source_obj['state']['customers'],desc="Customers")]
    source_obj['state']['customers'] = new_customers

    new_transactions = [Transaction(**vars(t)) for t in tqdm.tqdm(source_obj['state']['transactions'],desc="Transactions")]
    source_obj['state']['transactions'] = new_transactions

    # new_lineitems = [LineItem(**vars(l)) for l in tqdm.tqdm(source_obj['state']['line_items'],desc="LineItems")]
    # source_obj['state']['lineitems'] = new_lineitems

    # new_payments = [Payment(**vars(p)) for p in tqdm.tqdm(source_obj['state']['payments'],desc="Payments")]
    # source_obj['state']['payments'] = new_payments

    new_giftshops = [GiftShop(**vars(g)) for g in tqdm.tqdm(source_obj.get('state',{}).get('giftshops',[]),desc="GiftShops")]
    source_obj['state']['giftshops'] = new_giftshops

    new_products = [Product(**vars(p)) for p in tqdm.tqdm(source_obj.get('state',{}).get('products',[]),desc="Products")]
    source_obj['state']['products'] = new_products

    source_obj["data_version"] = 1
    print("Migration OK - writing new file...")

    with open(output_path, "wb") as f:
        pickle.dump(source_obj, f)
    print(f"Migration completed. Results are in {output_path}")

if __name__ == "__main__":
    main()















