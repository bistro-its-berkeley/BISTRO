import pandas as pd
from pathlib import Path
import numpy as np
import os

# Ensures that the program is being run from the right repository, i.e the one containing the build.gradle file.
assert (Path(Path.cwd()).parent / "build.gradle").exists(), "Wrong directory. Python should be run from the " \
                                                          "BeamCompetitions root directory"


class Inputs:
    """Utility to import default input DataFrames with common characteristics.

    """
    def __init__(self,
                 path_directory=os.getcwd(),
                 route_id_217=np.arange(1340, 1352).tolist(),
                 buses_available=["BUS-DEFAULT", "BUS-SMALL-HD", "BUS-STD-HD", "BUS-STD-ART"],
                 modes_to_incentivise=["car", "walk", "ride_hail", "drive_transit", "walk_transit"]):

        self.path_directory = path_directory
        self.route_id = route_id_217
        self.buses_available = buses_available
        self.agencies = [217] * len(self.route_id)
        self.modes_to_incentivise = modes_to_incentivise

    def create_default_data_frames(self):
        """Build the BAU input files to be able to modify them and save them afterwards.

        Returns
        -------
        veh_type_input, pandas DataFrame:
            Gathers the vehicle fleet mix inputs, as described in the Starter Kit documentation.

        incentives_input, pandas DataFrame:
            Gathers the incentives inputs, as described in the Starter Kit documentation.

        road_pricing_input, pandas DataFrame:
            Gathers the road pricing inputs, as described in the Starter Kit documentation.

        frequency_input, pandas DataFrame:
            Gathers the frequency adjustments inputs, as described in the Starter Kit documentation.

        """

        # Get the VehType input file
        vehicle_type_id_bau = [None] * len(self.route_id)
        vehicle_type_input = pd.DataFrame({"agencyId": self.agencies, "routeId": self.route_id,
                                           "vehicleTypeId": vehicle_type_id_bau}).set_index("agencyId")

        # Get the Incentives input file
        incentives_input = pd.DataFrame(columns=["mode", "age", "income", "amount"]).set_index("mode")

        # Get the road pricing input file
        road_pricing_input = pd.DataFrame(columns=["linkId", "toll", "timeRange"]).set_index("linkId")

        # Get the frequency adjustment file
        frequency_input = pd.DataFrame(columns=["trip_id", "start_time", "emd_time", "headway_secs", "exact_times"])\
            .set_index("trip_id")

        return vehicle_type_input, incentives_input, road_pricing_input, frequency_input


def change_vehicle_fleet_mix():
    """ Automatically generates a list of input dictionaries, differing from the vehicle fleet mix.

    Each of these inputs dictionary will be later saved into a csv file to be able to launch s simulation for each
    of them so that their outputs can be compared.

    Returns
    -------
    List of input dictionaries
    """
    # Create the bus input file
    input_sets_list = []

    a = Inputs()

    # for transport_type, n_buslines in zip([a.buses_available[3],
    #                                        a.buses_available[3],
    #                                        a.buses_available[3],
    #                                        a.buses_available[2],
    #                                        a.buses_available[1]],
    #                                       [3, 6, 12, 12, 12]):
    # @Sid: Not sure if zip preserves order during iteration?
    for transport_type, n_bus_lines in zip([a.buses_available[3],
                                           a.buses_available[1]],
                                           [12, 12]):
        veh_type_input, incentives_input, road_pricing_input, frequency_input = \
            a.create_default_data_frames()
        veh_type_input["vehicleTypeId"].iloc[:n_bus_lines] = transport_type

        inputs_fleet_mix = {
            "VehicleFleetMix": veh_type_input,
            "ModeIncentives": incentives_input,
            "FrequencyAdjustment": frequency_input,
            "RoadPricing": road_pricing_input
        }

        input_sets_list.append(inputs_fleet_mix)

    return input_sets_list
