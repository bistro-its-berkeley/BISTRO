import gzip
from pathlib import Path

import dask.dataframe as dd

import numpy as np
import pandas as pd

from data_parsing import extract_dataframe, open_xml


# ########### 1. INTERMEDIARY FUNCTIONS ###########

def unzip_file(path: Path):
    """ Unzips a file ending with .gz

    Parameters
    ----------
    path: pathlib.Path object or os.path object

    Returns
    -------
    path: string
        Path of the unzipped folder or file

    """

    if Path(path).suffix == ".gz":
        return gzip.open(path)
    else:
        return path


def parse_bus_fare_input(bus_fare_data_df, route_ids, max_age):
    """Processes the `MassTransitFares.csv` input file into a dataframe with rows = ages and columns = routes

    Parameters
    ----------
    bus_fare_data_df: pandas DataFrame
        Bus fares extracted from the "submission-inputs/MassTransitFares.csv"
    route_ids: list of strings
        All routes ids where buses operate (from `routes.txt` file in the GTFS data)
    max_age: int
        maximum age

    Returns
    -------
    bus_fare_per_route_df: pandas DataFrame
        Dataframe with rows = ages and columns = routes
    """

    bus_fare_per_route_df = pd.DataFrame(np.zeros((max_age + 1, len(route_ids))), columns=route_ids)

    routes = bus_fare_data_df['routeId'].unique()
    for r in routes:
        if np.isnan(r):
            cols = route_ids
            r_fares = bus_fare_data_df.loc[np.isnan(bus_fare_data_df['routeId']),]
        else:
            cols = int(r)
            r_fares = bus_fare_data_df.loc[bus_fare_data_df['routeId'] == r,]
        for i, row in r_fares.iterrows():
            age_group = row['age']
            left = age_group[0]
            ages = age_group[1:-1].split(':')
            right = age_group[-1]
            if left == '(':
                min_a = int(ages[0]) + 1
            else:
                min_a = int(ages[0])
            if right == ')':
                max_a = int(ages[1]) - 1
            else:
                max_a = int(ages[1])
            bus_fare_per_route_df.loc[min_a:max_a, cols] = float(row['amount'])

    return bus_fare_per_route_df


def parse_incentive_input(incentive_data, max_age, max_income):
    """Processes the `MassTransitFares.csv` input file into a dataframe with rows = ages and columns = routes

    Parameters
    ----------
    incentive_data: pandas DataFrame
        Incentives extracted from the "submission-inputs/ModeIncentives.csv"
    max_age: int
        maximum age
    max_income: int
        maximum income

    Returns
    -------
    incentive_dict: Dictionaries of pandas DataFrames {mode: incentive_per_age_income}
        incentive_per_age_income: Dataframe with rows = ages and columns = incomes
    """

    incentive_elligible = {"OnDemand_ride", "drive_transit", "walk_transit"}

    incentive_per_age_income = pd.DataFrame(np.zeros((max_age + 1, max_income + 1)))

    incentive_dict = {}
    for m in incentive_elligible:
        incentive_per_age_income = pd.DataFrame(np.zeros((max_age + 1, max_income + 1)))
        # get all incentive rows for this mode:
        m_incentives = incentive_data.loc[incentive_data['mode'] == m,]
        if len(m_incentives) > 0:
            for i, row in m_incentives.iterrows():
                age_group = row['age']
                income_group = row['income']

                left_a = age_group[0]
                ages = age_group[1:-1].split(':')
                right_a = age_group[-1]
                if left_a == '(':
                    min_a = int(ages[0]) + 1
                else:
                    min_a = int(ages[0])
                if right_a == ')':
                    max_a = int(ages[1]) - 1
                else:
                    max_a = int(ages[1])

                left_i = income_group[0]
                incomes = income_group[1:-1].split(':')
                right_i = income_group[-1]
                if left_i == '(':
                    min_i = int(incomes[0]) + 1
                else:
                    min_i = int(incomes[0])
                if right_i == ')':
                    max_i = int(incomes[1]) - 1
                else:
                    max_i = int(incomes[1])

                incentive_per_age_income.loc[min_a:max_a, min_i:max_i] = float(row['amount'])
        incentive_dict[m] = incentive_per_age_income

    return incentive_dict


def find_incentive(row, incentive_df, person_df):
    pid = row['PID']

    age = person_df.loc[pid, 'Age']
    income = person_df.loc[pid, 'income']

    incentive = incentive_df.loc[int(float(age)), int(float(income))]
    return incentive


def calc_incentives(trips_df, incentive_dict, person_df):
    # row: row from trips dataframe
    incentive_elligible = {"OnDemand_ride", "drive_transit", "walk_transit"}
    trips_df['Incentive'] = np.zeros((trips_df.shape[0]))
    for m in incentive_elligible:
        incentive_df = incentive_dict[m]
        these_trips = trips_df.loc[trips_df['realizedTripMode'] == m,]

        trips_df.loc[trips_df['realizedTripMode'] == m, 'Incentive'] = these_trips.apply(
            lambda x: find_incentive(x, incentive_df, person_df), axis=1)
    return trips_df


def calc_fuel_costs(legs_df, fuel_cost_dict):
    # legs_df: legs_dataframe
    # fuel_cost_dict: {fuel_type: $/MJoule}
    # returns: legs_df augmented with an additional column of estimated fuel costs

    legs_df.loc[:, "FuelCost"] = np.zeros(legs_df.shape[0])
    for f in fuel_cost_dict.keys():
        legs_df.loc[legs_df["primaryFuelType"] == f.capitalize(), "FuelCost"] = (pd.to_numeric(
            legs_df.loc[legs_df["primaryFuelType"] == f.capitalize(), "primaryFuel"]) * float(
            fuel_cost_dict[f])) / 1000000

    return legs_df


def calc_transit_fares(row, bus_fare_dict, person_df, trip_to_route):
    pid = row['PID']
    age = person_df.loc[pid, 'Age']
    vehicle = row['Veh']
    route = trip_to_route[vehicle.split(':')[1].split('-')[0]]
    fare = bus_fare_dict.loc[age, route]
    return fare


def calc_fares(legs_df, ride_hail_fares, bus_fare_dict, person_df, trip_to_route):
    # legs_df: legs_dataframe
    # ride_hail_fares: {'base': $, 'duration': $/hour, 'distance': $/km}
    # transit_fares isnt being used currently - would need to be updated to compute fare based on age
    # returns: legs_df augmented with an additional column of estimated transit and on-demand ride fares

    legs_df["Fare"] = np.zeros(legs_df.shape[0])

    legs_df.loc[legs_df["Mode"] == 'bus', "Fare"] = legs_df.loc[legs_df["Mode"] == 'bus'].apply(
        lambda row: calc_transit_fares(row, bus_fare_dict, person_df, trip_to_route), axis=1)

    legs_df.loc[legs_df["Mode"] == 'OnDemand_ride', "Fare"] = ride_hail_fares['base'] + (
            pd.to_timedelta(legs_df['Duration_sec']).dt.seconds / 60) * float(ride_hail_fares['duration']) + (
                                                                      pd.to_numeric(
                                                                          legs_df['Distance_m']) / 1000) * (
                                                                  0.621371) * float(ride_hail_fares['distance'])

    return legs_df


def one_path(path_trav, leg_id, pid, trip_id):
    # extracts leg data from path traversal
    # returns a leg_dataframe row

    l_row = path_trav
    leg_id_this = leg_id + l_row.name
    leg_id_full = trip_id + "_l-" + str(leg_id)
    veh_id = l_row["vehicle"]
    leg_start_time = l_row['departureTime']
    veh_type = l_row['vehicleType']
    distance = l_row['length']
    leg_end_time = l_row['arrivalTime']
    leg_duration = int(leg_end_time) - int(leg_start_time)
    leg_path = l_row['links']
    leg_mode = l_row['mode']
    leg_fuel = l_row['primaryFuel']
    leg_fuel_type = l_row['primaryFuelType']

    # return the leg record
    return [pid, trip_id, leg_id_full, leg_mode, veh_id, veh_type, leg_start_time, leg_end_time, leg_duration, distance,
            leg_path, leg_fuel, leg_fuel_type]


def parse_transit_trips(row, non_bus_path_traversal_events, bus_path_traversal_events, enter_veh_events):
    # inputs:
    # row: a row from transit_trips_df
    # path_traversal_events: non-transit path traversal df
    # bus_path_traversal_events: transit path traversal df
    # enter_veh_events: enter vehicle events

    leg_array = []
    pid = row['PID']
    trip_id = row['Trip_ID']
    start_time = row['Start_time'].total_seconds()
    duration = row['Duration_sec']
    end_time = row['End_time']
    mode = row['Mode']
    # initiate the leg ID counter
    leg_id = 0

    # get all path traversals occuring within the time frame of this trip in which the driver is the person making this trip
    path_trav = non_bus_path_traversal_events[
        (non_bus_path_traversal_events['driver'] == pid) & (
                    non_bus_path_traversal_events['arrivalTime'] <= end_time) & (
                non_bus_path_traversal_events['departureTime'] >= start_time)]
    path_trav = path_trav.reset_index(drop=True)

    # get the vehicle entry events corresponding to this person during the time frame of this trip
    veh_entries = enter_veh_events[
        (enter_veh_events['person'] == pid) & (enter_veh_events['time'] >= start_time) & (
                enter_veh_events['time'] <= end_time)]

    # get bus entry events for this person & trip
    bus_entries = veh_entries[veh_entries['vehicle'].str.startswith('siouxareametro-sd-us:', na=False)]
    bus_entries = bus_entries.reset_index(drop=True)

    if len(bus_entries) > 0:
        prev_entry_time = start_time
        for idx, bus_entry in bus_entries.iterrows():
            if idx < len(bus_entries) - 1:
                next_entry = bus_entries.loc[idx + 1]
                next_entry_time = next_entry['time']
            else:
                next_entry_time = end_time

            # get all path traversals occuring before the bus entry
            prev_path_trav = path_trav[
                (path_trav['arrivalTime'] <= bus_entry['time']) & (path_trav['arrivalTime'] >= prev_entry_time)]

            # get all path traversals occuring after the bus entry
            post_path_trav = path_trav[
                (path_trav['arrivalTime'] > bus_entry['time']) & (path_trav['arrivalTime'] <= next_entry_time)]
            prev_path_trav = prev_path_trav.reset_index(drop=True)
            post_path_trav = post_path_trav.reset_index(drop=True)
            prev_entry_time = bus_entry['time']

            # iterate through the path traversals prior to the bus entry

            if len(prev_path_trav) > 0:
                these_legs = prev_path_trav.apply(lambda row1: one_path(row1, leg_id, pid, trip_id), axis=1)
                leg_array.extend(these_legs)

            # record transit leg
            leg_id += 1
            leg_id_full = trip_id + "_l-" + str(leg_id)
            veh_id = bus_entry['vehicle']
            leg_start_time = int(bus_entry['time'])
            if len(post_path_trav) > 0:
                leg_end_time = int(post_path_trav['departureTime'].values[0])
                bus_path_trav = bus_path_traversal_events[(bus_path_traversal_events['vehicle'] == veh_id) & (
                        bus_path_traversal_events['arrivalTime'] <= leg_end_time) & (bus_path_traversal_events[
                                                                                         'departureTime'] >= leg_start_time)]
            else:
                leg_end_time = next_entry_time
                bus_path_trav = bus_path_traversal_events[(bus_path_traversal_events['vehicle'] == veh_id) & (
                        bus_path_traversal_events['arrivalTime'] < leg_end_time) & (bus_path_traversal_events[
                                                                                        'departureTime'] >= leg_start_time)]

            leg_duration = int(leg_end_time - bus_entry['time'])
            # find the path traversals of the bus corresponding to the bus entry for this trip, occuring between the last prev_path_traversal and the first post_path_traversal

            if len(bus_path_trav) > 0:
                veh_type = bus_path_trav['vehicleType'].values[0]
                distance = bus_path_trav['length'].sum()
                leg_path = [path['links'] for p, path in bus_path_trav.iterrows()]
                leg_mode = bus_path_trav['mode'].values[0]
                leg_fuel = 0
                leg_fuel_type = 'Diesel'
                leg_array.append(
                    [pid, trip_id, leg_id_full, leg_mode, veh_id, veh_type, leg_start_time, leg_end_time,
                     leg_duration,
                     distance, leg_path, leg_fuel, leg_fuel_type])

            # iterate through the path traversals after the bus entry
            if len(post_path_trav) > 0:
                these_legs = post_path_trav.apply(lambda row1: one_path(row1, leg_id, pid, trip_id), axis=1)
                leg_array.extend(these_legs)

    # if the agent underwent replanning, there will be no bus entry
    else:
        leg_array = parse_walk_car_trips(row, non_bus_path_traversal_events, enter_veh_events)

    return leg_array


def parse_walk_car_trips(row, path_traversal_events, enter_veh_events):
    # inputs:
    # row: a row from transit_trips_df
    # path_traversal_events: non-transit path traversal df
    # person_costs: person cost events df
    # enter_veh_events: enter vehicle events

    leg_array = []
    pid = row['PID']
    trip_id = row['Trip_ID']
    start_time = row['Start_time']
    duration = row['Duration_sec']
    end_time = row['End_time']
    mode = row['Mode']
    # initiate the leg ID counter
    leg_id = 0

    # get all path traversals occuring within the time frame of this trip in which the driver is the person making this trip

    path_trav = path_traversal_events.loc[
        (path_traversal_events['driver'] == pid) & (path_traversal_events['arrivalTime'] <= end_time) & (
                path_traversal_events['departureTime'] >= start_time.total_seconds()),]
    path_trav.reset_index(drop=True, inplace=True)
    # iterate through the path traversals
    if len(path_trav) > 0:
        these_legs = path_trav.apply(lambda row: one_path(row, leg_id, pid, trip_id), axis=1)
        leg_array.extend(these_legs)
    return leg_array


def parse_ridehail_trips(row, path_traversal_events, enter_veh_events):
    # inputs:
    # row: a row from transit_trips_df
    # path_traversal_events: non-transit path traversal df
    # person_costs: person cost events df
    # enter_veh_events: enter vehicle events
    # reserve_ridehail_events: ReserveRideHail events
    leg_array = []
    pid = row['PID']
    trip_id = row['Trip_ID']
    start_time = row['Start_time']
    duration = row['Duration_sec']
    end_time = row['End_time']
    mode = row['Mode']
    # initiate the leg ID counter
    leg_id = 0

    # get all vehicle entry events corresponding to this person during the time frame of this trip, not including those corresponding to a walking leg
    veh_entry = enter_veh_events.loc[
        (enter_veh_events['person'] == pid) & (enter_veh_events['time'] >= start_time.total_seconds()) & (
                enter_veh_events['time'] <= end_time),]
    veh_entry2 = veh_entry.loc[(veh_entry['vehicle'] != 'body-' + pid),]

    # reservation = reserve_ridehail_events.loc[(reserve_ridehail_events['person']==pid)&(reserve_ridehail_events['time'] >= start_time.total_seconds()) & (reserve_ridehail_events['time'] <= end_time),]

    try:
        veh_id = veh_entry2['vehicle'].item()
        leg_start_time = veh_entry2['time'].item()
        # get the path traversal corresponding to this ridehail trip
        path_trav = path_traversal_events.loc[(path_traversal_events['vehicle'] == veh_id) & (
                path_traversal_events['departureTime'] == int(leg_start_time)) & (
                                                          path_traversal_events['numPassengers'] > 0),]
    except:
        path_trav = []
        print(row)

    leg_id += 1
    # create leg ID
    leg_id_full = trip_id + "_l-" + str(leg_id)
    if len(path_trav) > 0:
        veh_type = path_trav['vehicleType'].values[0]
        distance = path_trav['length'].item()
        leg_end_time = path_trav['arrivalTime'].item()
        leg_duration = int(leg_end_time) - int(leg_start_time)
        leg_path = path_trav['links'].item()
        leg_mode = 'OnDemand_ride'
        leg_fuel = path_trav['primaryFuel'].item()
        leg_fuel_type = path_trav['primaryFuelType'].item()
        leg_array.append(
            [pid, trip_id, leg_id_full, leg_mode, veh_id, veh_type, leg_start_time, leg_end_time, leg_duration,
             distance, leg_path, leg_fuel, leg_fuel_type])
    return leg_array


def label_trip_mode(modes):
    if ('walk' in modes) and ('car' in modes) and ('bus' in modes):
        return 'drive_transit'
    elif ('car' in modes) and ('bus' in modes):
        return 'drive_transit'
    elif ('walk' in modes) and ('bus' in modes):
        return 'walk_transit'
    elif ('walk' in modes) and ('car' in modes):
        return 'car'
    elif ('car' == modes):
        return 'car'
    elif ('OnDemand_ride' in modes):
        return 'OnDemand_ride'
    elif ('walk' == modes):
        return 'walk'
    else:
        print(modes)


def merge_legs_trips(legs_df, trips_df):
    trips_df = trips_df[['PID', 'Trip_ID', 'Origin_Activity_ID', 'Destination_activity_ID', 'Trip_Purpose',
                         'Mode']]
    trips_df.columns = ['PID', 'Trip_ID', 'Origin_Activity_ID', 'Destination_activity_ID', 'Trip_Purpose',
                        'plannedTripMode']
    legs_grouped = legs_df.groupby("Trip_ID")
    unique_modes = legs_grouped['Mode'].unique()
    unique_modes_df = pd.DataFrame(unique_modes)
    unique_modes_df.columns = ['legModes']
    merged_trips = trips_df.merge(legs_grouped['Duration_sec', 'Distance_m', 'primaryFuel', 'FuelCost', 'Fare'].sum(),
                                  on='Trip_ID')
    merged_trips.set_index('Trip_ID', inplace=True)
    legs_transit = legs_df.loc[legs_df['Mode'] == 'bus',]
    legs_transit_grouped = legs_transit.groupby("Trip_ID")
    count_modes = legs_transit_grouped['Mode'].count()
    merged_trips.loc[count_modes.loc[count_modes.values > 1].index.values, 'Fare'] = merged_trips.loc[count_modes.loc[
                                                                                                          count_modes.values > 1].index.values, 'Fare'] / \
                                                                                     count_modes.loc[
                                                                                         count_modes.values > 1].values
    merged_trips = merged_trips.merge(unique_modes_df, on='Trip_ID')
    legs_grouped_start_min = pd.DataFrame(legs_grouped['Start_time'].min())
    legs_grouped_end_max = pd.DataFrame(legs_grouped['End_time'].max())
    merged_trips = merged_trips.merge(legs_grouped_start_min, on='Trip_ID')
    merged_trips = merged_trips.merge(legs_grouped_end_max, on='Trip_ID')
    merged_trips['realizedTripMode'] = merged_trips['legModes'].apply(lambda row: label_trip_mode(row))
    return merged_trips


# ########### 2. PARSING AND PROCESSING THE XML FILES INTO PANDAS DATA FRAMES ###############

def get_person_output_from_households_xml(households_xml, output_folder_path):
    """
    - Parses the outputHouseholds file to create the households_dataframe gathering each person's household attributes
    (person id, household id, number of vehicles in the household, overall income of the household)
    - Saves the household dataframe to csv

    Parameters
    ----------
    households_xml: ElementTree object
        Output of the open_xml() function for the `outputHouseholds.xml` file

    output_folder_path: pathlib.Path object
        Absolute path of the output folder of the simulation
        (format of the output folder name: `<scenario_name>-<sample_size>__<date and time>`)

    Returns
    -------
    households_df: pandas Dataframe
        Record of each person's household attributes
        (person id, household id, number of vehicles in the household, overall income of the household)
    """

    # get root of the `outputHouseholds.xml` file
    households_root = households_xml.getroot()
    hhd_array = []

    for hhd in households_root.getchildren():
        hhd_id = hhd.get('id').strip()
        hhd_children = hhd.getchildren()
        # check for vehicles; record household attributes
        if len(hhd_children) == 3:
            members = hhd_children[0]
            vehicles = hhd_children[1]
            income = hhd_children[2]
            vehs = vehicles.getchildren()
            hdd_num_veh = len(vehs)
        else:
            members = hhd_children[0]
            vehicles = []
            income = hhd_children[1]
            hdd_num_veh = 0
        hhd_income = income.text.strip()
        # get list of persons in household and make a record of each person
        list_members = members.getchildren()
        for person in list_members:
            pid = person.attrib['refId'].strip()
            hhd_array.append([pid, hhd_id, hdd_num_veh, hhd_income])

    # convert array to dataframe and save
    households_df = pd.DataFrame(hhd_array,
                                 columns=['PID', 'Household_ID', 'Household_num_vehicles', 'Household_income [$]'])
    households_df.to_csv(str(output_folder_path) + "/households_dataframe.csv")

    return households_df


def get_person_output_from_output_plans_xml(output_plans_xml):
    """ Parses the outputPlans file to create the person_dataframe gathering individual attributes of each person
    (person id, age, sex, home location)

    Parameters
    ----------
    output_plans_xml: ElementTree object
        Output of the open_xml() function for the `outputPlans.xml` file

    Returns
    -------
    person_df: pandas DataFrame
        Record of some of each person's individual attributes (person id, age, sex, home location)
    """

    # get root of the `outputPlans.xml` file
    output_plans_root = output_plans_xml.getroot()
    person_array = []

    for person in output_plans_root.findall('./person'):
        pid = person.get('id')
        attributes = person.findall('./attributes')[0]
        age = int(attributes.findall('./attribute[@name="age"]')[0].text)
        sex = attributes.findall('./attribute[@name="sex"]')[0].text
        plan = person.findall('./plan')[0]
        home = plan.findall('./activity')[0]
        home_x = home.get('x')
        home_y = home.get('y')
        person_array.append([pid, age, sex, home_x, home_y])
    # convert person array to dataframe
    person_df = pd.DataFrame(person_array, columns=['PID', 'Age', 'Sex', 'Home_X', 'Home_Y'])

    return person_df


def get_person_output_from_output_person_attributes_xml(persons_xml):
    """ Parses outputPersonAttributes.xml file to create population_attributes_dataframe gathering individual attributes
    of the population (person id, excluded modes (i.e. transportation modes that the peron is not allowed to use),
    income, rank, value of time).

    Parameters
    ----------
    persons_xml: ElementTree object
        Output of the open_xml() function for the `outputPersonAttributes.xml` file

    Returns
    -------
    person_df_2: pandas DataFrame
        Record of some of each person's individual attributes (person id, excluded modes (i.e. transportation modes
        that the peron is not allowed to use), income, rank, value of time)
    """

    # get root of the `outputPersonAttributes.xml` file
    persons_root = persons_xml.getroot()
    population_attributes = []

    population = persons_root.getchildren()
    for person in population:
        pid = person.get('id')
        attributes = person.findall("./attribute")
        population_attributes_dict = {}
        population_attributes_dict['PID'] = pid
        for attribute in attributes:
            population_attributes_dict[attribute.attrib['name']] = attribute.text
        population_attributes.append(population_attributes_dict)

    # convert attribute array to dataframe
    person_df_2 = pd.DataFrame(population_attributes)

    return person_df_2


def get_persons_attributes_output(output_plans_xml, persons_xml, households_xml, output_folder_path):
    """Outputs the augmented persons dataframe, including all individual and household attributes for each person

    Parameters
    ----------
    output_plans_xml: ElementTree object
        Output of the open_xml() function for the `outputPlans.xml` file

    persons_xml: ElementTree object
        Output of the open_xml() function for the `outputPersonAttributes.xml` file

    households_xml: ElementTree object
        Output of the open_xml() function for the `outputHouseholds.xml` file

    output_folder_path: pathlib.Path object
        Absolute path of the output folder of the simulation (format of the output folder name: `<scenario_name>-<sample_size>__<date and time>`)

    Returns
    -------
    persons_attributes_df: pandas DataFrame
        Record of all individual and household attributes for each person
    """
    # get the person attributes dataframes
    households_df = get_person_output_from_households_xml(households_xml, output_folder_path)
    person_df = get_person_output_from_output_plans_xml(output_plans_xml)
    person_df_2 = get_person_output_from_output_person_attributes_xml(persons_xml)

    # set the index of all dataframes to PID (person ID)
    person_df.set_index('PID', inplace=True)
    person_df_2.set_index('PID', inplace=True)
    households_df.set_index('PID', inplace=True)

    # join the three dataframes together
    persons_attributes_df = person_df.join(person_df_2)
    persons_attributes_df = persons_attributes_df.join(households_df)

    return persons_attributes_df


def get_activities_output(experienced_plans_xml):
    """ Parses the experiencedPlans.xml file to create the activities_dataframe, gathering each person's activities' attributes
    (person id, activity id, activity type, activity start time, activity end time)

    Parameters
    ----------
    experienced_plans_xml: ElementTree object
        Output of the open_xml() function for the `<num_iterations>.experiencedPlans.xml` file located in
        the `/ITERS/it.<num_iterations> folder

    Returns
    -------
    activities_df: pandas DataFrame
        Record of each person's activities' attributes

    trip_purposes: list of string
        purpose of each trip, ege, "Work", "Home".etc...

    """

    # get root of experiencedPlans xml file
    plans_root = experienced_plans_xml.getroot()
    acts_array = []

    # iterate through persons, recording activities and trips for each person
    for person in plans_root.findall('./person'):
        # we use the person ID from the raw output
        pid = person.get('id')
        plan = person.getchildren()[0]
        activities = plan.findall('./activity')

        # initialize activity ID counters (we create activity IDs using these)
        act_id = 0
        trip_purposes = []

        # iterate through activities and make record of each activity
        for activity in activities:
            act_id += 1
            # create activity ID
            activity_id = pid + "_a-" + str(act_id)
            act_type = activity.get('type')
            if activity.get('start_time') is None:
                act_start_time = None
            else:
                act_start_time = activity.get('start_time')
            if activity.get('end_time') is None:
                act_end_time = None
            else:
                act_end_time = activity.get('end_time')

            # record all activity types to determine trip trip_purposes
            trip_purposes.append([act_type])
            acts_array.append([pid, activity_id, act_type, act_start_time, act_end_time])

    # convert the activity_array to a dataframe
    activities_df = pd.DataFrame(acts_array, columns=['PID', 'Activity_ID', 'Activity_Type', 'Start_time', 'End_time'])

    return activities_df, trip_purposes


def get_trips_output(experienced_plans_xml_path):
    """ Parses the experiencedPlans.xml file to create the trips dataframe, gathering each person's trips' attributes
    (person id, trip id, id of the origin activity of the trip, id of the destination activity of the trip, trip purpose,
    mode used, start time of the trip, duration of the trip, distance of the trip, path of the trip)

    Parameters
    ----------
    experienced_plans_xml_path: str
        Output of the open_xml() function for the `<num_iterations>.experiencedPlans.xml` file located in
        the `/ITERS/it.<num_iterations> folder

    Returns
    -------
    trips_df: pandas DataFrame
        Record of each person's trips' attributes
    """
    # get root of experiencedPlans xml file
    experienced_plans_xml = open_xml(experienced_plans_xml_path)
    plans_root = experienced_plans_xml.getroot()
    trip_array = []

    # Getting the activities dataframe
    _, trip_purposes = get_activities_output(experienced_plans_xml)

    # iterate through persons, recording activities and trips for each person
    for person in plans_root.findall('./person'):
        # we use the person ID from the raw output
        pid = person.get('id')
        plan = person.getchildren()[0]
        legs = plan.findall('./leg')

        # initialize trip ID counters (we create trip IDs using these)
        trip_id = 0

        # iterate through trips (called legs in the `experiencedPlans.xml` file) and make record of each trip
        for trip in legs:
            trip_id += 1
            # create trip ID
            trip_id_full = pid + "_t-" + str(trip_id)
            # record activity IDs for origin and destination activities of the trip
            o_act_id = pid + "_a-" + str(trip_id)
            d_act_id = pid + "_a-" + str(trip_id + 1)

            # identify the activity type of the trip destination to record as the trip trip_purpose
            trip_purpose = trip_purposes[trip_id][0]

            mode = trip.get('mode')
            dep_time = trip.get('dep_time')
            duration = trip.get('trav_time')
            route = trip.find('./route')
            distance = route.get('distance')
            path = route.text
            trip_array.append(
                [pid, trip_id_full, o_act_id, d_act_id, trip_purpose, mode, dep_time, duration, distance, path])

    # convert the trip_array to a dataframe
    trips_df = pd.DataFrame(trip_array,
                            columns=['PID', 'Trip_ID', 'Origin_Activity_ID', 'Destination_activity_ID', 'Trip_Purpose',
                                     'Mode', 'Start_time', 'Duration_sec', 'Distance_m', 'Path_linkIds'])

    return trips_df


# def get_events_output(events):
#     """ Parses the outputEvents.xml to gather the event types into a pandas DataFrame
#
#     Parameters
#     ----------
#     events: xml.etree.ElementTree.ElementTree
#         Element tree instance of the xml file of interest
#
#     Returns
#     -------
#     :pandas Dataframe
#
#     """
#     event_data = {}
#     root = events.getroot()
#     for event in root.getchildren():
#         add_event_type_data_to_library(event, event_data)
#     return pd.DataFrame(event_data)
#
#
# def add_event_type_data_to_library(event, event_data):
#     """For each child element in the tree, creates a dictionary with the "type" attribute.
#
#     Parameters
#     ----------
#     event: xml.etree.ElementTree.Element
#         Child of the element tree instance
#
#     event_data: dictionary
#         Dictionary where the "type" attribute of the child element will be stored
#
#     """
#     attrib = event.attrib
#     event_type = attrib['type']
#     if event_type not in event_data:
#         dd = defaultdict(list)
#         event_data[event_type] = dd
#     else:
#         dd = event_data[event_type]
#     for k, v in attrib.items():
#         dd[k].append(v)


def get_path_traversal_output(events_df):
    """ Parses the experiencedPlans.xml file to create the trips dataframe, gathering each person's trips' attributes
    (person id, trip id, id of the origin activity of the trip, id of the destination activity of the trip, trip purpose,
    mode used, start time of the trip, duration of the trip, distance of the trip, path of the trip)

    Parameters
    ----------
    events_df: pandas DataFrame
        DataFrame extracted from the <num_iterations>.events.xml` file: output of the extract_dataframe() function

    trips_df: pandas DataFrame
        Record of each person's trips' attributes: output of the  get_trips_output() function

    Returns
    -------
    path_traversal_events_df: pandas DataFrame

    """

    # Selecting the columns of interest
    events_df = events_df[['time', 'type', 'person', 'vehicle', 'driver', 'vehicleType', 'length',
                           'numPassengers', 'departureTime', 'arrivalTime', 'mode', 'links',
                           'primaryFuelType', 'primaryFuel']]

    # get all path traversal events (all vehicle movements, and all person walk movements)
    path_traversal_events_df = events_df[(events_df['type'] == 'PathTraversal') & (events_df['length'] > 0)]
    path_traversal_events_df = path_traversal_events_df.reset_index(drop=True)
    path_traversal_events_df = path_traversal_events_df

    return path_traversal_events_df


def get_legs_output(events_df, trips_df):
    """ Parses the outputEvents.xml and trips_df file to create the legs dataframe, gathering each person's trips' legs' attributes
    (PID, Trip_ID, Leg_ID, Mode, Veh, Veh_type, Start_time, End_time,
                                    Duration, Distance, Path, fuel, fuelType)

    Parameters
    ----------
    events_df: pandas DataFrame
        DataFrame extracted from the outputEvents.xml` file: output of the extract_dataframe() function

    trips_df: pandas DataFrame
        Record of each person's trips' attributes: output of the get_trips_output() function

    Returns
    -------
    legs_df: pandas DataFrame
        Records the legs attributes for each person's trip

    """

    # convert trip times to timedelta; calculate end time of trips
    trips_df['Start_time'] = pd.to_timedelta(trips_df['Start_time'])
    trips_df['Duration_sec'] = pd.to_timedelta(trips_df['Duration_sec'])
    trips_df['End_time'] = trips_df['Start_time'].dt.seconds + trips_df['Duration_sec'].dt.seconds + (
            3600 * 24 * trips_df['Start_time'].dt.days)

    path_traversal_events_full = get_path_traversal_output(events_df)

    # get all relevant personEntersVehicle events (those occurring at time ==0 are all ridehail/bus drivers)
    enter_veh_events = events_df[(events_df['type'] == 'PersonEntersVehicle') & (events_df['time'] > 0)]

    # filter for bus path traversals only
    bus_path_traversal_events = path_traversal_events_full[path_traversal_events_full['mode'] == "bus"]

    # filter for car & body path traversals only
    non_bus_path_traversal_events = path_traversal_events_full[path_traversal_events_full['mode'] != "bus"]

    # get all PersonCost events (record the expenditures of persons during a trip)
    # person_costs = events_df.loc[events_df['type']=='PersonCost',]

    # get all ReserveRideHail events
    # reserve_ridehail_events = events_df[(events_df['type'] == 'ReserveRideHail') & (events_df['time'] > 0)]

    legs_array = []

    # record all legs corresponding to OnDemand_ride trips
    on_demand_ride_trips_df = trips_df.loc[((trips_df['Mode'] == 'OnDemand_ride') | (trips_df['Mode'] == 'ride_hail')),]
    print("Now processing on-demand ride trips")
    on_demand_ride_trips_dask_df = dd.from_pandas(on_demand_ride_trips_df, 32)
    on_demand_ride_legs_array = on_demand_ride_trips_dask_df.map_partitions(
        lambda df: df.apply((lambda row: parse_ridehail_trips(row, non_bus_path_traversal_events, enter_veh_events)),
                            axis=1)).compute(scheduler='processes')
    for bit in on_demand_ride_legs_array.tolist():
        legs_array.extend(tid for tid in bit)

    # record all legs corresponding to transit trips
    transit_trips_df = trips_df[(trips_df['Mode'] == 'drive_transit') | (trips_df['Mode'] == 'walk_transit')]
    print("Now processing transit trips")
    transit_trips_dask_df = dd.from_pandas(transit_trips_df, 32)
    transit_legs_array = transit_trips_dask_df.map_partitions(
        lambda df: df.apply((lambda row: parse_transit_trips(row, non_bus_path_traversal_events, bus_path_traversal_events, enter_veh_events)),
                            axis=1)).compute(scheduler='processes')
    for bit in transit_legs_array.tolist():
        legs_array.extend(tid for tid in bit)

    # record all legs corresponding to walk and car trips
    walk_car_trips_df = trips_df.loc[(trips_df['Mode'] == 'car') | (trips_df['Mode'] == 'walk'),]
    print("Now processing walk->car trips")
    walk_car_trips_dask_df = dd.from_pandas(walk_car_trips_df, 32)
    walk_car_legs_array = walk_car_trips_dask_df.map_partitions(lambda df: df.apply((lambda row: parse_walk_car_trips(row, non_bus_path_traversal_events, enter_veh_events)), axis=1)).compute(scheduler='processes')
    for bit in walk_car_legs_array.tolist():
        legs_array.extend(tid for tid in bit)

    # convert the leg array to a dataframe
    legs_df = pd.DataFrame(legs_array,
                           columns=['PID', 'Trip_ID', 'Leg_ID', 'Mode', 'Veh', 'Veh_type', 'Start_time', 'End_time',
                                    'Duration_sec', 'Distance_m', 'Path', 'primaryFuel', 'primaryFuelType'])

    return legs_df, path_traversal_events_full


# ############ 3. GENERATE THE CSV FILES ###########


def extract_person_dataframes(output_plans_path, persons_path, households_path, output_folder_path):
    """ Create a csv file from the processed person dataframe

    Parameters
    ----------
    output_plans_path: pathlib.Path object
        Absolute path of the the `outputPlans.xml` file

    persons_path: pathlib.Path object
        Absolute path of the the `outputPersonAttributes.xml` file

    households_path: pathlib.Path object
        Absolute path of the the `outputHouseholds.xml` file

    output_folder_path: pathlib.Path object
        Absolute path of the output folder of the simulation (format of the output folder name: `<scenario_name>-<sample_size>__<date and time>`)

    Returns
    -------
    persons_attributes_df: pandas DataFrame
        Record of all individual and household attributes for each person

    """

    # opens the xml files
    output_plans_xml = open_xml(output_plans_path)
    persons_xml = open_xml(persons_path)
    households_xml = open_xml(households_path)

    persons_attributes_df = get_persons_attributes_output(output_plans_xml, persons_xml, households_xml,
                                                          output_folder_path)
    persons_attributes_df.to_csv(str(output_folder_path) + "/persons_dataframe.csv")
    print("person_dataframe.csv generated")

    return persons_attributes_df


def extract_activities_dataframes(experienced_plans_path, output_folder):
    """ Create a csv file from the processed activities dataframe

    Parameters
    ----------
    experienced_plans_path: pathlib.Path object

    output_folder_path: pathlib.Path object
        Absolute path of the output folder of the simulation
        (format of the output folder name: `<scenario_name>-<sample_size>__<date and time>`)

    Returns
    -------
    activities_df
    """

    # opens the experiencedPlans and passes the xml file to get_activity_trip_output
    # returns the actitivities_dataframe and trips_dataframe

    experienced_plans_xml = open_xml(experienced_plans_path)
    activities_df, _ = get_activities_output(experienced_plans_xml)

    # convert dataframes into csv files
    activities_df.to_csv(str(output_folder) + "/activities_dataframe.csv")
    print("activities_dataframe.csv generated")

    return activities_df


def extract_legs_dataframes(events_path, trips_df, person_df, bus_fares_df, trip_to_route, fuel_costs,
                            output_folder_path):
    """ Create a csv file from the processes legs dataframe

    Parameters
    ----------
    events_path: pathlib.Path object
        Absolute path of the `ITERS/<num_iterations>.events.csv.gz` file

    trips_df: pandas DataFrame
        Record of each person's trips' attributes: output of the  get_trips_output() function

    person_df: pandas DataFrame
        Record of each person's trips' attributes: output of the  get_persons_attributes_output() function

    bus_fares_df: pandas DataFrame
        Dataframe with rows = ages and columns = routes: output of the parse_bus_fare_input() function

    trip_to_route: dictionary
        route_id / trip_id correspondence extracted from the `trips.csv` file in the
        `/reference-data/sioux_faux/sioux_faux_bus_lines/gtfs_data` folder of the Starter Kit

    fuel_costs: dictionary
        fuel type / fuel price correspondence extracted from the `beamFuelTypes.csv` file in the
        `/reference-data/sioux_faux/config/<SAMPLE_SIZE>` folder of the Starter Kit

    output_folder_path: pathlib.Path object
        Absolute path of the output folder of the simulation
        (format of the output folder name: `<scenario_name>-<sample_size>__<date and time>`)

    Returns
    -------
    legs_df: pandas DataFrame
        Records the legs attributes for each person's trips
    """
    # opens the outputevents and passes the xml file to get_legs_output
    # augments the legs dataframe with estimates of the fuelcosts and fares for each leg

    # extract a dataframe from the `outputEvents.xml` file
    # all_events_df = extract_dataframe(str(events_path))
    suffixes = Path(events_path).suffixes
    if suffixes[1] == ".xml":
        all_events_df = extract_dataframe(str(events_path))
    else:
        all_events_df = pd.read_csv(events_path)

    legs_df, path_traversal_df = get_legs_output(all_events_df, trips_df)

    path_traversal_df_new = calc_fuel_costs(path_traversal_df, fuel_costs)
    path_traversal_df_new.to_csv(str(output_folder_path) + '/path_traversals_dataframe.csv')
    print("path_traversals_dataframe.csv generated")
    legs_df_new = calc_fuel_costs(legs_df, fuel_costs)
    ride_hail_fares = {'base': 0.0, 'distance': 1.0, 'duration': 0.5}

    legs_df_new_new = calc_fares(legs_df_new, ride_hail_fares, bus_fares_df, person_df, trip_to_route)

    legs_df_new_new.to_csv(str(output_folder_path) + '/legs_dataframe.csv')
    print("legs_dataframe.csv generated")

    return legs_df_new_new


def output_parse(events_path, output_plans_path, persons_path, households_path, experienced_plans_path,
                 bus_fares_data_df, route_ids, trip_to_route, fuel_costs, output_folder_path, incentive_data, max_age,
                 max_income):
    persons_attributes_df = extract_person_dataframes(output_plans_path, persons_path, households_path,
                                                      output_folder_path)

    activities_df = extract_activities_dataframes(experienced_plans_path, output_folder_path)

    trips_df = get_trips_output(str(experienced_plans_path))
    bus_fares_df = parse_bus_fare_input(bus_fares_data_df, route_ids, max_age)
    incentive_df = parse_incentive_input(incentive_data, max_age, max_income)
    legs_df = extract_legs_dataframes(events_path, trips_df, persons_attributes_df, bus_fares_df, trip_to_route,
                                      fuel_costs, output_folder_path)
    legs_df = pd.read_csv(str(output_folder_path) + '/legs_dataframe.csv')
    final_trips_df = merge_legs_trips(legs_df, trips_df)
    final_trips_df_new = calc_incentives(final_trips_df, incentive_df, persons_attributes_df)

    final_trips_df_new.to_csv(str(output_folder_path) + '/trips_dataframe.csv')
    print("trips_dataframe.csv generated")
