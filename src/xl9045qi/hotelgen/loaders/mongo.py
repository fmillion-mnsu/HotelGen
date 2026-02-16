import dataclasses

import pymongo
import tqdm


def chunked_insert(collection, docs, chunk_size=10000, desc="Inserting"):
    """Insert documents in chunks, showing progress."""
    total = len(docs)
    for i in tqdm.tqdm(range(0, total, chunk_size), desc=desc, unit="chunk"):
        chunk = docs[i:i + chunk_size]
        collection.insert_many(chunk)
    return total


class MongoDatabaseLoader():

    def __init__(self, job: dict):
        self.job = job
        self._url = job["database"]["mongo"]["url"]

    def check_should_run(self, state: dict):
        return state.get("load_state", {}).get("mongodb", 0) == 0

    def connect(self) -> bool:
        print("Connecting to MongoDB...", end="", flush=True)
        try:
            self._client = pymongo.MongoClient(self._url)
            # Extract database name from the URL
            self._db = self._client.get_default_database()
            # Verify the connection works
            self._client.admin.command("ping")
        except Exception as e:
            print("failed.")
            print("ERROR: Could not connect to MongoDB.")
            print("       " + str(e))
            print()
            return False

        print("OK.")
        return True

    def drop_all_tables(self):
        """Drop all gift-shop related collections."""
        for name in ["shops", "products", "customers", "transactions"]:
            self._db.drop_collection(name)

    def make_schema(self):
        """No-op for MongoDB — collections are created on first insert."""
        pass

    def load_data(self, state: dict):
        """Load gift-shop data into MongoDB."""

        # -- shops --
        print("Loading shops...")
        shop_docs = [dataclasses.asdict(s) for s in state['giftshops']]
        if shop_docs:
            self._db.shops.insert_many(shop_docs)
        print(f"  Inserted {len(shop_docs)} shops")

        # -- products --
        print("Loading products...")
        product_docs = [dataclasses.asdict(p) for p in state['products']]
        if product_docs:
            chunked_insert(self._db.products, product_docs, desc="Loading products")
        print(f"  Inserted {len(product_docs)} products")

        # -- customers --
        print("Loading customers...")
        customers_by_id = state['cache'].get('retail_customers_by_id', {})
        customer_docs = [dataclasses.asdict(c) for c in customers_by_id.values()]
        # Remove the "main_customer_id" field from all customer docs
        for doc in customer_docs:
            del doc['main_customer_id']
        if customer_docs:
            chunked_insert(self._db.customers, customer_docs, desc="Loading customers")
        print(f"  Inserted {len(customer_docs)} customers")

        # -- transactions (with embedded customer) --
        print("Loading transactions...")
        transaction_docs = []
        for i, txn in enumerate(state['retail_transactions']):
            doc = dataclasses.asdict(txn)
            # Embed the full customer document
            cust = customers_by_id.get(txn.customer_id)
            doc['customer'] = dataclasses.asdict(cust) if cust else None
            del(doc['customer_id'])
            doc['id'] = i
            transaction_docs.append(doc)

        if transaction_docs:
            chunked_insert(self._db.transactions, transaction_docs, chunk_size=50000, desc="Loading transactions")
        print(f"  Inserted {len(transaction_docs)} transactions")

        print("MongoDB data load completed!")

        state['load_state'] = state.get('load_state', {})
        state['load_state']['mongodb'] = 1
