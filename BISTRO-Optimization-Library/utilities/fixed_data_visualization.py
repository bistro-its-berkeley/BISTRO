from pathlib import Path
import pandas as pd
import visualization as viz
import plans_parser as parser


REFERENCE_DATA = "reference-data"
AGENCY = "sioux_faux_bus_lines"
CONFIG = "config"
EXAMPLES = "examples"
COMPETITION = "competition"
SUBMISSION_INPUTS = "submission-inputs"
ITERS = "ITERS"


max_incentive = 50
max_income = 150000
max_age = 120
max_fare = 10
transit_scale_factor = 0.1

poi_types = ['work', 'secondary']
time_ranges = {'morning peak': range(7, 10), "evening peak": range(17, 20)}
max_time = 900
utm_zone = "14N"


class ReferenceData(object):

    def __init__(self, sample_size, scenario_name="sioux_faux", transit_scale_factor=0.1):
        """

        Parameters
        ----------
        reference_data_path : Path
            Directory containing the scenario's reference-data
        """
        # Scale factor to compare the 15k to the 157k scenario (full population)
        self.transit_scale_factor = transit_scale_factor

        # Importing agencies ids from agency.txt
        agency_ids = pd.read_csv(Path.cwd().parent / REFERENCE_DATA / scenario_name / AGENCY / "gtfs_data/agency.txt")
        self.agency_ids = agency_ids["agency_id"].tolist()

        # Importing route ids from `routes.txt`
        route_df = pd.read_csv(Path.cwd().parent / REFERENCE_DATA / scenario_name / AGENCY /"gtfs_data/routes.txt")
        self.route_ids = route_df["route_id"].sort_values(ascending=True).tolist()

        # Importing vehicle types and seating capacities from `availableVehicleTypes.csv` file
        self.available_vehicle_types = pd.read_csv(Path.cwd().parent / REFERENCE_DATA /
                                                   scenario_name / AGENCY /"availableVehicleTypes.csv")

        self.buses_list = self.available_vehicle_types["vehicleTypeId"][1:].tolist()
        self.seating_capacities = self.available_vehicle_types[["vehicleTypeId", "seatingCapacity"]].\
                                                    set_index("vehicleTypeId", drop=True).T.to_dict("records")[0]

        # Extracting Operational costs per bus type from the `vehicleCosts.csv` file
        operational_costs = pd.read_csv(Path.cwd().parent / REFERENCE_DATA / scenario_name / AGENCY / "vehicleCosts.csv")
        self.operational_costs = operational_costs[["vehicleTypeId", "opAndMaintCost"]].\
                                                    set_index("vehicleTypeId", drop=True).T.to_dict("records")[0]

        # Extracting route_id / trip_id correspondence from the `trips.csv` file
        trips = pd.read_csv(Path.cwd().parent / REFERENCE_DATA / scenario_name / AGENCY / "gtfs_data/trips.txt")
        self.trip_to_route = trips[["trip_id", "route_id"]].set_index("trip_id", drop=True).T.to_dict('records')[0]


        #Extracting Fuel cost from the `beamFuelTypes.csv` file
        fuel_costs = pd.read_csv(Path.cwd().parent / REFERENCE_DATA / scenario_name / CONFIG / sample_size / "beamFuelTypes.csv")
        fuel_costs.loc[len(fuel_costs)] = ["food", 0]
        self.fuel_costs = fuel_costs.set_index("fuelTypeId", drop=True).T.to_dict('records')[0]

        # PATHS TO BAU DATA
        # 1.ouput folder
        path_output_folder_bau = (Path.cwd().parent / REFERENCE_DATA / scenario_name /
                                  f"bau/warm-start/sioux_faux-{sample_size}__warm-start").absolute()
        self.path_output_folder_bau = viz.unzip_file(path_output_folder_bau)

        # 2. Network and population files
        self.path_network_file = Path.cwd().parent / REFERENCE_DATA /scenario_name / CONFIG/ "physsim-network.xml"
        self.path_population_file = Path.cwd().parent / REFERENCE_DATA /scenario_name / CONFIG / f"{sample_size}/population.xml.gz"


class ResultFiles:
    def __init__(self, path_output_folder, number_iterations, reference_data: ReferenceData):

        self.path_output_folder = path_output_folder
        self.number_iterations = number_iterations
        self.reference_data = reference_data

        # Extracting input data from the submission input csv files
        self.bus_fares_data = pd.read_csv(path_output_folder / COMPETITION / SUBMISSION_INPUTS / "MassTransitFares.csv")
        self.incentives_data = pd.read_csv(path_output_folder / COMPETITION / SUBMISSION_INPUTS / "ModeIncentives.csv")
        self.fleet_mix_data = pd.read_csv(path_output_folder / COMPETITION / SUBMISSION_INPUTS / "VehicleFleetMix.csv")
        self.bus_frequency_data = pd.read_csv(path_output_folder / COMPETITION / SUBMISSION_INPUTS / "FrequencyAdjustment.csv")

        # Extracting output data
        self.scores_data = pd.read_csv(path_output_folder/ COMPETITION / "submissionScores.csv")
        self.mode_choice_data = pd.read_csv(path_output_folder / "modeChoice.csv")

        # Getting the csv data from the xml files
        self.process_all_xml_files()

    def process_all_xml_files(self):
        """ Import all xml.gz files from the output folder of the scenario, parse them and create .csv files"

        """

        self.events_path = self.path_output_folder / ITERS / "it.{0}".format(self.number_iterations) / \
                           "{0}.events.csv.gz".format(self.number_iterations)
        self.output_plans_path = self.path_output_folder / "outputPlans.xml.gz"
        self.experienced_plans_path = self.path_output_folder / ITERS / "it.{0}".format(self.number_iterations) \
                                      / "{0}.experiencedPlans.xml.gz".format(self.number_iterations)
        self.persons_path = self.path_output_folder / "outputPersonAttributes.xml.gz"
        self.households_path = self.path_output_folder / "outputHouseholds.xml.gz"

        if not Path(self.path_output_folder / "trips_dataframe.csv").exists():
            # Parsing and creating the csv files in the output folder
            parser.output_parse(self.events_path, self.output_plans_path, self.persons_path, self.households_path,
                                self.experienced_plans_path, self.bus_fares_data, self.reference_data.route_ids,
                                self.reference_data.trip_to_route, self.reference_data.fuel_costs, self.path_output_folder)

        # Get the data from the generated csv files
        self.trips_df = pd.read_csv(self.path_output_folder / "trips_dataframe.csv")
        self.person_df = pd.read_csv(self.path_output_folder / "persons_dataframe.csv")
        self.activities_df = pd.read_csv(self.path_output_folder / "activities_dataframe.csv")
        self.legs_df = pd.read_csv(self.path_output_folder / "legs_dataframe.csv")
        self.paths_traversals_df = pd.read_csv(self.path_output_folder / "path_traversals_dataframe.csv")