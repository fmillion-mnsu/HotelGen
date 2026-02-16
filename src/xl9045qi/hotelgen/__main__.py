# Generate the database for a hotel chain in a live MSSQL database

import argparse
import os
import os.path

from pydantic import TypeAdapter
from yaml import safe_load

import xl9045qi.hotelgen.simulation as sim
import xl9045qi.hotelgen.loaders as ld

# Semaphore at exit is harmless
import warnings
warnings.filterwarnings("ignore", message="resource_tracker:")

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
    parser.add_argument("--checkpoints",action="store_true",help="Save checkpoints in the output directory after each phase")
    parser.add_argument("--no-database",action="store_true",help="Do not load data into the database; instead, only produce the output .pkl file")
    parser.add_argument("--db_assume_complete", type=str, metavar="DB", help="Assume the load for database DB is complete even if the state says otherwise")

    args = parser.parse_args()

    print("Reading job: " + args.JOBFILE)
    job = safe_load(open(args.JOBFILE,"r"))["job"]

    output_path = os.path.abspath(args.output)
    print("Output will be written to: " + output_path)
    output_dir = os.path.dirname(output_path)
    if args.checkpoints:
        print("Checkpoints will be saved to: " + output_dir)

    if args.input is not None:
        input_path = os.path.abspath(args.input)
        print("Resuming from input file: " + input_path)
        generator = sim.HGSimulationState(job)
        try:
            generator.import_pkl(input_path)
        except Exception as e:
            print("ERROR: Could not import from input file.")
            print(str(e))
            exit(1)
        if "data_version" not in generator.state:
            dv = 0
        else:
            dv = generator.state["data_version"]
        
        if dv < 1:
            print("ERROR: Input file is too old (data version 0). Please use migration tool.")
            exit(1)

        generator.job = job # Replace job in case ours is newer
    else:
        print("Initializing generator...")
        generator = sim.HGSimulationState(job)

    counter = 0
    for phase in sim.PHASES:
        print()
        print(f"=== Running Phase {counter} ===")
        success = phase(generator)
        if args.checkpoints:
            if success:
                ckpt_name = os.path.splitext(os.path.basename(output_path))[0] + f"_p{counter:02d}.pkl"
                generator.export(os.path.join(output_dir, ckpt_name))
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

        for loader_class in ld.LOADERS:
            db = loader_class(job)
            try:
                print(f"Database {db.__class__.__name__}:")
                db.connect()
                if args.drop:
                    print("  Dropping existing tables...")
                    db.drop_all_tables()
                print("  Creating database tables...")
                db.make_schema()

            except Exception as e:
                print("ERROR: Could not initialize database.")
                print("To generate data without loading to a database, use --no-database.")
                print(str(e))
                exit(1)
            
            print("  Loading data...")
            db.load_data(generator.state)

    print("Exiting program.")
    os._exit(0)

if __name__ == "__main__":
    main()