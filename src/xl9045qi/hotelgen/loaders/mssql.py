import mssql_python as mssql
import tqdm

from xl9045qi.hotelgen import data
from xl9045qi.hotelgen.models import Hotel, Customer, Transaction

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

        # Load room types first.
        for rt in data.room_types.keys():
            cursor.execute("INSERT INTO room_type (id, code, description) VALUES (?, ?, ?)", (data.room_types[rt]['id'], rt, data.room_types[rt]['name']))
        cursor.connection.commit()

        # First, we load the hotels.
        hotel: Hotel
        self.set_identity_insert("property", True)
        self.set_identity_insert("property_rooms", True)
        for hotel in tqdm.tqdm(state['hotels'], desc="Loading properties"):
            cursor.execute("""
                INSERT INTO property (id, name, street_address, city, state, zip, email, website, phone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                hotel.id,
                hotel.name,
                hotel.street,
                hotel.city,
                hotel.state,
                hotel.zip,
                hotel.email,
                hotel.website,
                hotel.phone
            ))

            for rt, room_info in hotel.rooms.items():
                # First, ensure the room type exists (lookup by code, not description)
                cursor.execute("""
                    SELECT id FROM room_type WHERE code = ?;
                """, (rt,))
                row = cursor.fetchone()
                if row is None:
                    # Insert it with both code and description
                    rt_name = data.room_types.get(rt, {}).get('name', rt)
                    cursor.execute("""
                        INSERT INTO room_type (code, description) VALUES (?, ?);
                    """, (rt, rt_name))
                    room_type_id = cursor.lastrowid
                else:
                    room_type_id = row[0]

                # Now insert the property_rooms record (use hotel.id, not lastrowid)
                cursor.execute("""
                    INSERT INTO property_rooms (property_id, room_type_id, count, price, resort_fee)
                    VALUES (?, ?, ?, ?, ?);
                """, (
                    hotel.id,
                    room_type_id,
                    room_info.count,
                    room_info.price,
                    hotel.resort_fee
                ))
        cursor.connection.commit()
        self.set_identity_insert("property", False)
        self.set_identity_insert("property_rooms", False)

        # Now, load customers
        self.set_identity_insert("customer", True)        
        cust: Customer
        for cust in tqdm.tqdm(state['customers'], desc="Loading customers"):
            cursor.execute("""
                INSERT INTO customer (id, first_name, last_name, email, phone, address, city, state, zip)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                cust.id,
                cust.fname,
                cust.lname,
                cust.email,
                cust.phone,
                cust.street,
                cust.city,
                cust.state,
                cust.zip
            ))
        cursor.connection.commit()
        self.set_identity_insert("customer", False)

        # Lets now load the events (events are still dicts, not dataclasses)
        self.set_identity_insert("event", True)
        for event in tqdm.tqdm(state['events'], desc="Loading events"):
            if event['event'] == 'checkin':
                event_code = 'checkin'
                event_date = event['checkin_date']
            else:
                event_code = 'checkout'
                event_date = event['checkout_date']
            cursor.execute("""
                INSERT INTO event (customer_id, event_code, property_id, event_date)
                VALUES (?, ?, ?, ?);
            """, (
                event['customer_id'],
                event_code,
                event['property_id'],
                event_date
            ))
        cursor.connection.commit()
        self.set_identity_insert("event", False)

        # And finally the transactions
        self.set_identity_insert("transact", True)
        transaction: Transaction
        for transaction in tqdm.tqdm(state['transactions'], desc="Loading transactions"):
            # Parse payment method (e.g., "Visa xxxx-1234" -> method="Visa", stub="xxxx-1234")
            payment_parts = transaction.payment.method.split(' ', 1)
            payment_method = payment_parts[0]
            payment_card_stub = payment_parts[1] if len(payment_parts) > 1 else None

            cursor.execute("""
                INSERT INTO transact (transaction_date, customer_id, hotel_id, amount, payment_method, payment_card_stub)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (
                transaction.check_out_date,
                transaction.customer_id,
                transaction.hotel_id,
                transaction.total,
                payment_method,
                payment_card_stub
            ))
            transaction_id = cursor.lastrowid

            for line in transaction.line_items:
                cursor.execute("""
                    INSERT INTO transaction_line (transaction_id, description, amount_per, quantity)
                    VALUES (?, ?, ?, ?);
                """, (
                    transaction_id,
                    line.description,
                    line.amount_per,
                    line.quantity
                ))
        cursor.connection.commit()
        self.set_identity_insert("transact", False)

        print("Data load completed!")
    