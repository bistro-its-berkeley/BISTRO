# Filesystem management
import os
import sys
from shutil import copyfile
sys.path.append(os.path.abspath("../"))
sys.path.append(os.path.abspath("../../"))
sys.path.append(os.getcwd())

from utilities.optimization_utils import *
from ipyparallel import Client

# Utils
# import docker
import numpy as np

# Optimizers
from hyperopt import hp
from hyperopt.mongoexp import MongoTrials
from hyperopt import fmin
from hyperopt import tpe
from optimizer_per_mile_freeform_cl_sf import *

# projection conversion between lat/lon and projected coordinates
from pyproj import Proj, transform

# Logging and settings import
import csv
import yaml 

import argparse
import tqdm
import warnings
from functools import partial
warnings.filterwarnings("ignore")


# Load config
CONFIG = {}
with open("settings.yaml") as stream:
    CONFIG = yaml.safe_load(stream)

if not os.path.exists(CONFIG["RESULTS_PATH"]):
    os.makedirs(CONFIG["RESULTS_PATH"])

# BISTRO input files
# AGENCY = "sioux_faux_bus_lines"
FREQ_FILE = "FrequencyAdjustment.csv"
SUB_FILE = "ModeSubsidies.csv"
FLEET_FILE = "VehicleFleetMix.csv"
MASS_TRANSIT_FILE = "MassTransitFares.csv"

# chaging projection between meters and degree
inProj = Proj('epsg:3857') # projection
outProj = Proj('epsg:4326') # lat/lon

# x1,y1 = -11705274.6374,4826473.6922
# x2,y2 = transform(inProj,outProj,x1,y1)

centroids=[
    [-13629234.999116288, 4546248.731626279],
    [-13626639.261281533, 4550349.175273786],
    [-13633881.839333337, 4541056.829664177],
]

radius=[
    2411.4568215553545, 
    2411.4568215553545,
    3607.5806132652624
]


MAX_PRICE_PER_MILE = CONFIG["MAX_PRICE_PER_MILE"]
MIN_PRICE_PER_MILE = CONFIG["MIN_PRICE_PER_MILE"]
TOLL_DIM = CONFIG["TOLL_DIM"]

MAX_RADIUS = CONFIG["MAX_RADIUS"]
MIN_RADIUS = CONFIG["MIN_RADIUS"]
RADIUS_DIM = CONFIG["RADIUS_DIM"]

NUM_CORDONS = CONFIG["NUM_CORDONS"]

MIN_INCOME_THRESH_VERY_LOW = CONFIG["MIN_INCOME_THRESH_VERY_LOW"]
MAX_INCOME_THRESH_VERY_LOW = CONFIG["MAX_INCOME_THRESH_VERY_LOW"]
VERYLOW_INCOME_DIM = CONFIG["VERYLOW_INCOME_DIM"]

MIN_INCOME_THRESH_LOW = CONFIG["MIN_INCOME_THRESH_LOW"]
MAX_INCOME_THRESH_LOW = CONFIG["MAX_INCOME_THRESH_LOW"]
LOW_INCOME_DIM = CONFIG["LOW_INCOME_DIM"]

MIN_TNC_SUBSIDY = CONFIG["MIN_TNC_SUBSIDY"]
MAX_TNC_SUBSIDY = CONFIG["MAX_TNC_SUBSIDY"]
TNC_DIM = CONFIG["TNC_DIM"]

MIN_TRANSIT_SUBSIDY = CONFIG["MIN_TRANSIT_SUBSIDY"]
MAX_TRANSIT_SUBSIDY = CONFIG["MAX_TRANSIT_SUBSIDY"]
TRANIST_DIM = CONFIG["TRANIST_DIM"]


def uniform_points_from_circle(cordon_x, cordon_y, radius, N):
    """
    generating points in a cordon that are uniformly distributed
    """
    # np.random.seed(1)

    theta = np.random.uniform(0, 2*np.pi, N)
    radius = np.random.uniform(0, radius, N) ** 0.5

    x = cordon_x + radius * np.cos(theta)
    y = cordon_y + radius * np.sin(theta)
    
    return x, y

def round_nearest(x, a):
    return round(x / a) * a

def main(phase):

    data_root = abspath2(os.path.join(CONFIG["RESULTS_PATH"],"/reference-data"))
    input_root = abspath2(os.path.join(CONFIG["RESULTS_PATH"],"/bayesian-input"))
    output_root = abspath2(os.path.join(CONFIG["RESULTS_PATH"],"/bayesian-output"))

    os.makedirs(input_root, exist_ok=True)
    os.makedirs(output_root, exist_ok=True)

    # Keep track of results
    
    # File to save first results
    out_file = CONFIG["RESULTS_PATH"]+'/bayes_trials.csv'
    of_connection = open(out_file, 'w')
    writer = csv.writer(of_connection)

    # Write the headers to the file
    # logger.info("write row start\n")
    # logger.debug("write row start\n")
    writer.writerow(['loss', 'params', 'iteration', 'estimators', 'train_time'])

    if phase == '1':
        # 1 cordon only
        num_cordons = 1
        subsidies = False
    elif phase == '2':
        # 2 cordons only
        num_cordons = 2
        subsidies = False
    elif phase == '3':
        # 3 cordons only
        num_cordons = 3
        subsidies = False
    elif phase == '4':
        # 1 cordon + subsidies
        num_cordons = 1
        subsidies = True
    elif phase == '5':
        # 2 cordon + subsidies
        num_cordons = 2
        subsidies = True
    elif phase == '6':
        # 3 cordon + subsidies
        num_cordons = 3
        subsidies = True

    params = {}

    for i in np.random.choice([0, 1, 2], size=num_cordons, replace=False):
        params['centerx' + str(i)] = round_nearest(np.random.choice(x[i], replace=True), 50) # rounding to nearest 50m 
        params['centery' + str(i)] = round_nearest(np.random.choice(y[i], replace=True), 50) # rounding to nearest 50m 
        params['cradius' + str(i)] = np.random.choice(R, replace=True)
        params['ctoll' + str(i)] = np.random.choice(TOLL, replace=True)

    if subsidies:
        # income threhsolds
        vl_thresh = np.random.choice(VL_TRHESH)
        l_thresh = np.random.choice(L_TRHESH)
        vl_thresh = min(vl_thresh, l_thresh)
        params['low_income_thresh'] = l_thresh
        params['very_low_income_thresh'] = vl_thresh

        # subsidies: TNC, sample with replacement
        vl_tnc_subsidy = np.random.choice(TNC_SUB)
        l_tnc_subsidy = np.random.choice(TNC_SUB)
        vl_tnc_subsidy = min(vl_tnc_subsidy, l_tnc_subsidy)
        params['low_tnc_subsidy'] = l_tnc_subsidy
        params['very_low_tnc_subsidy'] = vl_tnc_subsidy

        # subsidies: TRANSIT, sample with replacement
        vl_transit_subsidy = np.random.choice(TRANS_SUB)
        l_transit_subsidy = np.random.choice(TRANS_SUB)
        vl_transit_subsidy = min(vl_transit_subsidy, l_transit_subsidy)
        params['low_transit_subsidy'] = l_transit_subsidy
        params['very_low_transit_subsidy'] = vl_transit_subsidy
    
    trial_result = objective(params)


    # logger.info("write row done\n")
    # logger.debug("write row done\n")
    # Run optimization
    # best = fmin(fn=objective, space=space, algo=tpe.suggest,
    #             max_evals=MAX_EVALS, trials=bayes_trials, rstate=np.random.RandomState(50))

    # logger.info("after best\n")
    # logger.debug("after best\n")
    #Post optimization cleanup
    # bayes_trials_results = sorted(bayes_trials.results, key=lambda x: x['loss'])
    # logger.info("experiment end")
    # logger.debug("experiment end")
    # logger.info(str(bayes_trials_results))
    # logger.info("saving experiment result to txt")
    # logger.debug(str(bayes_trials_results))
    # logger.debug("saving experiment result to txt")
    file = open("result.txt", "w")
    # for result in bayes_trials_results:
    for result in trial_result:
        # logger.info("writting result to csv")
        writer.writerow(result)
        file.write(str(result))
        #of_connection.write(",".join(result))
    # of_connection.close()
    file.close()


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", "-p")
    args = parser.parse_args()

    # phase param setup
    phase = args.phase

    # os_setup()
    # main()
    rc = Client()
    view = rc.load_balanced_view()

    # search space setup
    X, Y = [], []

    # generate the search space in cordon once and randomly sample from them for each experiment with replacement
    for i in range(3):
        x, y = uniform_points_from_circle(centroids[i][0], centroids[i][1], radius[i], 50) # change the density of fill of the circle
        X.append(x)
        Y.append(y)

    # cordon radius and toll
    R = np.random.uniform(MIN_RADIUS, MAX_RADIUS, RADIUS_DIM)
    TOLL = np.random.uniform(MIN_PRICE_PER_MILE, MAX_PRICE_PER_MILE, TOLL_DIM)
    
    # thresholds and subsidies
    L_TRHESH = np.random.uniform(MIN_INCOME_THRESH_LOW, MAX_INCOME_THRESH_LOW, LOW_INCOME_DIM)
    VL_TRHESH = np.random.uniform(MIN_INCOME_THRESH_VERY_LOW, MAX_INCOME_THRESH_VERY_LOW, VERYLOW_INCOME_DIM)

    TNC_SUB = np.random.uniform(MIN_TNC_SUBSIDY, MAX_TNC_SUBSIDY, TNC_DIM)
    TRANS_SUB = np.random.uniform(MIN_TRANSIT_SUBSIDY, MAX_TRANSIT_SUBSIDY, TRANIST_DIM)
    
    """
    phases:
    1: 1 cordon
    2: 2 cordons
    3: 3 cordons
    4: 1 cordon & subsidies
    5: 2 cordons & subsidies
    6: 3 cordons & subsidies
    """

    for _ in range(200):
        view.apply_async(partial(main), phase)
        # for running on SAVIO, need to modify this to without parallelization since one gradle instance is allowed at once