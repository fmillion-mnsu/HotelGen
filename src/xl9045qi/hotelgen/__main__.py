# Generate the database for a hotel chain in a live MSSQL database

import argparse
from xl9045qi.hotelgen.generator import HotelGen

import mssql_python as mssql
from yaml import safe_load

def main():

    print()
    print("  Hospitality Chain Simulation Generator  v0.1")
    print("  (C)  2025-2026 Flint Million PhD")
    print("  For use in CIS 444/544 courses at Minnesota State University, Mankato")
    print()

    parser = argparse.ArgumentParser(description="Generate the database for a hotel chain in a live MSSQL database")
    parser.add_argument("JOBFILE",nargs="?",default="dev/cis444-s26.job.yaml",help="Path to hotelgen YAML job file for the run")
    parser.add_argument("--drop",action="store_true",help="Drop existing tables before creating new ones")

    args = parser.parse_args()

    print("Reading job: " + args.JOBFILE)
    job = safe_load(open(args.JOBFILE,"r"))["job"]

    print("Initializing generator...")
    generator = HotelGen(job)

    # Start the generation process
    generator.start()

    import pickle
    open("FINAL.pkl","wb").write(pickle.dumps(generator.state))
    exit(0)

    # Try to connect first
    print("Connecting to the database...",end="",flush=True)

    try:
        conn = mssql.connect(
            server=job["database"]["host"],   
            uid=job["database"]["username"],
            pwd=job["database"]["password"],
            database=job["database"]["dbname"],
            encrypt="yes",
            trust_server_certificate="yes"
        )
    except Exception as e:
        print("failed.")
        print("ERROR: Could not connect to the database.")
        print("       " + str(e))
        print()
        return
    
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
        print("WARNING: The database already contains existing tables.")
        print("         Use the --drop option to drop existing tables before creating new ones.")
        print()
        return
    
if __name__ == "__main__":
    main()