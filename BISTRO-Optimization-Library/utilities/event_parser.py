from collections import defaultdict

import pandas as pd
import progressbar

from data_parsing import extract_dataframe
from plans_parser import (
    label_trip_mode, calc_transit_fares, calc_ride_hail_fares, find_incentive)

class Trip():
    def __init__(self, run_id, person_id, trip_num):
        self.run_id = run_id
        self.person_id = person_id
        self.trip_num = trip_num
        self.orig_act = 0
        self.dest_act = 0 # dest_act by default should be orig act + 1
        self.trip_start = 0  # trip starts with activity end
        self.trip_end = 0  # trip ends with activity start
        self.distance = 0  # should be incremented along the way
        #self.trip_mode = ''  # shold be added along the way
        self.planned_mode = ''  # planned_mode in first mode chioce per trip
        self.realized_mode = ''
        self.fare = 0
        self.fuel_cost = 0
        self.toll = 0
        self.incentives = 0  # should be incremented along the way
        self.legs = []

    def to_list(self):
        return [self.run_id, self.person_id, self.trip_num, self.orig_act,
                 self.dest_act, self.trip_start, self.trip_end, self.distance,
                 self.planned_mode, self.realized_mode, self.fare, 
                 self.fuel_cost, self.toll, self.incentives]


class Leg():
    def __init__(self, run_id, person_id, trip_num, leg_num):
        self.run_id = run_id
        self.person_id = person_id
        self.trip_num = trip_num
        self.leg_num = leg_num
        self.orig_link = -1
        self.dest_link = -1
        self.leg_start = 0
        self.leg_end = 0
        self.distance = 0
        self.leg_mode = ''
        self.vehicle = ''
        self.path = []
        self.links = []
        self.fuel_cost = 0
        self.fare = 0
        self.toll = 0

    def to_list(self):
        return [self.run_id, self.person_id, self.trip_num, self.leg_num,
                self.orig_link, self.dest_link, self.leg_start, self.leg_end,
                self.distance, self.leg_mode, self.vehicle, self.fuel_cost,
                self.fare, self.toll]

    def leg_links_list(self, scenario):
        return [[self.run_id, self.person_id, self.trip_num, self.leg_num, link,
                 scenario] for link in self.links]

    def leg_pathtraversals_list(self, scenario):
        return [[self.run_id, self.person_id, self.trip_num, self.leg_num,
                 self.vehicle, path] for path in self.path]


class Person():
    def __init__(self, person_id):
        self.person_id = person_id
        self.trips = []
        self.event_indices = []


def search_vehicle_path(events_df, vehicle_path, vehicle, start, end):
    path_indices = []
    path_nums = []
    links = []
    link_set = set()
    fuel_cost = 0
    toll = 0
    for path_num, path_index in enumerate(vehicle_path[vehicle]):
        path = events_df.loc[path_index, :]
        time1 = float(path['departureTime'])
        time2 = float(path['arrivalTime'])
        if (time1 <= start and time2 >= end) or (start <= time1 < end) or\
                (start < time2 <= end):
            path_indices.append(path_index)
            path_nums.append(path_num+1)
            path_links = path['links'].split(',')
            # some times the output of BEAM has multiple PathTraversal events with
            # overlapping links in them, needs to deduplicate first
            fuel_cost += float(path['fuel_cost'])
            toll += float(path['tollPaid'])
            for link in path_links:
                if link == '':
                    continue
                link = int(link)
                if link not in link_set:
                    links.append(link)
                    link_set.add(link)

    return path_indices, path_nums, links, fuel_cost, toll


def parse_person_events(run_id, events_df, person, vehicle_path):
    """the person events should contain all events with @person=pid,
    plus the walking PathTraversal.  
    because most PathTraversal locates between enter vehicle
    and leave vehicle event and can be found easily with search_vehicle_path,
    but that's not always true for the walking PathTraversal.
    """

    walk_path_num = 0
    act_num = 1
    # we set this to 1 instead of 0 because the event from BEAM is organized so
    # that the actstart for the first activity won't show up here.
    trip_num = 0

    planned_mode = None
    start_time = None
    end_time = None

    for index in person.event_indices:
        e = events_df.loc[index, :]
        event_type = e['type']

        if event_type == 'ModeChoice':
            planned_mode = e['mode']
            start_time = None
            end_time = None

        if event_type == 'actend':
            # after actend, new trip begin
            trip_num += 1
            trip = Trip(run_id, person.person_id, trip_num)
            trip.planned_mode = planned_mode
            trip.trip_start = int(float(e['time']))
            trip.orig_act = act_num
            person.trips.append(trip)

        if event_type == 'PathTraversal' and e['mode'] == 'walk' and\
                float(e['length']) > 0:
            # we don't care about the stationary 'walk',
            # which is not walking at all.
            walk_path_num += 1
            trip = person.trips[-1]
            leg = Leg(run_id, person.person_id, trip.trip_num, len(trip.legs)+1)
            leg.path.append(walk_path_num)
            if e['links'] != '':
                links = [int(link) for link in e['links'].split(',') if link]
                leg.orig_link = links[0]
                leg.dest_link = links[-1]
                leg.links = links
            leg.leg_start = int(e['departureTime'])
            leg.leg_end = int(e['arrivalTime'])
            leg.distance = float(e['length'])
            leg.leg_mode = e['mode']
            leg.vehicle = e['vehicle']
            trip.legs.append(leg)

        if event_type == 'PersonEntersVehicle' and 'body' not in e['vehicle']:
            # this is the start of drive / transit / ride_hail leg
            trip = person.trips[-1]
            leg = Leg(run_id, person.person_id, trip.trip_num, len(trip.legs)+1)
            leg.leg_start = int(float(e['time']))
            leg.vehicle = e['vehicle']
            trip.legs.append(leg)

        if event_type == 'PersonLeavesVehicle' and 'body' not in e['vehicle']:
            # this is the end of drive / transit / ride_hail leg
            leg = person.trips[-1].legs[-1] 
            leg.leg_end = int(float(e['time']))
            path_indices, path_nums, links, fuel_cost, toll = search_vehicle_path(
                events_df, vehicle_path, e['vehicle'], leg.leg_start, leg.leg_end)
            leg.path = path_nums
            leg.fuel_cost = fuel_cost
            leg.toll = toll
            leg.links = links
            if len(links) > 0:
                leg.orig_link = links[0]
                leg.dest_link = links[-1]
            # distance is simply the sum of all path length
            leg.distance = sum([float(events_df.loc[index, 'length']) for index in path_indices])

            # for ride_hail pathTraversal has mode=car, needs to check VehicleID
            leg_mode = events_df.loc[path_indices[0], 'mode']
            if leg_mode == 'car' and 'rideHailVehicle' in events_df.loc[
                    path_indices[0], 'vehicle']:
                leg_mode = 'ride_hail'
            leg.leg_mode = leg_mode

        if event_type == 'actstart':
            # actstart marks the end of a trip, should handle the trip properly
            act_num += 1
            last_trip = person.trips[-1]
            last_trip.dest_act = act_num
            last_trip.trip_end = int(float(e['time']))
            last_trip.distance = sum([leg.distance for leg in last_trip.legs])
            last_trip.realized_mode = label_trip_mode([leg.leg_mode for leg in last_trip.legs])


def get_trips_legs_pathtraversals_vehicles_list(
        events_path, run_id, scenario, fuel_cost, incentive_df, bus_fares_df,
        person_df, trip_to_route):
    """"""
    events_df = extract_dataframe(events_path)

    # calculate fuel_cost for pathtraversals events
    events_df['fuel_cost'] = 0
    for f in fuel_cost.keys():
        index = ((events_df['type']=='PathTraversal') &
                 (events_df["primaryFuelType"] == f.capitalize()))
        events_df.loc[index, 'fuel_cost'] = (
            pd.to_numeric(
                events_df.loc[index, 'primaryFuel']) * float(fuel_cost[f])
        ) / 1000000

    vehicle_path = defaultdict(list)
    # keep all PathTraversal events in a dict for future use
    for index, e in events_df.iterrows():
        if e['type'] == 'PathTraversal':
            vehicle_path[e['vehicle']].append(index)

    # group all events by person (ignore the bus/ridehail agent)
    persons = {}
    for index, e in events_df.iterrows():
        if e['mode'] == 'walk':
            pid = e['driver']
        else:
            pid = e['person']
        
        if not pid or 'Agent' in pid:
            continue

        if pid not in persons:
            person = Person(pid)
            persons[pid] = person
        else:
            person = persons[pid]

        # for a person, event indices contains root indices of events that
        # relate to this person, include the walk PathTraversal, but not include
        # any other PathTraversal
        person.event_indices.append(index)

    bar = progressbar.ProgressBar(
        maxval=20,
        widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])

    bar.start()
    i = 0
    frac = len(persons.keys()) // 20
    for pid in persons:
        parse_person_events(run_id, events_df, persons[pid], vehicle_path)
        i += 1
        if i % frac == 0:
            bar.update(i // frac)
    bar.finish()

    vehicles_list = []
    pathtraversals_list = []
    pathtraversal_links_list = []
    for v_id, indices in vehicle_path.items():
        e = events_df.loc[indices[0], :]
        vehicles_list.append([v_id, e['vehicleType'], scenario])
        for i, index in enumerate(indices):
            path = events_df.loc[index, :]
            if path['links'] is not None and path['links'] != '':
                for link in path['links'].split(','):
                    pathtraversal_links_list.append(
                        [run_id, v_id, i+1, int(link), scenario]
                    )
            # BEAM was not very consistent on its output names
            # different version has different format.
            fuel_level = path['primaryFuelLevel'] if 'primaryFuelLevel' in path else path['endLegPrimaryFuelLevel']
            pathtraversals_list.append(
                [run_id, v_id, i+1, path['driver'], path['mode'],
                 float(path['length']), int(path['departureTime']),
                 int(path['arrivalTime']), int(path['numPassengers']),
                 float(path['primaryFuel']),
                 float(fuel_level),
                 path['primaryFuelType'],
                 path['fuel_cost'],
                 float(path['startX']),
                 float(path['startY']),
                 float(path['endX']),
                 float(path['endY'])
                ]
            )


    trips_list = []
    legs_list = []
    leg_links_list = []
    leg_pathtraversals_list = []
    ride_hail_fares = {'base': 0.0, 'distance': 1.0, 'duration': 0.5}

    for person in persons.values():
        for trip in person.trips:
            for leg in trip.legs:
                if leg.leg_mode in ['bus','tram','subway','cable_car']:
                    leg.fare = calc_transit_fares(
                        {'PID': person.person_id,'Veh':leg.vehicle},
                        bus_fares_df, person_df, trip_to_route)
                elif leg.leg_mode == 'ride_hail':
                    leg.fare = calc_ride_hail_fares(
                        {'Duration_sec':leg.leg_end-leg.leg_start,
                         'Distance_m':leg.distance},
                        ride_hail_fares)
                legs_list.append(leg.to_list())
                leg_links_list += leg.leg_links_list(scenario)
                leg_pathtraversals_list += leg.leg_pathtraversals_list(scenario)

            if trip.realized_mode in {
                    "ride_hail", "drive_transit", "walk_transit"}:
                trip.incentives = find_incentive(
                    {'PID':person.person_id}, incentive_df[trip.realized_mode], 
                    person_df
                )
            for leg in trip.legs:
                trip.fare += leg.fare
                trip.toll += leg.toll
                if leg.leg_mode == 'car':
                    trip.fuel_cost += leg.fuel_cost
            trips_list.append(trip.to_list())            

    return (trips_list, legs_list, leg_links_list, leg_pathtraversals_list,
            pathtraversals_list, pathtraversal_links_list, vehicles_list)