import datetime
import random

from typing import TYPE_CHECKING

from xl9045qi.hotelgen import data
from xl9045qi.hotelgen.generators import r
from xl9045qi.hotelgen.models import Transaction, LineItem, Payment, RetailCustomer, RetailTransaction

if TYPE_CHECKING:
    from xl9045qi.hotelgen.simulation import HGSimulationState

def generate_transaction(self: 'HGSimulationState', hotel_id: int, customer: int, stay_length: int, room_type: str) -> Transaction:
    """Generate a transaction for a hotel stay.

    Args:
        self: The simulation state.
        hotel_id: The ID of the hotel.
        customer: The customer ID.
        stay_length: Length of stay in nights.
        room_type: The room type code.

    Returns:
        Transaction: A Transaction dataclass instance.
    """
    overall_total = 0.0

    this_hotel = self.state['cache']['hotels_by_id'][hotel_id]
    # Room price is already fully calculated (base_price * room_type_multiplier) in hotel generation
    room_price = this_hotel.rooms[room_type].price

    room_cost = room_price * stay_length

    line_items = [
        LineItem(
            description=f"Room Charge - {stay_length} nights @ ${room_price:.2f}/night",
            amount_per=room_price,
            quantity=stay_length,
        )
    ]

    # If the hotel has a resort fee, add it
    if this_hotel.resort_fee > 0.0:
        line_items.append(LineItem(
            description=f"Resort Fee @ ${this_hotel.resort_fee:.2f}/night",
            amount_per=this_hotel.resort_fee,
            quantity=stay_length
        ))
        room_cost += this_hotel.resort_fee * stay_length

    overall_total += room_cost

    # If the hotel is in a state with sales tax, apply it
    state_tax = data.state_data.get(this_hotel.state, {}).get('sales_tax', 0)
    if state_tax > 0:
        tax_amount = room_cost * state_tax
        line_items.append(LineItem(
            description=f"{this_hotel.state.upper()} Sales Tax @ {state_tax*100:.2f}%",
            amount_per=tax_amount,
            quantity=1
        ))
        overall_total += tax_amount

    # If the state has luxury tax, apply it
    # Luxury tax applies only if room cost exceeds $100 per night
    if room_cost > 100:
        luxury_tax = data.state_data.get(this_hotel.state, {}).get('luxury_tax', 0)
        if luxury_tax > 0:
            tax_amount = room_cost * luxury_tax
            line_items.append(LineItem(
                description=f"{this_hotel.state.upper()} Luxury Tax @ {luxury_tax*100:.2f}%",
                amount_per=tax_amount,
                quantity=1
            ))
            overall_total += tax_amount

    overall_total = round(overall_total, 2)

    # Determine payment status (5% decline rate)
    payment_status = "DECLINED" if r.random() < 0.05 else "APPROVED"
    payment = Payment(
        method=r.choice(data.misc['credit_card_names']) + " xxxx-" + str(r.randrange(10, 9999)).zfill(4),
        amount=overall_total,
        status=payment_status
    )

    return Transaction(
        customer_id=customer,
        hotel_id=hotel_id,
        check_in_date=(self.state['current_day'] - datetime.timedelta(days=stay_length)).strftime("%Y-%m-%d"),
        check_out_date=self.state['current_day'],
        line_items=line_items,
        total=overall_total,
        payment=payment
    )


def generate_transaction(self: 'HGSimulationState', hotel_id: int, customer: int, stay_length: int, room_type: str) -> Transaction:
    """Generate a transaction for a hotel stay.

    Args:
        self: The simulation state.
        hotel_id: The ID of the hotel.
        customer: The customer ID.
        stay_length: Length of stay in nights.
        room_type: The room type code.

    Returns:
        Transaction: A Transaction dataclass instance.
    """
    overall_total = 0.0

    this_hotel = self.state['cache']['hotels_by_id'][hotel_id]
    # Room price is already fully calculated (base_price * room_type_multiplier) in hotel generation
    room_price = this_hotel.rooms[room_type].price

    room_cost = room_price * stay_length

    line_items = [
        LineItem(
            description=f"Room Charge - {stay_length} nights @ ${room_price:.2f}/night",
            amount_per=room_price,
            quantity=stay_length,
        )
    ]

    # If the hotel has a resort fee, add it
    if this_hotel.resort_fee > 0.0:
        line_items.append(LineItem(
            description=f"Resort Fee @ ${this_hotel.resort_fee:.2f}/night",
            amount_per=this_hotel.resort_fee,
            quantity=stay_length
        ))
        room_cost += this_hotel.resort_fee * stay_length

    overall_total += room_cost

    # If the hotel is in a state with sales tax, apply it
    state_tax = data.state_data.get(this_hotel.state, {}).get('sales_tax', 0)
    if state_tax > 0:
        tax_amount = room_cost * state_tax
        line_items.append(LineItem(
            description=f"{this_hotel.state.upper()} Sales Tax @ {state_tax*100:.2f}%",
            amount_per=tax_amount,
            quantity=1
        ))
        overall_total += tax_amount

    # If the state has luxury tax, apply it
    # Luxury tax applies only if room cost exceeds $100 per night
    if room_cost > 100:
        luxury_tax = data.state_data.get(this_hotel.state, {}).get('luxury_tax', 0)
        if luxury_tax > 0:
            tax_amount = room_cost * luxury_tax
            line_items.append(LineItem(
                description=f"{this_hotel.state.upper()} Luxury Tax @ {luxury_tax*100:.2f}%",
                amount_per=tax_amount,
                quantity=1
            ))
            overall_total += tax_amount

    overall_total = round(overall_total, 2)

    # Determine payment status (5% decline rate)
    payment_status = "DECLINED" if r.random() < 0.05 else "APPROVED"
    payment = Payment(
        method=r.choice(data.misc['credit_card_names']) + " xxxx-" + str(r.randrange(10, 9999)).zfill(4),
        amount=overall_total,
        status=payment_status
    )

    return RetailTransaction(
        customer_id=customer,
        hotel_id=hotel_id,
        check_in_date=(self.state['current_day'] - datetime.timedelta(days=stay_length)).strftime("%Y-%m-%d"),
        check_out_date=self.state['current_day'],
        line_items=line_items,
        total=overall_total,
        payment=payment
    )

def generate_retail_transaction(self: 'HGSimulationState', store_id: int, customer_id: Optional[int] = -1) -> RetailTransaction:
    """Generate a retail transaction for a gift shop."""
    
    # Store customers are tracked separately.
    if customer_id in self.state['cache'].get('retail_customers_by_id',{}).keys():
        this_customer: RetailCustomer = self.state['cache']['retail_customers_by_id'][customer_id]
    else:
        # If the customer ID exists in the main customer database, copy it.
        if customer_id in self.state['cache']['customers_by_id'].keys():
            this_customer = self.state['cache']['customers_by_id'][customer_id].ToRetailCustomer()
            self.state['cache'].setdefault('retail_customers_by_id', {})
            this_customer.id = len(self.state['cache']['retail_customers_by_id'])
            self.state['cache']['retail_customers_by_id'][this_customer.id] = this_customer
        else:
            # We either have a newly generated customer, or a no-customer transaction
            # Half and half
            should_make_customer = (random.random() > 0.5)
            if should_make_customer:
                this_customer = generate_retail_customer(self)
                this_customer.id = len(self.state['cache']['retail_customers_by_id'])
                self.state['cache']['retail_customers_by_id'][this_customer.id] = this_customer

    store_data = [x for x in self.state['giftshops'] if x.id == store_id][0]

    # If our customer is a real customer, get its archetype; if not, anonymous
    if this_customer.main_customer_id != -1:
        archetype = self.state['cache']['customers_by_id'][this_customer.main_customer_id].type
    else:
        archetype = "anonymous"

    # Get the category probabilities for this archetype
    if archetype == "anonymous":
        category_probabilities = data.gifts['anonymous_gift_probabilities']
    else:
        category_probabilities = data.customer_archetypes[archetype]['gift_category_probabilities']

    # Get list of all products for this store
    store = [x for x in self.state['products'] if x.sold_at == store_id]
    if len(store) == 0:
        print(f"ERROR: No products found for store {store_id}")
        return None
    
    products_by_category = {}
    for product in store:
        products_by_category.setdefault(product.category, []).append(product)
    
    # How many products? (1-9 on an exponential curve biasing towards lower numbers)
    product_count = int(random.random() ** 3) * 9 + 1

    line_items = []
    running_taxed_total = 0.0

    for _ in product_count:
        # Choose a category based on the probabilities
        category = r.choices(list(category_probabilities.keys()), weights=list(category_probabilities.values()))[0]
        
        # Choose a product from the chosen category
        product = r.choice(products_by_category[category])
        
        # Quantity (1-3 but HEAVILY biased towards 1)
        qty = random.randint(1,15) - 12
        if qty <= 0: qty = 1

        # Add to transaction
        line_items.append(LineItem(
            description=product.name,
            amount_per=product.price,
            quantity=qty
        ))
        if category != "food":
            running_taxed_total += product.price * qty

    # Do we have sales tax?
    sales_tax = data.state_data[store_data.state]['sales_tax']
    if sales_tax > 0:
        tax_amount = running_taxed_total * sales_tax
        line_items.append(LineItem(
            description=f"{store_data.state.upper()} Sales Tax @ {sales_tax*100:.2f}%",
            amount_per=tax_amount,
            quantity=1
        ))
    
    # Get the total of all line items taking qty into account
    total_paid = sum([x.amount_per * x.quantity for x in line_items])
    # All items not in "food" category are sales taxed
    # Create a retail transaction for this product
    retail_transaction = RetailTransaction(
        customer_id=customer_id,
        store_id=store_id,
        total=total_paid,
        line_items=line_items,
        payment=Payment(
            method=r.choice(data.misc['credit_card_names']) + " xxxx-" + str(r.randrange(10, 9999)).zfill(4),
            amount=total_paid,
            status="APPROVED" # No failures for now
        )
    )
    
    return retail_transaction
