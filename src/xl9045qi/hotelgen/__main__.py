# Generate the database for a hotel chain in a live MSSQL database

import argparse
import os
import os.path

import tqdm
from yaml import safe_load

import xl9045qi.hotelgen.simulation as sim
from xl9045qi.hotelgen.loaders import mssql

def main():

    print()
    print("  Hospitality Chain Simulation Generator  v0.1")
    print("  (C)  2025-2026 Flint Million PhD")
    print("  For use in CIS 444/544 courses at Minnesota State University, Mankato")
    print()

    parser = argparse.ArgumentParser(description="Generate the database for a hotel chain in a live MSSQL database")
    parser.add_argument("JOBFILE",nargs="?",default="dev/cis444-s26.job.yaml",help="Path to hotelgen YAML job file for the run")
    parser.add_argument("--drop",action="store_true",help="Drop existing tables before creating new ones")
    parser.add_argument("-o","--output",type=str,default="hotelgen_output.pkl",help="Path to output pickle file")
    parser.add_argument("-i","--input",type=str,help="Path to input pickle file to resume from")
    parser.add_argument("--no-database",action="store_true",help="Do not load data into the database; instead, only produce the output .pkl file")
    args = parser.parse_args()

    print("Reading job: " + args.JOBFILE)
    job = safe_load(open(args.JOBFILE,"r"))["job"]

    output_path = os.path.abspath(args.output)
    print("Output will be written to: " + output_path)

    if not args.no_database:
        db = mssql.DatabaseLoader(job)
        try:
            db.connect()
            if args.drop:
                print("Dropping existing tables...")
                db.drop_all_tables()
            print("Creating database tables...")
            db.make_schema()

        except Exception as e:
            print("ERROR: Could not initialize database.")
            print("To generate data without loading to a database, use --no-database.")
            print(str(e))
            exit(1)

    if args.input is not None:
        input_path = os.path.abspath(args.input)
        print("Resuming from input file: " + input_path)
        generator = sim.HGSimulationState(job)
        generator.import_pkl(input_path)
    else:
        print("Initializing generator...")
        generator = sim.HGSimulationState(job)

    counter = 0
    for phase in sim.PHASES:
        print()
        print(f"=== Running Phase {counter} ===")
        phase(generator)
        #generator.export(f"{counter:02d}.pkl")
        counter += 1



    print("Writing output to " + output_path)
    generator.export(output_path)

    if args.no_database:
        print("Skipping database load.")
        print(f"Output has been written to {output_path}.")
        print("You can import this into your database by executing:\n")
        print(f"  hotelgen -i {output_path}\n")

    else:
        print("Loading data into database...")
        db.load_data(generator.state)

    print("Exiting program.")
    os._exit(0)

if __name__ == "__main__":
    main()