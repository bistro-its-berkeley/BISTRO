import os
from os.path import join
import re
import uuid
import zipfile
from datetime import datetime as dt

import pandas as pd
import utm
import sys
sys.path.append(os.path.abspath("../"))
sys.path.append(os.path.abspath("../../"))
sys.path.append(os.path.abspath("./"))
from utilities.bistro_connect_db import BistroDB, parse_credential
from utilities.bistro_dbschema import TABLES, TABLES_LIST
from utilities.data_parsing import open_xml
from utilities.plans_parser import (
    calc_fuel_costs,
    get_nodes_list,
    get_links_list,
    get_activities_list,
    get_person_output_from_households_xml,
    get_person_output_from_output_plans_xml,
    get_person_output_from_output_person_attributes_xml,
    get_bus_fares_df,
    get_fleet_mix_df,
    get_incentive_df,
    get_road_pricing_df,
    get_vehicletypes_df,
    parse_bus_fare_input,
    parse_incentive_input
)
from utilities.event_parser import get_trips_legs_pathtraversals_vehicles_list

# new import
from utilities.event_parser import get_trips_legs_pathtraversals_vehicles_list_express


max_age = 120
max_income = 150000


def vehicle_cost_path(fixed_data, city):
    return fixed_data + '/' + city + '/vehicleCosts.csv'


def vehicle_type_path(fixed_data, city, sample_size):
    path = fixed_data + '/' + city
    if city == 'sioux_faux':
        path += '/sample/' + sample_size

    elif city == 'sf_light':
        # the csv is stored in 'path' itself
        pass

    return path + '/vehicleTypes.csv'


def fuel_type_path(fixed_data, city, sample_size):
    path = fixed_data + '/' + city
    if city == 'sioux_faux':
        path += '/sample/' + sample_size

    elif city == 'sf_light':
        # the csv is stored in 'path' itself
        pass

    return path + '/beamFuelTypes.csv'


def get_r5_df(fixed_data, city, file_name):
    path = fixed_data + '/' + city
    if city == 'sioux_faux':
        with zipfile.ZipFile(path + '/r5/full_network/sf_gtfs.zip') as z:
            with z.open(file_name) as f:
                return pd.read_csv(f)

    elif city == 'sf_light':
        # manually added SF.zip as the GTFS feed for sf_light ~/r5/SF.zip
        with zipfile.ZipFile(path + '/r5/SF.zip') as z:
            with z.open(file_name) as f:
        #return pd.read_csv(path+'/r5/'+file_name)
                return pd.read_csv(f)


def convert_utm(easting, northing, city):
    # convert from utm to lat lon
    UTM_ZONE = {'sf_light': (10, 'N'),
                'sioux_faux': (14, 'N')}
    zone_number, zone = UTM_ZONE[city]
    return utm.to_latlon(easting, northing, zone_number, zone)


def load_persons_attributes_df(scenario, bistro_db):
    data = bistro_db.query(
        """
        SELECT person_id, age, income FROM person WHERE scenario='{}'
        """.format(scenario))
    person_df = pd.DataFrame(data, columns=['PID', 'Age', 'income'])

    return person_df.set_index('PID')


def load_route_ids(scenario, bistro_db):
    data = bistro_db.query(
        """
        SELECT route_id FROM transitroute WHERE scenario='{}'
        """.format(scenario))
    # data looks like [(route1,), (route2,), (route3,), ...]
    # sort in ascending order
    return sorted([row[0] for row in data])


def load_trip_to_route(scenario, bistro_db):
    data = bistro_db.query(
        """
        SELECT route_id, trip_id FROM transittrip WHERE scenario='{}'
        """.format(scenario))

    transit_trips = pd.DataFrame(data, columns=['route_id', 'trip_id'])

    return transit_trips.set_index('trip_id', drop=True).T.to_dict('records')[0]

def store_network_data_to_db(output_path, city, scenario, bistro_db):
    """"""
    network_xml = open_xml(output_path + '/outputNetwork.xml.gz')
    nodes_list = get_nodes_list(network_xml, scenario)
    for node in nodes_list:
        node[1], node[2] = convert_utm(node[1], node[2], city)
    links_list = get_links_list(network_xml, scenario)
    bistro_db.insert('node', nodes_list, skip_existing=True)
    bistro_db.insert('link', links_list, skip_existing=True)


def store_household_person_data_to_db(
        output_path, city, scenario, bistro_db):
    """"""
    households_df = get_person_output_from_households_xml(
        open_xml(output_path + '/outputHouseholds.xml.gz'))
    person_df = get_person_output_from_output_plans_xml(
        open_xml(output_path + '/outputPlans.xml.gz'))
    person_df_2 = get_person_output_from_output_person_attributes_xml(
        open_xml(output_path + '/outputPersonAttributes.xml.gz'))
    
    person_df.set_index('PID', inplace=True)
    person_df_2.set_index('PID', inplace=True)
    households_df.set_index('PID', inplace=True)

    persons_attributes_df = person_df.join(person_df_2)
    persons_attributes_df = persons_attributes_df.join(households_df)

    # sf_light data has no personal income, as a work around,
    # we just use household income for now
    if city == 'sf_light':
        persons_attributes_df['income'] = 0
    persons_attributes_df['scenario'] = scenario

    for col in ['Age', 'income', 'Household_num_vehicles', 'Home_X', 'Home_Y', 
                'Household_income [$]', 'rank', 'valueOfTime', 'excluded-modes']:
                # added 'excluded-modes'
        # added conditional statement
        # as of 06/28/2020, the sf_light BAU doesn't have the attribute 'valueOfTime'

        if col not in persons_attributes_df.columns:
        	# set to a default if column not found in the outputs
            persons_attributes_df[col] = 0
        else:
            persons_attributes_df[col] = pd.to_numeric(persons_attributes_df[col])

    household_list = persons_attributes_df.groupby('Household_ID').first().\
        reset_index()[[
            'Household_ID', 'Household_income [$]', 'Household_num_vehicles',
            'Home_X', 'Home_Y', 'scenario']
        ].values.tolist()
    # convert to lat lon
    for household in household_list:
        household[3], household[4] = convert_utm(
            household[3], household[4], city)
    #ipdb.set_trace()
    bistro_db.insert('household', household_list, skip_existing=True)

    # person_list will have values in order of (person_id, house_id, age, sex, income)
    person_list = persons_attributes_df.reset_index()[
        ['PID', 'Household_ID', 'Age', 'Sex', 'income',
         'excluded-modes', 'rank', 'valueOfTime', 'scenario']
    ].values.tolist()
    bistro_db.insert('person', person_list, skip_existing=True)

    return persons_attributes_df[['Age', 'income']]


def store_activity_data_to_db(output_path, scenario, iteration, bistro_db):
    """"""
    # 07/07: current BEAM output doesn't have the experiencedPlans.xml.gz generated in iteration folders
    # replacing with outout_plans.xml.gz
    #print(scenario)
    if 'sf_light' in scenario:
        activities_list = get_activities_list(
            open_xml(output_path +
                 '/output_plans.xml.gz'.format(iteration)),
            scenario)
    else:
        activities_list = get_activities_list(
            open_xml(output_path +
                 '/ITERS/it.{0}/{0}.experiencedPlans.xml.gz'.format(iteration)),
            scenario)

    bistro_db.insert('activity', activities_list, skip_existing=True)


def store_agency_to_db(fixed_data, city, scenario, bistro_db):
    agency = get_r5_df(fixed_data, city, 'agency.txt')
    agency['scenario'] = scenario
    bistro_db.insert(
        'agency',
        agency[['agency_id','scenario']].values.tolist(),
        skip_existing=True
    )

def store_transit_route_to_db(fixed_data, city, scenario, bistro_db):
    routes = get_r5_df(fixed_data, city, 'routes.txt')
    routes['scenario'] = scenario
    bistro_db.insert(
        'transitroute',
        routes[['route_id','agency_id','scenario']].values.tolist(),
        skip_existing=True
    )

    # for trips fare calculation
    return routes['route_id'].sort_values(ascending=True).tolist()

def store_default_transit_trips_to_db(fixed_data, city, scenario, bistro_db):
    transit_trips = get_r5_df(fixed_data, city, 'trips.txt')
    transit_trips['scenario'] = scenario
    bistro_db.insert(
        'transittrip',
        transit_trips[
            ['route_id','service_id','trip_id', 'scenario']
        ].values.tolist(),
        skip_existing=True
    )

    return transit_trips[['trip_id','route_id']].set_index(
        'trip_id', drop=True).T.to_dict('records')[0]


def store_default_vehicle_cost_to_db(fixed_data, city, scenario, bistro_db):
    vehicle_cost = pd.read_csv(vehicle_cost_path(fixed_data, city))
    vehicle_cost['scenario'] = scenario
    bistro_db.insert(
        'vehiclecost',
        vehicle_cost[
            ['vehicleTypeId', 'purchaseCost', 'opAndMaintCost', 'scenario']
        ].values.tolist(),
        skip_existing=True
    )


def store_vehicle_type_data_to_db(
        fixed_data, city, sample_size, bistro_db):
    vehicletypes_df = get_vehicletypes_df(
        vehicle_type_path(fixed_data, city, sample_size))
    vehicletypes_df['scenario'] = city + '-' + sample_size
    vehicletypes_list = vehicletypes_df[
        ['vehicleTypeId', 'primaryFuelType',
         'primaryFuelConsumptionInJoulePerMeter', 'primaryFuelCapacityInJoule',
         'seatingCapacity', 'standingRoomCapacity', 'scenario']].values.tolist()

    bistro_db.insert('vehicletype', vehicletypes_list, skip_existing=True)


def store_input_fleet_mix_data_to_db(output_path, simulation_id, bistro_db):
    if os.path.isfile(output_path + '/competition/submission-inputs/VehicleFleetMix.csv'):
        fleet_mix_data = pd.read_csv(
            output_path + '/competition/submission-inputs/VehicleFleetMix.csv')

        bus_frequency_data = pd.read_csv(
            output_path + '/competition/submission-inputs/FrequencyAdjustment.csv')

        fleet_mix_df = get_fleet_mix_df(fleet_mix_data, bus_frequency_data)
        if len(fleet_mix_df) > 0:
            fleet_mix_df['run_id'] = simulation_id
            bistro_db.insert(
                'fleetmix',
                fleet_mix_df[
                    ['run_id','agencyId','route_id','start_time',
                    'end_time','headway_secs','vehicleTypeId']
                ].values.tolist()
            )
    else:
        print(output_path, '/competition/VehicleFleetMix.csv file not found, skipped prasing and storing.')



def store_input_bus_fare_data_to_db(
        output_path, simulation_id, route_ids, bistro_db):
    if os.path.isfile(output_path + '/competition/submission-inputs/MassTransitFares.csv'):

        bus_fares_data = pd.read_csv(
            output_path + '/competition/submission-inputs/MassTransitFares.csv')
        routes = get_r5_df(fixed_data, city, 'routes.txt')

        bus_fares_df = get_bus_fares_df(bus_fares_data, routes)
        if len(bus_fares_df) > 0:
            bus_fares_df['run_id'] = simulation_id
            bistro_db.insert(
                'transitfare',
                bus_fares_df[
                    ['run_id','route_id','age_min','age_max','amount']
                ].values.tolist()
            )
        # construct detail bus fare data for event parsing
        return parse_bus_fare_input(bus_fares_data, route_ids, max_age)
    else:
        print(output_path, '/competition/MassTransitFares.csv file not found, skipped prasing and storing.')


def store_input_incentive_data_to_db(output_path, simulation_id, bistro_db):

    if os.path.isfile(output_path + '/competition/submission-inputs/ModeIncentives.csv'):
        incentive_data = pd.read_csv(
            output_path + '/competition/submission-inputs/ModeIncentives.csv')

        incentive_df = get_incentive_df(incentive_data)
        if len(incentive_df) > 0:
            incentive_df['run_id'] = simulation_id
            bistro_db.insert(
                'incentive',
                incentive_df[
                    ['run_id','mode','age_min','age_max',
                     'income_min','income_max','amount']
                ].values.tolist()
            )
    # this will be used to calculate incentive for trip
        return parse_incentive_input(incentive_data, max_age, max_income)
    else:
        print(output_path, '/competition/ModeIncentives.csv file not found, skipped prasing and storing.')



def store_input_road_pricing_data_to_db(output_path, simulation_id, bistro_db):

    if os.path.isfile(output_path + '/competition/submission-inputs/RoadPricing.csv'):
        pricing_data = pd.read_csv(
            output_path + '/competition/submission-inputs/RoadPricing.csv')

        pricing_df = get_road_pricing_df(pricing_data)
        if len(pricing_df) > 0:
            pricing_df['run_id'] = simulation_id
            bistro_db.insert(
                'roadpricing',
                pricing_df[
                    ['run_id', 'link_id', 'toll', 'start_time', 'end_time']
                ].values.tolist()
            )
    else:
        print(output_path, '/competition/RoadPricing.csv file not found, skipped prasing and storing.')


def store_toll_circle_to_db(output_path, simulation_id, city, scenario_n_size, bistro_db):
    with open(output_path+'/../../../../circle_params.txt', 'r') as f:
        tmp = f.readline().strip()
    arr = tmp.split(',')
    easting, northing = float(arr[0].split(':')[1]), float(arr[1].split(':')[1])
    radius = float(arr[2].split(':')[1])
    price = float(arr[3].split(':')[1])
    center_lat, center_lon = convert_utm(easting, northing, city)
    border_lat, border_lon = convert_utm(easting+radius, northing, city)

    bistro_db.insert(
            'tollcircle',
            [[simulation_id,scenario_n_size,'mileage',price,center_lat,center_lon,border_lat,border_lon]])


def store_hourly_mode_choice_to_db(
        output_path, simulation_id, iteration, bistro_db):
    df = pd.read_csv(
        output_path + '/ITERS/it.{0}/{0}.modeChoice.csv'.format(iteration),
        index_col=0).fillna(0)
    df.drop(columns=[col for col in df.columns if '_' not in col], inplace=True)
    df.rename(
        columns={col:int(col.split('_')[1]) for col in df.columns},
        inplace=True
    )
    df = df.stack().reset_index()
    df['run_id'] = simulation_id
    bistro_db.insert(
        'hourlymodechoice',
        df[['run_id','Modes','level_1',0]].values.tolist())


def store_average_travel_time_to_db(
        output_path, simulation_id, iteration, bistro_db):
    file_path = (output_path +
                 '/ITERS/it.{0}/{0}.averageTravelTimes.csv'.format(iteration))
    df = pd.read_csv(file_path, index_col=0).fillna(0.0)
    df = df.stack().reset_index()
    df['run_id'] = simulation_id
    bistro_db.insert(
        'traveltime',
        df[['run_id','TravelTimeMode\\Hour','level_1',0]].values.tolist())


def store_mode_choice_stats_to_db(output_path, simulation_id, bistro_db):
    df = pd.read_csv(output_path + '/modeChoice.csv', index_col=0).fillna(0)
    df = df.stack().reset_index()
    df['run_id'] = simulation_id
    bistro_db.insert(
        'modechoice',
        df[['run_id','iterations','level_1',0]].values.tolist())


def store_realized_mode_choice_stats_to_db(
        output_path, simulation_id, bistro_db):
    df = pd.read_csv(
        output_path + '/realizedModeChoice.csv', index_col=0).fillna(0)
    df = df.stack().reset_index()
    df['run_id'] = simulation_id
    bistro_db.insert(
        'realizedmodechoice',
        df[['run_id','iterations','level_1',0]].values.tolist())


def store_simulation_scores_to_db(output_path, simulation_id, bistro_db):    

    if os.path.isfile(output_path + '/competition/submissionScores.csv'):
        df = pd.read_csv(
            output_path + '/competition/submissionScores.csv').fillna(0.0)
        df['run_id'] = simulation_id
        bistro_db.insert(
            'score',
            df[['run_id', 'Component Name', 'Weight', 'Z-Mean', 'Z-StdDev',
                'Raw Score', 'Weighted Score']].values.tolist()
        )
    # added default handling for missing the submissionScores.csv file for BEAM outputs 
    else:
        print(output_path, '/competition/submissionScores.csv file not found, skipped prasing and storing.')


def store_raw_scores_to_db(output_path, simulation_id, iteration, bistro_db):

    if os.path.isfile(output_path + '/competition/rawScores.csv'):
    # and os.path.isfile('standardizationParameters'):

        score_df = pd.read_csv(output_path + '/competition/rawScores.csv',index_col='Iteration').fillna(0.0).loc[iteration,:]
        standard = pd.read_csv('standardizationParameters.csv',index_col='KPI').fillna(0.0)
        res = []
        for idx, score in score_df.items():
            # The simulation raw score used to have VMT score, but this score disappeared
            # after a BEAM update.
            if idx == 'Congestion: total vehicle miles traveled':
                continue

            if idx == 'TollRevenue':
                kpi = 'Toll Revenue'
            elif idx == 'VMT':
                kpi = 'Congestion: total vehicle miles traveled'
            else:
                kpi = idx
            mean = standard['MEAN'][idx]
            std = standard['STD'][idx]
            norm_score = score if std == 0 else (score-mean)/std
            res.append([simulation_id, kpi, 1.0, mean, std, score, norm_score])
        bistro_db.insert('score', res)
    else:
        print(output_path, '/competition/rawScores.csv file not found, skipped prasing and storing.')


def store_event_data_to_db(
        output_path, iteration, simulation_id, scenario, fuel_cost,
        detail_incentive_df, detail_bus_fares_df, persons_attributes_df,
        trip_to_route, bistro_db):
    if os.path.isfile(output_path +
                   '/ITERS/it.{0}/{0}.events.xml.gz'.format(iteration)):

        events_path = (output_path +
                   '/ITERS/it.{0}/{0}.events.xml.gz'.format(iteration))
        f = 'xml'
    else:
        # BEAM output as a csv rather than xml
        print('Found events.csv.gz instead')
        f = 'csv'
        events_path = (output_path +
                   '/ITERS/it.{0}/{0}.events.csv.gz'.format(iteration))
    (trips_list, legs_list, leg_links_list, leg_pathtraversals_list,
     pathtraversals_list, pathtraversal_links_list, vehicles_list) = \
        get_trips_legs_pathtraversals_vehicles_list(
            events_path, simulation_id, scenario, fuel_cost,
            detail_incentive_df, detail_bus_fares_df, persons_attributes_df,
            trip_to_route, f)

    bistro_db.insert('vehicle', vehicles_list, skip_existing=True)
    
    bistro_db.insert('trip', trips_list)
    bistro_db.insert('leg', legs_list)
    bistro_db.insert('pathtraversal', pathtraversals_list)

    try:
        pathtraversal_links_list.head()
    except:
        print(type(pathtraversal_links_list))
    bistro_db.insert('pathtraversal_link', pathtraversal_links_list, skip_existing=True)
    bistro_db.insert('leg_pathtraversal', leg_pathtraversals_list)
    bistro_db.insert('leg_link', leg_links_list, skip_existing=True)

    print('Finished storing event data to database')

#############################################################################
def return_event_data(
        output_path, iteration, simulation_id, scenario, fuel_cost,
        detail_incentive_df, detail_bus_fares_df, persons_attributes_df,
        trip_to_route, bistro_db):
    if os.path.isfile(output_path +
                   '/ITERS/it.{0}/{0}.events.xml.gz'.format(iteration)):

        events_path = (output_path +
                   '/ITERS/it.{0}/{0}.events.xml.gz'.format(iteration))
        f = 'xml'
    else:
        # BEAM output as a csv rather than xml
        print('Found events.csv.gz instead')
        f = 'csv'
        events_path = (output_path +
                   '/ITERS/it.{0}/{0}.events.csv.gz'.format(iteration))
    (trips_list, legs_list, leg_links_list, leg_pathtraversals_list,
     pathtraversals_list, pathtraversal_links_list, vehicles_list) = \
        get_trips_legs_pathtraversals_vehicles_list_express(
            events_path, simulation_id, scenario, fuel_cost,
            detail_incentive_df, detail_bus_fares_df, persons_attributes_df,
            trip_to_route, f)
    # changed to express function here
    return trips_list, legs_list, pathtraversals_list, vehicles_list
#############################################################################

def parse_and_store_data_to_db(
        output_path, fixed_data, city, sample_size, iteration, name='test',
        cordon=False, standardize_score=False, local=False, db_name='bistro'):

    datetime_pattern = r"__(\d+)-(\d+)-(\d+)_(\d+)-(\d+)-(\d+)"

    match = re.search(datetime_pattern, output_path)
    if match:
        year, month, date, hour, minute, second = match.groups()
        datetime = '-'.join(
            [year, month, date]) + ' ' + ':'.join([hour, minute, second])
    
    else:
        datetime = dt.now().strftime("%Y-%m-%d %H:%M:%S")

    scenario_n_size = city + '-' + sample_size

    bistro_db = parse_credential(join(dirname(__file__),'dashboard_profile.ini'))

    for table in TABLES_LIST:
        bistro_db.create_table(table, TABLES[table])

    if not bistro_db.fixed_data_in_db(scenario_n_size):
        store_network_data_to_db(output_path, city, scenario_n_size, bistro_db)

        persons_attributes_df = store_household_person_data_to_db(
            output_path, city, scenario_n_size, bistro_db)

        store_vehicle_type_data_to_db(
            fixed_data, city, sample_size, bistro_db)

        store_activity_data_to_db(
            output_path, scenario_n_size, iteration, bistro_db)

        store_agency_to_db(fixed_data, city, scenario_n_size, bistro_db)

        route_ids = store_transit_route_to_db(
            fixed_data, city, scenario_n_size, bistro_db)

        trip_to_route = store_default_transit_trips_to_db(
            fixed_data, city, scenario_n_size, bistro_db)
    
        store_default_vehicle_cost_to_db(
            fixed_data, city, scenario_n_size, bistro_db)

        # commit the change here after the fixed data has been parsed. 
        # In case something goes wrong in the following dynamic data parsing,
        # we don't have to re-parse these fixed data again.
        bistro_db.fixed_data_finish_parsing(scenario_n_size)
    else:
        print('Fixed data for {} already exist in DB.'.format(scenario_n_size))
        # if fixed data has been stored in the database, we load them from DB
        # directly
        persons_attributes_df = load_persons_attributes_df(
            scenario_n_size, bistro_db)
        route_ids = load_route_ids(scenario_n_size, bistro_db)
        trip_to_route = load_trip_to_route(scenario_n_size, bistro_db)

    fuel_cost = pd.read_csv(
            fuel_type_path(fixed_data, city, sample_size)
            )[['fuelTypeId','priceInDollarsPerMJoule']]

    fuel_cost.loc[len(fuel_cost)] = ['food', 0]
    fuel_cost = fuel_cost.set_index('fuelTypeId', drop=True).T.to_dict('records')[0]

    ########################
    #
    # Store Simulation Data
    #
    ########################
    simulation_id = str(uuid.uuid1())
    bistro_db.insert(
        'simulationrun', [[simulation_id, datetime, scenario_n_size, name]])

    store_input_fleet_mix_data_to_db(output_path, simulation_id, bistro_db)

    detail_bus_fares_df = store_input_bus_fare_data_to_db(
        output_path, simulation_id, route_ids, bistro_db)

    detail_incentive_df = store_input_incentive_data_to_db(
        output_path, simulation_id, bistro_db)

    store_input_road_pricing_data_to_db(output_path, simulation_id, bistro_db)

    if cordon:
        store_toll_circle_to_db(
            output_path, simulation_id, city, scenario_n_size, bistro_db)

    store_hourly_mode_choice_to_db(output_path, simulation_id, iteration, bistro_db)

    store_average_travel_time_to_db(
        output_path, simulation_id, iteration, bistro_db)

    store_mode_choice_stats_to_db(output_path, simulation_id, bistro_db)

    store_realized_mode_choice_stats_to_db(
        output_path, simulation_id, bistro_db)

    if standardize_score:
        store_raw_scores_to_db(output_path, simulation_id, iteration, bistro_db)
    else:
        store_simulation_scores_to_db(output_path, simulation_id, bistro_db)

    # this will store all trip, leg, pathtraversal, and vehicle data from the
    # simulation to the database
    if not local:
        store_event_data_to_db(
            output_path, iteration, simulation_id, scenario_n_size, fuel_cost,
            detail_incentive_df, detail_bus_fares_df, persons_attributes_df,
            trip_to_route, bistro_db)

        # commit after all data had been added to DB.
        bistro_db.connection.commit()
        return simulation_id
    if local:
        (trips_list, legs_list, pathtraversals_list, vehicles_list) = \
        return_event_data(
            output_path, iteration, simulation_id, scenario_n_size, fuel_cost,
            detail_incentive_df, detail_bus_fares_df, persons_attributes_df,
            trip_to_route, bistro_db)
        return (trips_list, legs_list, pathtraversals_list, vehicles_list)
    
    return simulation_id

def tpe_path(root, name):
    import glob
    return glob.glob(root+ '/'+ name+ '/'+ 'output/*/sioux_faux/*')[0]


if __name__ == '__main__':

    # city = 'sf_light'
    # sample_size = '25k'
    # iteration = 0

    city = 'sioux_faux'
    sample_size = '15k'
    iteration = 99

    output_root = '/Users/zangnanyu/bistro/BeamCompetitions/output'
    input_root = '/Users/zangnanyu/bistro/BeamCompetitions/submission-inputs'
    fixed_data = '/Users/zangnanyu/bistro/BeamCompetitions/fixed-data'

    print("start running simulation")
    # log = os.popen(
    #     """docker run -it --memory=8g --cpus=4 -v {}:/submission-inputs:ro
    #     -v {}:/output:rw beammodel/beam-competition:0.0.3-SNAPSHOT
    #     --scenario {} --sample-size {} --iters {}
    #     """.format(input_root, output_root, city, sample_size, iteration)
    # ).read()
    # print(log)

    # use regex to match the special format in BEAM output directory path
    # '__yyyy-mm-dd_hh-mm-ss'

    # datetime_pattern = r"__(\d+)-(\d+)-(\d+)_(\d+)-(\d+)-(\d+)"
    # match = re.search(datetime_pattern, log)

    # output_root += '/' if output_root[-1] != '/' else ''
    # output_path = (output_root + city + '/' +  city + '-' + sample_size + match.group())
    output_path = '/Users/zangnanyu/bistro/BeamCompetitions/fixed-data/sioux_faux/bau/warm-start/sioux_faux-15k__warm-start'

    parse_and_store_data_to_db(output_path, fixed_data, city, sample_size, iteration)
