"""Utility functions to sample random inputs for execution in Uber Prize.

Example
-------
Provide the root to the data directory and select a scenario:

{{
    # By default, this is /reference-data in the root of this repository
    ROOT_DATA_DIR = <path_to_data_dir_as_string>
}}

Get the mapping of agencies to paths for this :

{{
    SCENARIO_NAME = 'sioux_faux'
    agency_dict = scenario_agencies(DATA_DIR, SCENARIO_NAME)
}}

Here's how to generate a sample of 5 records from each of the input samplers for an agency as
separate Pandas `DataFrame`s. For illustrative purposes, we only one agency (the only one in
Sioux Faux), but you can just iterate through the agency mapping if more agencies are desired:

    {{
    agency = 'sioux_faux_bus_lines'
    agency_dict = scenario_agencies(DATA_DIR,{}.format(SCENARIO_NAME))
    # Create a lazy cache of GTFS data for the agency:
    sf_gtfs_manager = AgencyGtfsDataManager(agency_dict[agency])

    freq_df = sample_frequency_adjustments(num_records, sf_gtfs_manager)
    mode_incentive_df = sample_mode_incentives(num_records)
    vehicle_fleet_mix_df = sample_vehicle_fleet_mix(num_records, sf_gtfs_manager)
    }}

Write each dataframe of samples to file using <input_df>.to_csv(<filename>, index=None) if desired.
"""

from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from utils import lazyprop

MASS_TRANSIT_FARE_FILE = "MassTransitFares.csv"

AGE_RANGE_LOWER = np.array([i for i in range(1, 116, 5)])
AGE_RANGE_UPPER = np.array([i for i in range(5, 120, 5)])
INCOME_RANGE_LOWER = np.array([0] + [i for i in range(5000, 150000, 5000)])
INCOME_RANGE_UPPER = np.array([i for i in range(4999, 149999, 5000)] + [150000])


def scenario_agencies(data_dir, scenario_name):
    """Given root data directory and scenario name, computes a mapping
    of agency names to their respective paths.

    Parameters
    ----------
    data_dir : Path
        Absolute path to root of data directory
    scenario_name : str
        Name of scenario with GTFS data

    Returns
    -------
    dict
        Dictionary of agency names mapped to directories containing files comprising their GTFS
        data.
    """
    gtfs_root = (data_dir / scenario_name).absolute()
    return {p.stem: p for p in
            gtfs_root.iterdir()}


class AgencyGtfsDataManager(object):

    def __init__(self, agency_gtfs_path):
        """Used to cache an agency's GTFS data for sampling purposes

        Parameters
        ----------
        agency_gtfs_path : pahtlib.Path object
            Directory containing the agency's gtfs data
        """

        self.agency_gtfs_path = agency_gtfs_path

    @lazyprop
    def routes(self):
        return pd.read_csv(self.agency_gtfs_path / "gtfs_data/routes.txt", header=0, index_col=1,
                           na_values=None,
                           delimiter=',')

    @lazyprop
    def vehicle_types(self):
        return pd.read_csv(self.agency_gtfs_path / "availableVehicleTypes.csv", header=0,
                           index_col=0, na_values=None,
                           delimiter=',')

    @lazyprop
    def trips(self):
        return pd.read_csv(self.agency_gtfs_path / "gtfs_data/trips.txt", header=0, index_col=2,
                           na_values=None,
                           delimiter=',')


def sample_vehicle_fleet_mix_input(num_records, gtfs_manager, bus_set=None):
    """Generate random `VehicleFleetMix` input according to possible substitute
    vehicle trip ids available for an agency.

    Parameters
    ----------
    num_records : int
        Number of randomly sampled records to create.
    gtfs_manager : `AgencyGtfsDataManager`
        An instance of the `AgencyGtfsDataManager` for the target agency.
    bus_set : list of strings
        A list of possible bus types that we want to sample from if we don't want to sample from all
        bus types. If bus_set = None samples from all bus types

    Returns
    -------
    `pd.DataFrame`
        `num_records` `VehicleFleetMix` records. These are unique by `routeId`
        for the `agencyId` specified on the `gtfs_manager`

    Raises
    ------
    `ValueError`
        If the `num_records` is in excess of the number of routes that an agency schedules buses on.
    """
    df_columns = ["agencyId", "routeId", "vehicleTypeId"]
    if num_records == 0:
        return pd.DataFrame({k: [] for k in df_columns})

    max_num_routes = gtfs_manager.routes.shape[0]
    if num_records > max_num_routes:
        raise ValueError(
            "More samples requested than the number of routes available in agency; please enter a "
            "number less than {}".format(
                max_num_routes))
    route_agency_sample = gtfs_manager.routes.sample(num_records)
    routes = pd.Series(route_agency_sample.index.values)
    agency = pd.Series(route_agency_sample.agency_id.values)
    if bus_set is None:
        vehicles = pd.Series((gtfs_manager.vehicle_types.filter(like="BUS", axis=0))
                             .sample(num_records, replace=True).index)
    else:
        vehicles = pd.Series(bus_set).sample(num_records, replace=True).reset_index(drop=True)
    df = pd.concat([agency, routes, vehicles], axis=1, ignore_index=True)
    df.columns = df_columns
    return df


def _sample_census_interval(census_type):
    if census_type == "age":
        eps = AGE_RANGE_LOWER, AGE_RANGE_UPPER
    elif census_type == "income":
        eps = INCOME_RANGE_LOWER, INCOME_RANGE_UPPER
    else:
        raise ValueError("Undefined census type!")
    right_ep = np.random.choice(eps[1])
    left_ep = np.random.choice(eps[0][eps[0] < right_ep])
    return "[{}:{}]".format(left_ep, right_ep)


def sample_frequency_adjustment_input(num_service_periods, gtfs_manager):
    """Generate random `FrequencyAdjustment` inputs according to trips run by
    an agency.

    Creates `num_records` frequency adjustment records where fields for each record where the
    `headway_secs` field is randomly chosen from a range of between `min_headway_seconds`
    (per the route.txt file in the corresponding gtfs data for the trip) and 7200
    seconds at intervals of 60 seconds and the `min_time` and `max_time` field
    are sampled between the 0 and 86340 seconds, respectively (i.e.,
    the possible minimum and maximum number of seconds in a day of 86359
    seconds, given the headway interval).

    Note that a frequency adjustment is really tied to a route based on a particular trip.
    The trip serves as a template for the frequency adjustment. See the documentation
    for further details.

    Parameters
    ----------
    num_service_periods : int
        Number of service periods with a new headway that can be added to a route.
    gtfs_manager : `AgencyGtfsDataManager`
        An instance of the `AgencyGtfsDataManager` for the target agency.

    Returns
    -------
    `pd.DataFrame`
        `num_records` `FrequencyAdjustmentInput` records.
    """
    if num_service_periods > 5:
        raise ValueError(
            "The maximum number of service periods per route is equal to {0} although it should not exceed 5.".format(
                num_service_periods))

    df_columns = ['route_id', 'start_time', 'end_time', 'headway_secs']

    grouped = [np.random.randint(num_service_periods) * [route_id] for route_id in
               gtfs_manager.routes.index.values.astype(int)]
    route_id_list = [i for j in grouped for i in j]

    min_secs = 0
    max_secs = 86399
    min_headway_seconds = 180
    max_headway_seconds = 7199

    frequency_data = []
    route_frequency = Counter(route_id_list).items()
    for route_id, route_num_service_periods in route_frequency:
        st_et_flat = np.sort(
            np.random.choice(np.arange(min_secs, max_secs, 60), route_num_service_periods, replace=False))

        for st, et in zip(st_et_flat, st_et_flat[1:]):
            headway = np.random.choice(np.arange(min_headway_seconds, max_headway_seconds, 60))
            frequency_data.append([route_id, st, et, headway])

    frequency_adjustment_df = pd.DataFrame(frequency_data, columns=df_columns)
    frequency_adjustment_df['exact_times'] = 0
    return frequency_adjustment_df


def sample_mode_incentives_input(num_records, gtfs_manager=None, min_incentive=0.1, max_incentive=50):
    """Generate random mode incentives inputs based on modes available for
    subsidies.

    Creates `num_records` ModeIncentivesInput records where fields for each record
    are randomly sampled as follows:
        * `age` : an interval with age values sampled uniformly from [1 .. 116]\cup[120] inclusive, in steps of 5.
        * `mode` : uniformly from list of available modes for scenario.
        * `income` : an interval with income values sampled uniformly from integers values
           [0 to 144,999]\cup[150,000] in steps of 5,000.
        * `amount` : uniformly from `range(0.1,50)`.

    The amount of subsidy is rounded to the nearest $0.10.

    Parameters
    ----------
    num_records : int
        Number of randomly sampled records to create.

    gtfs_manager : `AgencyGtfsDataManager`, optional
        An instance of the `AgencyGtfsDataManager` for the target agency.

    min_incentive : float
        Minimum amount accepted for an incentive according to the inputs specifications of the Starter-Kit

    max_incentive : float
        Maximum amount accepted for an incentive according to the inputs specifications of the Starter-Kit

    Notes
    -----
    `gtfs_manager` added to support duck-typing this field.

    Returns
    -------
    `DataFrame`
        `num_records` `ModeIncentivesInput` records.

    """
    df_columns = ['mode', 'age', 'income', 'amount']
    if num_records == 0:
        return pd.DataFrame({k: [] for k in df_columns})
    possible_modes = ['OnDemand_ride', 'walk_transit', 'drive_transit']
    modes = np.random.choice(possible_modes, num_records).tolist()
    ages = [_sample_census_interval("age") for _ in range(num_records)]
    incomes = [_sample_census_interval("income") for _ in range(num_records)]
    amounts = [np.round(np.random.uniform(min_incentive, max_incentive), 1) for _ in range(num_records)]
    return pd.DataFrame(np.array([modes, ages, incomes, amounts]).T,
                        columns=df_columns)


def sample_mass_transit_fares_input(num_records, gtfs_manager, max_fare_amount=10.0):
    """Generate `num_records` random `PtFares` for an
    agency (specified within `gtfs_manager`) by randomly sampling age and fare amount.

    The fare amount will not exceed the maximum fare amount and cannot be less than $0.10 (else,
    there shouldn't have been a fare assigned in the first place).

    The age will be sampled from 1 to 120 inclusive (maximum age in scenario).

    Parameters
    ----------
    num_records : int
        Number of randomly sampled records to create.
    gtfs_manager : `AgencyGtfsDataManager`
        An instance of the `AgencyGtfsDataManager` for the target agency.
    max_fare_amount : float
        The maximum fare amount that should be charged.

    Returns
    -------
    `pd.DataFrame`
        `num_records` `PtFares` records. These are unique by `routeId`
        for the `agencyId` specified on the `gtfs_manager`

    Raises
    ------
    `ValueError`
        If the `num_records` is in excess of the number of routes that an agency schedules
        buses on.
    """

    df_columns = ['agencyId', 'routeId', 'age', 'amount']
    if num_records == 0:
        return pd.read_csv('../submission-inputs/{0}'.format(MASS_TRANSIT_FARE_FILE))
    max_num_routes = gtfs_manager.routes.shape[0]
    if num_records > max_num_routes:
        raise ValueError(
            "More samples requested than the number of routes available in agency; please enter a "
            "number less than {}".format(max_num_routes))
    route_agency_sample = gtfs_manager.routes.sample(num_records)
    routes = pd.Series(route_agency_sample.index.values)
    agency = pd.Series(route_agency_sample.agency_id.values)
    amounts = [np.round(np.random.uniform(0.1, max_fare_amount), 1) for _ in range(num_records)]
    ages = [_sample_census_interval("age") for _ in range(num_records)]
    return pd.DataFrame(np.array([agency, routes, ages, amounts]).T,
                        columns=df_columns)
