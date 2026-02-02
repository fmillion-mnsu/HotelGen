import mssql_python as mssql

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
        "id": "INT PRIMARY KEY IDENTITY(1,1)",
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
    "transaction": {
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
    }
}

class DatabaseLoader():
    
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

        # Determine if there are any objects in the database beyond system objects (i.e. any tables)
        cursor = conn.cursor()
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
            print()
            print("ERROR: The database already contains existing tables.")
            print()
            return False

        self._conn = conn
        return True

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
            print(f"Creating table {table}...",end="",flush=True)
            cursor = self._conn.cursor()
            cursor.execute(create_sql)
            self._conn.commit()
            print("OK.")