import os
import sys

import docker
import numpy as np
from hyperopt import hp
from hyperopt.mongoexp import MongoTrials

sys.path.append(os.path.abspath("../../"))
from optimizer import *

AGENCY = "sioux_faux_bus_lines"

FREQ_FILE = "FrequencyAdjustment.csv"
SUB_FILE = "ModeSubsidies.csv"
FLEET_FILE = "VehicleFleetMix.csv"
MASS_TRANSIT_FILE = "MassTransitFares.csv"

MIN_X = 676949
MAX_X = 689624

MIN_Y = 4818750
MAX_Y = 4832294

MAX_PRICE_PER_MILE = 3.0

logger = logging.getLogger(__name__)

# Define the search space
space = {

    #Tolls adjustements
    #'fareLimitX': hp.quniform('fareLimitX', MIN_X, MAX_X, (MAX_X - MIN_X)/50),
    #'fareLimitY': hp.quniform('fareLimitY', MIN_Y, MAX_Y, (MAX_Y - MIN_Y)/50),
    #'farePriceP': hp.quniform('farePriceP', 0, MAX_PRICE_PER_MILE/1600,MAX_PRICE_PER_MILE/1600/50)

    #Variable circle with varaible entry tolls at peak times
    'centerx': hp.quniform('centerx', MIN_X, MAX_X, (MAX_X - MIN_X)/50),
    'centery': hp.quniform('centery', MIN_Y, MAX_Y, (MAX_Y - MIN_Y)/50),
    'cradius':  hp.quniform('cradius',  0 , MAX_Y - MIN_Y, (MAX_Y - MIN_Y)/50),
    'centry_toll': hp.quniform('centry_toll', 0, 10, 0.1)



    # VehicleFleetMix
    #'vehicleType_r1340': hp.choice('vehicleType1', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    #'vehicleType_r1341': hp.choice('vehicleType2', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    #'vehicleType_r1342': hp.choice('vehicleType3', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    #'vehicleType_r1343': hp.choice('vehicleType4', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    #'vehicleType_r1344': hp.choice('vehicleType5', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    #'vehicleType_r1345': hp.choice('vehicleType6', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    #'vehicleType_r1346': hp.choice('vehicleType7', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    #'vehicleType_r1347': hp.choice('vehicleType8', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    #'vehicleType_r1348': hp.choice('vehicleType9', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    #'vehicleType_r1349': hp.choice('vehicleType10', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    #'vehicleType_r1350': hp.choice('vehicleType11', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    #'vehicleType_r1351': hp.choice('vehicleType12', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),

    # MassTransitFares
    # Simplied list
    #'age1:15': hp.quniform('age1:5', 0.05, 10, 0.5),
    #'age16:60': hp.quniform('age16:60', 0.05, 10, 0.5),
    #'age61:120': hp.quniform('age61:120', 0.05, 10, 0.5),

    # ModeIncentives
    # Simplied list

    #'walk_transit_age1:15_income0': hp.quniform('walk_transit_age1-15_income0', 0.5, 50, 0.5),
    #'walk_transit_age1:15_income1': hp.quniform('walk_transit_age1-15_income1', 0.5, 50, 0.5),
    #'walk_transit_age1:15_income2': hp.quniform('walk_transit_age1-15_income2', 0.5, 50, 0.5),
    #'walk_transit_age1:15_income3': hp.quniform('walk_transit_age1-15_income3', 0.5, 50, 0.5),
    #'walk_transit_age16:60_income0': hp.quniform('walk_transit_age16-60_income0', 0.5, 50, 0.5),
    #'walk_transit_age16:60_income1': hp.quniform('walk_transit_age16-60_income1', 0.5, 50, 0.5),
    #'walk_transit_age16:60_income2': hp.quniform('walk_transit_age16-60_income2', 0.5, 50, 0.5),
    #'walk_transit_age16:60_income3': hp.quniform('walk_transit_age16-60_income3', 0.5, 50, 0.5),
    #'walk_transit_age61:120_income0': hp.quniform('walk_transit_age61-120_income0', 0.5, 50, 0.5),
    #'walk_transit_age61:120_income1': hp.quniform('walk_transit_age61-120_income1', 0.5, 50, 0.5),
    #'walk_transit_age61:120_income2': hp.quniform('walk_transit_age61-120_income2', 0.5, 50, 0.5),
    #'walk_transit_age61:120_income3': hp.quniform('walk_transit_age61-120_income3', 0.5, 50, 0.5),

    #'drive_transit_age1:15_income0': hp.quniform('drive_transit_age1-15_income0', 0.5, 50, 0.5),
    #'drive_transit_age1:15_income1': hp.quniform('drive_transit_age1-15_income1', 0.5, 50, 0.5),
    #'drive_transit_age1:15_income2': hp.quniform('drive_transit_age1-15_income2', 0.5, 50, 0.5),
    #'drive_transit_age1:15_income3': hp.quniform('drive_transit_age1-15_income3', 0.5, 50, 0.5),
    #'drive_transit_age16:60_income0': hp.quniform('drive_transit_age16-60_income0', 0.5, 50, 0.5),
    #'drive_transit_age16:60_income1': hp.quniform('drive_transit_age16-60_income1', 0.5, 50, 0.5),
    #'drive_transit_age16:60_income2': hp.quniform('drive_transit_age16-60_income2', 0.5, 50, 0.5),
    #'drive_transit_age16:60_income3': hp.quniform('drive_transit_age16-60_income3', 0.5, 50, 0.5),
    #'drive_transit_age61:120_income0': hp.quniform('drive_transit_age61-120_income0', 0.5, 50, 0.5),
    #'drive_transit_age61:120_income1': hp.quniform('drive_transit_age61-120_income1', 0.5, 50, 0.5),
    #'drive_transit_age61:120_income2': hp.quniform('drive_transit_age61-120_income2', 0.5, 50, 0.5),
    #'drive_transit_age61:120_income3': hp.quniform('drive_transit_age61-120_income3', 0.5, 50, 0.5),

    #'OnDemand_ride_age1:15_income0': hp.quniform('OnDemand_ride_age1-15_income0', 0.5, 50, 0.5),
    #'OnDemand_ride_age1:15_income1': hp.quniform('OnDemand_ride_age1-15_income1', 0.5, 50, 0.5),
    #'OnDemand_ride_age1:15_income2': hp.quniform('OnDemand_ride_age1-15_income2', 0.5, 50, 0.5),
    #'OnDemand_ride_age1:15_income3': hp.quniform('OnDemand_ride_age1-15_income3', 0.5, 50, 0.5),
    #'OnDemand_ride_age16:60_income0': hp.quniform('OnDemand_ride_age16-60_income0', 0.5, 50, 0.5),
    #'OnDemand_ride_age16:60_income1': hp.quniform('OnDemand_ride_age16-60_income1', 0.5, 50, 0.5),
    #'OnDemand_ride_age16:60_income2': hp.quniform('OnDemand_ride_age16-60_income2', 0.5, 50, 0.5),
    #'OnDemand_ride_age16:60_income3': hp.quniform('OnDemand_ride_age16-60_income3', 0.5, 50, 0.5),
    #'OnDemand_ride_age61:120_income0': hp.quniform('OnDemand_ride_age61-120_income0', 0.5, 50, 0.5),
    #'OnDemand_ride_age61:120_income1': hp.quniform('OnDemand_ride_age61-120_income1', 0.5, 50, 0.5),
    #'OnDemand_ride_age61:120_income2': hp.quniform('OnDemand_ride_age61-120_income2', 0.5, 50, 0.5),
    #'OnDemand_ride_age61:120_income3': hp.quniform('OnDemand_ride_age61-120_income3', 0.5, 50, 0.5),

    # FrequencyAdjustment
    # Simplied list

    # Midnight
    #'r1340_18001_27955': hp.choice('r1340_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1341_18001_27955': hp.choice('r1341_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1342_18001_27955': hp.choice('r1342_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1343_18001_27955': hp.choice('r1343_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1344_18001_27955': hp.choice('r1344_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1345_18001_27955': hp.choice('r1345_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1346_18001_27955': hp.choice('r1346_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1347_18001_27955': hp.choice('r1347_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1348_18001_27955': hp.choice('r1348_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1349_18001_27955': hp.choice('r1349_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1350_18001_27955': hp.choice('r1350_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1351_18001_27955': hp.choice('r1351_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),

    # Morning rush
    #'r1340_27956_37624': hp.choice('r1340_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1341_27956_37624': hp.choice('r1341_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1342_27956_37624': hp.choice('r1342_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1343_27956_37624': hp.choice('r1343_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1344_27956_37624': hp.choice('r1344_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1345_27956_37624': hp.choice('r1345_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1346_27956_37624': hp.choice('r1346_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1347_27956_37624': hp.choice('r1347_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1348_27956_37624': hp.choice('r1348_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1349_27956_37624': hp.choice('r1349_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1350_27956_37624': hp.choice('r1350_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1351_27956_37624': hp.choice('r1351_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),

    # Afternoon
    #'r1340_37625_59311': hp.choice('r1340_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1341_37625_59311': hp.choice('r1341_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1342_37625_59311': hp.choice('r1342_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1343_37625_59311': hp.choice('r1343_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1344_37625_59311': hp.choice('r1344_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1345_37625_59311': hp.choice('r1345_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1346_37625_59311': hp.choice('r1346_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1347_37625_59311': hp.choice('r1347_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1348_37625_59311': hp.choice('r1348_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1349_37625_59311': hp.choice('r1349_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1350_37625_59311': hp.choice('r1350_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1351_37625_59311': hp.choice('r1351_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),

    # Afternoon rush
    #'r1340_59312_72653': hp.choice('r1340_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1341_59312_72653': hp.choice('r1341_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1342_59312_72653': hp.choice('r1342_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1343_59312_72653': hp.choice('r1343_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1344_59312_72653': hp.choice('r1344_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1345_59312_72653': hp.choice('r1345_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1346_59312_72653': hp.choice('r1346_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1347_59312_72653': hp.choice('r1347_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1348_59312_72653': hp.choice('r1348_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1349_59312_72653': hp.choice('r1349_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1350_59312_72653': hp.choice('r1350_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1351_59312_72653': hp.choice('r1351_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),

    # Midnight
    #'r1340_72654_79199': hp.choice('r1340_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1341_72654_79199': hp.choice('r1341_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1342_72654_79199': hp.choice('r1342_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1343_72654_79199': hp.choice('r1343_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1344_72654_79199': hp.choice('r1344_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1345_72654_79199': hp.choice('r1345_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1346_72654_79199': hp.choice('r1346_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1347_72654_79199': hp.choice('r1347_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1348_72654_79199': hp.choice('r1348_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1349_72654_79199': hp.choice('r1349_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1350_72654_79199': hp.choice('r1350_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    #'r1351_72654_79199': hp.choice('r1351_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120])

}


def abspath2(path):
    path = os.path.abspath(os.path.expanduser(path))
    return path


def only_subdir(path):
    subdir, = os.listdir(path)  # Validates only returned element
    path = os.path.join(path, subdir)
    return path


def docker_exists(container_id, client):
    try:
        client.containers.get(container_id)
    except docker.errors.NotFound:
        return False
    return True


def save_inputs(input_dir, freq_df=None, mode_incentive_df=None, vehicle_fleet_mix_df=None, pt_fare_df=None):
    if freq_df is not None:
        freq_df.to_csv(os.path.join(input_dir, FREQ_FILE), header=True, index=False)
    if mode_incentive_df is not None:
        mode_incentive_df.to_csv(os.path.join(input_dir, SUB_FILE), header=True, index=False)
    if vehicle_fleet_mix_df is not None:
        vehicle_fleet_mix_df.to_csv(os.path.join(input_dir, FLEET_FILE), header=True, index=False)
    if pt_fare_df is None:
        pt_fare_df = pd.read_csv('../submission-inputs/{0}'.format(MASS_TRANSIT_FILE))
    pt_fare_df.to_csv(os.path.join(input_dir, MASS_TRANSIT_FILE), header=True, index=False)


import csv


def main():
    logging.basicConfig(level=logging.INFO)

    data_root = abspath2("../reference-data")
    input_root = abspath2("../bayesian-input")
    output_root = abspath2("../bayesian-output")

    os.makedirs(input_root, exist_ok=True)
    os.makedirs(output_root, exist_ok=True)

    seed = 123
    # TODO also consider setting pyseed
    np.random.seed(seed)

    # Global variable
    global ITERATION

    ITERATION = 0
    MAX_EVALS = 1000
    from hyperopt import fmin
    from hyperopt import tpe
    from hyperopt import rand
    
    # Keep track of results
    bayes_trials = MongoTrials('mongo://localhost:27017/wh_db_circle_rs/jobs', exp_key='RS_per_mile')
    # File to save first results
    out_file = '../bayesian-output/bayes_trials.csv'
    of_connection = open(out_file, 'w')
    writer = csv.writer(of_connection)

    # Write the headers to the file
    writer.writerow(['loss', 'params', 'iteration', 'estimators', 'train_time'])

    # Run optimization

    best = fmin(fn=objective, space=space, algo=rand.suggest,
                max_evals=MAX_EVALS, trials=bayes_trials, rstate=np.random.RandomState(50))

    bayes_trials_results = sorted(bayes_trials.results, key=lambda x: x['loss'])
    for result in bayes_trials_results:
        of_connection.write(",".join(result))
    of_connection.close()

    # with open('../bayesian-output/trials.pkl', 'wb', pkl.HIGHEST_PROTOCOL) as f:
    #     pkl.dump(bayes_trials, f)


if __name__ == "__main__":
    main()
