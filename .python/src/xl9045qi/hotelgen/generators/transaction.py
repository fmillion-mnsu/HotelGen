import datetime

from xl9045qi.hotelgen import data
from xl9045qi.hotelgen import simulation
from xl9045qi.hotelgen.generators import r
from xl9045qi.hotelgen.models import Transaction, LineItem, Payment

def generate_transaction(self: simulation.HGSimulationState, hotel_id: int, customer: int, stay_length: int, room_type: str) -> Transaction:
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