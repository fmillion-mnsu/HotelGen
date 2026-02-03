import mssql_python as mssql
import tqdm

from xl9045qi.hotelgen import data
from xl9045qi.hotelgen.models import Hotel, Customer, Transaction


def chunked_executemany(cursor, query, values, chunk_size=10000, desc="Inserting"):
    """Execute a query with many values in chunks, showing progress."""
    total = len(values)
    for i in tqdm.tqdm(range(0, total, chunk_size), desc=desc, unit="chunk"):
        chunk = values[i:i + chunk_size]
        cursor.executemany(query, chunk)
    return total

# Property example:
# {
#     "name": "Acceptable Beaker Hotel",
#     "street": "1037 Scott Street",
#     "city": "Yuma",
#     "state": "CO",
#     "zip": "80759",
#     "email": "events@acceptablebeakerhotel.com",
#     "website": "https: //www.acceptablebeakerhotel.com",
#     "phone": "422-503-4945",
#     "type": "Hotel",
#     "tourist_region": null,
#     "rooms": {
#         "1kn": {
#             "count": 22,
#             "price": 126.03
#         },
#         "2qn": {
#             "count": 36,
#             "price": 123.26
#         },
#         "2qs": {
#             "count": 2,
#             "price": 160.56
#         },
#         "es": {
#             "count": 0,
#             "price": 233.59
#         }
#     },
#     "base_price": 119.59045247223855,
#     "resort_fee": 0.0,
#     "id": 1
# }

SCHEMA = {
    "property": {
        "id": "INT PRIMARY KEY IDENTITY(1,1)",
        "name": "NVARCHAR(192) NOT NULL",
        "street_address": "NVARCHAR(192) NOT NULL",
        "city": "NVARCHAR(96) NOT NULL",
        "state": "VARCHAR(2) NOT NULL",
        "zip": "VARCHAR(10) NOT NULL",
        "email": "NVARCHAR(192) NOT NULL",
        "website": "NVARCHAR(192) NOT NULL",
        "phone": "VARCHAR(20) NOT NULL",
    },
    "room_type": {
        "id": "INT PRIMARY KEY",
        "code": "VARCHAR(10) NOT NULL",
        "description": "NVARCHAR(192) NOT NULL",
    },
    "property_rooms": {
        "id": "INT PRIMARY KEY IDENTITY(1,1)",
        "property_id": "INT NOT NULL",
        "room_type_id": "INT NOT NULL",
        "count": "INT NOT NULL",
        "price": "DECIMAL(10,2) NOT NULL",
        "resort_fee": "DECIMAL(10,2) NOT NULL",
        "_fk": ["FOREIGN KEY (property_id) REFERENCES property(id)",
                "FOREIGN KEY (room_type_id) REFERENCES room_type(id)"]
    },
    "customer": {
        "id": "INT PRIMARY KEY IDENTITY(1,1)",
        "first_name": "NVARCHAR(96) NOT NULL",
        "last_name": "NVARCHAR(96) NOT NULL",
        "email": "NVARCHAR(192) NOT NULL",
        "phone": "VARCHAR(20) NOT NULL",
        "address": "NVARCHAR(192) NOT NULL",
        "city": "NVARCHAR(96) NOT NULL",
        "state": "VARCHAR(2) NOT NULL",
        "zip": "VARCHAR(10) NOT NULL",
    },
    "event": {
        "id": "INT PRIMARY KEY IDENTITY(1,1)",
        "customer_id": "INT NOT NULL",
        "event_code": "VARCHAR(20) NOT NULL",
        "property_id": "INT NOT NULL",
        "event_date": "DATE NOT NULL",
        "_fk": ["FOREIGN KEY (customer_id) REFERENCES customer(id)",
                "FOREIGN KEY (property_id) REFERENCES property(id)"
        ]
    },
    "transact": {
        "id": "INT PRIMARY KEY IDENTITY(1,1)",
        "transaction_date": "DATETIME NOT NULL",
        "customer_id": "INT NOT NULL",
        "hotel_id": "INT NOT NULL",
        "amount": "DECIMAL(10,2) NOT NULL",
        "payment_method": "VARCHAR(20) NOT NULL",
        "payment_card_stub": "VARCHAR(20)",
        "_fk": ["FOREIGN KEY (customer_id) REFERENCES customer(id)",
                "FOREIGN KEY (hotel_id) REFERENCES property(id)"
        ]
    },
    "transaction_line": {
        "id": "INT PRIMARY KEY IDENTITY(1,1)",
        "transaction_id": "INT NOT NULL",
        "description": "NVARCHAR(192) NOT NULL",
        "amount_per": "DECIMAL(10,2) NOT NULL",
        "quantity": "INT NOT NULL",
        "_fk": ["FOREIGN KEY (transaction_id) REFERENCES transact(id)"]
    }
}

class DatabaseLoader():
    
    def drop_all_tables(self):
        """Drop all user tables, handling foreign key constraints properly."""
        cursor = self._conn.cursor()

        # First, get all foreign key constraints
        # Use OBJECT_SCHEMA_NAME for the parent table's schema (not SCHEMA_NAME which expects a schema_id)
        cursor.execute("""
            SELECT
                QUOTENAME(OBJECT_SCHEMA_NAME(parent_object_id)) + '.' + QUOTENAME(OBJECT_NAME(parent_object_id)) AS table_name,
                QUOTENAME(name) AS constraint_name
            FROM sys.foreign_keys
        """)
        fk_rows = cursor.fetchall()

        # Drop each FK constraint individually
        for row in fk_rows:
            table_name = row[0]
            constraint_name = row[1]
            try:
                cursor.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT {constraint_name}")
                self._conn.commit()
            except Exception as e:
                print(f"Warning: Could not drop constraint {constraint_name}: {e}")

        # Now get all user tables
        cursor.execute("""
            SELECT QUOTENAME(SCHEMA_NAME(schema_id)) + '.' + QUOTENAME(name) AS table_name
            FROM sys.tables
        """)
        table_rows = cursor.fetchall()

        # Drop each table individually
        for row in table_rows:
            table_name = row[0]
            try:
                cursor.execute(f"DROP TABLE {table_name}")
                self._conn.commit()
            except Exception as e:
                print(f"Warning: Could not drop table {table_name}: {e}")
    
    def connect(self) -> bool:
        # Try to connect first
        print("Connecting to the database...",end="",flush=True)

        try:
            conn = mssql.connect(
                server=self.job["database"]["host"],   
                uid=self.job["database"]["username"],
                pwd=self.job["database"]["password"],
                database=self.job["database"]["dbname"],
                encrypt="yes",
                trust_server_certificate="yes"
            )
        except Exception as e:
            print("failed.")
            print("ERROR: Could not connect to the database.")
            print("       " + str(e))
            print()
            return False
        
        print("OK.")

        self._conn = conn

        return True

    def check_tables(self):
        """Return True if there are any existing user tables in the database, False otherwise."""

        # Determine if there are any objects in the database beyond system objects (i.e. any tables)
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT COUNT(*)
            FROM sys.objects
            WHERE type IN ('U')
        """)
        row = cursor.fetchone()
        if row is None:
            existing_tables = 0
        else:
            existing_tables = row[0]

        if existing_tables > 0:
            return True

        return False

    def __init__(self, job: dict):
        self.job = job

    def make_schema(self):
        for table, columns in SCHEMA.items():
            column_defs = []
            for col,defn in columns.items():
                if col == "_fk":
                    for fk in defn:
                        column_defs.append(fk)
                else:
                    column_defs.append(f"{col} {defn}")
            column_defs_str = ",\n    ".join(column_defs)
            create_sql = f"CREATE TABLE {table} (\n    {column_defs_str}\n);"
            print(f"  - Creating table {table}...",end="",flush=True)
            cursor = self._conn.cursor()
            cursor.execute(create_sql)
            self._conn.commit()
            print("OK.")

    def set_identity_insert(self, table: str, enable: bool) -> bool:
        """Enable or disable IDENTITY_INSERT for the specified table."""
        cursor = self._conn.cursor()
        try:
            if enable:
                cursor.execute(f"SET IDENTITY_INSERT {table} ON;")
            else:
                cursor.execute(f"SET IDENTITY_INSERT {table} OFF;")
            cursor.connection.commit()
            return True
        except mssql.exceptions.ProgrammingError as e:
            return False

    def load_data(self, state: dict):
        """Load the data into the database. The `data` dict should be the 'state' item from a HGSimulationState  object."""
        # Ok, let's do this.

        cursor = self._conn.cursor()

        # Load room types first - batch insert
        print("Loading room types...")
        room_type_values = [
            (data.room_types[rt]['id'], rt, data.room_types[rt]['name'])
            for rt in data.room_types.keys()
        ]
        if room_type_values:
            cursor.executemany(
                "INSERT INTO room_type (id, code, description) VALUES (?, ?, ?)",
                room_type_values
            )
        cursor.connection.commit()

        # First, we load the hotels - batch insert
        print("Collecting property data...")
        self.set_identity_insert("property", True)

        # Collect all property values
        property_values = [
            (hotel.id, hotel.name, hotel.street, hotel.city, hotel.state,
             hotel.zip, hotel.email, hotel.website, hotel.phone)
            for hotel in state['hotels']
        ]

        # Batch insert properties
        if property_values:
            cursor.executemany("""
                INSERT INTO property (id, name, street_address, city, state, zip, email, website, phone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, property_values)
        print(f"Inserted {len(property_values)} properties")

        # Build room_type lookup cache
        cursor.execute("SELECT id, code FROM room_type")
        room_type_cache = {code: id for id, code in cursor.fetchall()}

        # Collect all property_rooms values
        property_rooms_values = []
        for hotel in state['hotels']:
            for rt, room_info in hotel.rooms.items():
                room_type_id = room_type_cache.get(rt)
                if room_type_id is None:
                    # Room type doesn't exist, insert it and update cache
                    rt_name = data.room_types.get(rt, {}).get('name', rt)
                    cursor.execute("""
                        INSERT INTO room_type (code, description)
                        OUTPUT INSERTED.id
                        VALUES (?, ?);
                    """, (rt, rt_name))
                    room_type_id = cursor.fetchone()[0]
                    room_type_cache[rt] = room_type_id

                property_rooms_values.append((
                    hotel.id,
                    room_type_id,
                    room_info.count,
                    room_info.price,
                    hotel.resort_fee
                ))

        # Batch insert property_rooms
        if property_rooms_values:
            cursor.executemany("""
                INSERT INTO property_rooms (property_id, room_type_id, count, price, resort_fee)
                VALUES (?, ?, ?, ?, ?);
            """, property_rooms_values)
        print(f"Inserted {len(property_rooms_values)} property-room relationships")

        cursor.connection.commit()
        self.set_identity_insert("property", False)

        # Now, load customers - batch insert with progress
        self.set_identity_insert("customer", True)

        # Collect all customer values
        customer_values = [
            (cust.id, cust.fname, cust.lname, cust.email, cust.phone,
             cust.street, cust.city, cust.state, cust.zip)
            for cust in state['customers']
        ]

        # Batch insert customers in chunks
        if customer_values:
            count = chunked_executemany(
                cursor,
                """INSERT INTO customer (id, first_name, last_name, email, phone, address, city, state, zip)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                customer_values,
                chunk_size=10000,
                desc="Loading customers"
            )
            print(f"Inserted {count} customers")

        cursor.connection.commit()
        self.set_identity_insert("customer", False)

        # Lets now load the events - batch insert with progress
        print("Preparing event data...")
        event_values = []
        for event in state['events']:
            if event['event'] == 'checkin':
                event_code = 'checkin'
                event_date = event['checkin_date']
            else:
                event_code = 'checkout'
                event_date = event['checkout_date']
            event_values.append((
                event['customer_id'],
                event_code,
                event['property_id'],
                event_date
            ))

        # Batch insert events in chunks
        if event_values:
            count = chunked_executemany(
                cursor,
                """INSERT INTO event (customer_id, event_code, property_id, event_date)
                   VALUES (?, ?, ?, ?);""",
                event_values,
                chunk_size=50000,
                desc="Loading events"
            )
            print(f"Inserted {count} events")

        cursor.connection.commit()

        # And finally the transactions - batch insert everything
        print("Preparing transaction data...")
        self.set_identity_insert("transact", True)

        # Collect all transaction values
        transaction_values = []
        all_line_items = []

        for transaction in state['transactions']:
            # Parse payment method (e.g., "Visa xxxx-1234" -> method="Visa", stub="xxxx-1234")
            payment_parts = transaction.payment.method.split(' ', 1)
            payment_method = payment_parts[0]
            payment_card_stub = payment_parts[1] if len(payment_parts) > 1 else None

            transaction_values.append((
                transaction.id,
                transaction.check_out_date,
                transaction.customer_id,
                transaction.hotel_id,
                transaction.total,
                payment_method,
                payment_card_stub
            ))

            # Collect line items with their transaction_id for batch insert later
            if transaction.line_items:
                for line in transaction.line_items:
                    all_line_items.append((
                        transaction.id,
                        line.description,
                        line.amount_per,
                        line.quantity
                    ))

        # Batch insert all transactions
        if transaction_values:
            count = chunked_executemany(
                cursor,
                """INSERT INTO transact (id, transaction_date, customer_id, hotel_id, amount, payment_method, payment_card_stub)
                   VALUES (?, ?, ?, ?, ?, ?, ?);""",
                transaction_values,
                chunk_size=50000,
                desc="Loading transactions"
            )
            print(f"Inserted {count} transactions")

        cursor.connection.commit()
        self.set_identity_insert("transact", False)

        # Now batch insert ALL transaction line items at once
        if all_line_items:
            count = chunked_executemany(
                cursor,
                """INSERT INTO transaction_line (transaction_id, description, amount_per, quantity)
                   VALUES (?, ?, ?, ?);""",
                all_line_items,
                chunk_size=50000,
                desc="Loading transaction lines"
            )
            print(f"Inserted {count} transaction line items")

        cursor.connection.commit()

        print("Data load completed!")
    