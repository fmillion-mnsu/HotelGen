import tqdm
from rich import print
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from xl9045qi.hotelgen.simulation import HGSimulationState
import xl9045qi.hotelgen.simulation as sim

def phase4(inst: HGSimulationState) -> bool:

    if inst.state.get("last_phase", -1) >= 4:
        print("[bold]Phase 4 already completed, skipping.")
        return False

    for n in tqdm.tqdm(range(inst.state['days_left']),desc="Running Simulation"):
        sim.process_day(inst)
        inst.state['days_left'] -= 1
    inst.state['last_phase'] = 4

    return True