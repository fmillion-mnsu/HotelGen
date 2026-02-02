import datetime
import pickle

from xl9045qi.hotelgen.generators.transaction import generate_transaction

from . import phase0, phase1, phase2, phase3

from xl9045qi.hotelgen import data

from .day import get_datetime_by_day_num, process_day

PRE_PHASES = [phase0.phase0, phase1.phase1, phase2.phase2, phase3.phase3]

class HGSimulationState:

    def __init__(self, job):
        self.job = job
        # Store hotels here
        self.state = {}
        self.state['hotels'] = []
        self.state['customers'] = []
        self.state['transactions'] = []
        self.state['events'] = []
        self.state['gen_params'] = {}

    def export(self, path: str):
        """Export the generated hotel data to a specified path as a pickle file.

        Args:
            path (str): The file path where the hotel data should be saved.
        """
        with open(path, "wb") as f:
            data = {
                "params": self.state['gen_params'],
                "jobfile": self.job,
                "state": self.state
            }
            pickle.dump(data, f)

        #print(f"Exported {len(inst.state['hotels'])} hotels to {path}.")
    
    def import_pkl(self, path: str):
        """Import generated hotel data from a specified pickle file.

        Args:
            path (str): The file path from which the hotel data should be loaded.
        """
        with open(path, "rb") as f:
            data = pickle.load(f)
            self.job = data.get("jobfile", {})
            self.state = data.get("state", {})

    def checkin(self, customer_id: int, hotel_id: int, room_type: str, stay_length: int):
        """Check in a customer to a hotel for a specified stay length.

        Args:
            customer_id (int): The ID of the customer to check in.
            hotel_id (int): The ID of the hotel where the customer is checking in.
            room_type (str): The type of room being booked.
            stay_length (int): The length of the stay in days.
        """

        checkin_event = {
            'event': 'checkin',
            'customer_id': customer_id,
            'property_id': hotel_id,
            'checkin_date': self.state['current_day'],
            'checkout_date': self.state['current_day'] + datetime.timedelta(days=stay_length),
            'room_type': room_type
        }

        self.state['events'].append(checkin_event)
        self.state['occupied_rooms'][hotel_id][room_type].append((
            customer_id,
            self.state['current_day_num'],
            stay_length,
            room_type
        ))

        customer_data = self.state['cache']['customers_by_id'][customer_id]
        
        self.state['occupied_customers'][customer_data.type].append((
            customer_id,
            hotel_id,
            self.state['current_day'] + datetime.timedelta(days=stay_length) + datetime.timedelta(days=data.customer_archetypes[customer_data.type].get('min_gap_days', 14))
        ))

    def checkout(self, hotel_id: int, booking: tuple, force: bool = False):
        """Checkout a customer from an occupied room tuple"""
        # If today is < the checkout date and not force, warn

        if self.state['current_day'] < get_datetime_by_day_num(self, booking[1]) and not force:
            print(f"[bold red]WARNING: Attempting to checkout customer {booking[0]} before their scheduled checkout date of {booking[1]}. Use force=True to override.")
            return

        skipped_days = 0
        if self.state['current_day'] < \
            datetime.datetime.strptime(self.job['generation']['dates']['start'], "%Y-%m-%d") + \
            datetime.timedelta(days=booking[2]):
            # Determine how many days the user skipped
            skipped_days = booking[1] - self.state['current_day_num']

        # Find the tuple in the self.state['occupied_rooms'] array and remove it
        self.state['occupied_rooms'][hotel_id][booking[3]].remove(booking)

        self._checkout_record(hotel_id, booking, skipped_days)

    def checkout_finalize(self, hotel_id: int, booking: tuple):
        """Finalize checkout when room already removed from occupied_rooms (batch processing)"""
        skipped_days = 0
        if self.state['current_day'] < \
            datetime.datetime.strptime(self.job['generation']['dates']['start'], "%Y-%m-%d") + \
            datetime.timedelta(days=booking[2]):
            skipped_days = booking[1] - self.state['current_day_num']

        self._checkout_record(hotel_id, booking, skipped_days)

    def _checkout_record(self, hotel_id: int, booking: tuple, skipped_days: int):
        """Record checkout event and transaction (shared by checkout methods)"""
        # Add checkout event
        checkout_event = {
            'event': 'checkout',
            'property_id': hotel_id,
            'customer_id': booking[0],
            'checkout_date': self.state['current_day'],
            'room_type': booking[3]
        }
        self.state['events'].append(checkout_event)

        trans = generate_transaction(self, hotel_id, booking[0], booking[2] - skipped_days, booking[3])
        self.state['transactions'].append(trans)
