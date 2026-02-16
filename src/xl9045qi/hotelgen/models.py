from pydantic.dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class RoomInfo:
    """Information about a room type in a hotel."""
    count: int
    price: float

# Dataclass for Hotel object:
# Fields:
#   "name": string
#   "street": string
#   "city": string
#   "state": string (2 char max)
#   "zip": string (10 char max),
#   "email": string,
#   "website": string,
#   "phone": string (12 char max),
#   "type": string (from 'resort', 'hotel', 'motel')
#   "tourist_region": string
#   "rooms": dict:
#     key: string (room type code, e.g. '1kn', '2qn', etc)
#     value: RoomInfo dataclass
#   "base_price": float,
#   "resort_fee": float

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

    def ToRetailCustomer(self):
        return RetailCustomer(
            fname=self.fname,
            lname=self.lname,
            street=self.street,
            city=self.city,
            state=self.state,
            zip=self.zip,
            email=self.email,
            main_customer_id=self.id
        )

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

@dataclass
class RetailTransaction:
    """A financial transaction for a retail store."""
    customer_id: Optional[int]
    store_id: int
    line_items: list[LineItem]
    total: float
    payment: Payment
    id: Optional[int] = None


@dataclass
class RetailCustomer:
    """A customer record."""
    fname: str
    lname: str
    street: str
    city: str
    state: str  # 2 char max
    zip: str  # 10 char max
    email: str
    main_customer_id: Optional[int] = -1
    id: Optional[int] = None

@dataclass
class GiftShop:
    """A gift shop."""
    name: str
    street: str
    city: str
    state: str  # 2 char max
    zip: str  # 10 char max
    located_at: int
    date_opened: Optional[datetime] = None
    id: Optional[int] = None

@dataclass
class Product:
    """A product sold in a gift shop."""
    name: str
    price: float
    category: str
    sold_at: int
    id: Optional[int] = None
