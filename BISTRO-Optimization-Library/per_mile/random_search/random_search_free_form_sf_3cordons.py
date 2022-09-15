# Filesystem management
import os
import sys
# import logging
# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)
from shutil import copyfile
sys.path.append(os.path.abspath("../"))
sys.path.append(os.path.abspath("../../"))
sys.path.append(os.getcwd())

from utilities.optimization_utils import *
from ipyparallel import Client

# Utils
import docker
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


inProj = Proj('epsg:3857') # projection
outProj = Proj('epsg:4326') # lat/lon

x1,y1 = -11705274.6374,4826473.6922
x2,y2 = transform(inProj,outProj,x1,y1)


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

# radius=[r/2 for r in radius] #added in debuging to avoid intersection, will realized this step in preprocessing


# MIN_X = 676949
# MAX_X = 689624

# MIN_Y = 4818750
# MAX_Y = 4832294

MAX_PRICE_PER_MILE = CONFIG["MAX_PRICE_PER_MILE"]
MIN_PRICE_PER_MILE = CONFIG["MIN_PRICE_PER_MILE"]

MAX_RADIUS = CONFIG["MAX_RADIUS"]
MIN_RADIUS = CONFIG["MIN_RADIUS"]

NUM_CORDONS = CONFIG["NUM_CORDONS"]

MIN_INCOME_THRESH_VERY_LOW = CONFIG["MIN_INCOME_THRESH_VERY_LOW"]
MAX_INCOME_THRESH_VERY_LOW = CONFIG["MAX_INCOME_THRESH_VERY_LOW"]

MIN_INCOME_THRESH_LOW = CONFIG["MIN_INCOME_THRESH_LOW"]
MAX_INCOME_THRESH_LOW = CONFIG["MAX_INCOME_THRESH_LOW"]
INCOME_THREH_INTERVAL = CONFIG["INCOME_THREH_INTERVAL"]

MIN_TNC_SUBSIDY = CONFIG["MIN_TNC_SUBSIDY"]
MAX_TNC_SUBSIDY = CONFIG["MAX_TNC_SUBSIDY"]
MIN_TRANSIT_SUBSIDY = CONFIG["MIN_TRANSIT_SUBSIDY"]
MAX_TRANSIT_SUBSIDY = CONFIG["MAX_TRANSIT_SUBSIDY"]
SUBSIDY_INTERVAL = CONFIG["SUBSIDY_INTERVAL"]


# logger = logging.getLogger(__name__)

#####################################################################
#
# EXPERIMENT SEARCH SPACE PARAMETERS:
#
# - centerx : x-coordinate of the center of the toll radius
#
# - centery : y-coordinate of the center of the toll radius
#
# - cradius : radius of the toll circle
#
# - ctoll : per mile toll paid when traveling within circle
#
#####################################################################

# space = {


#     # 'centerx': hp.quniform('centerx', MIN_X, MAX_X, (MAX_X - MIN_X)/50),
#     # 'centery': hp.quniform('centery', MIN_Y, MAX_Y, (MAX_Y - MIN_Y)/50),
#     # 'cradius':  hp.quniform('cradius',  0 , MAX_Y - MIN_Y, (MAX_Y - MIN_Y)/50),
#     # 'ctoll': hp.quniform('ctoll', 0, MAX_PRICE_PER_MILE, 0.1)

#     'centerx0': hp.quniform('centerx0', centroids[0][0]-radius[0]/2, centroids[0][0]+radius[0]/2, radius[0]/50),
#     'centery0': hp.quniform('centery0', centroids[0][1]-radius[0]/2, centroids[0][1]+radius[0]/2, radius[0]/50),
#     'cradius0':  hp.quniform('cradius0',  0 , radius[0], radius[0]/50),
#     'ctoll0': hp.quniform('ctoll0', 0, MAX_PRICE_PER_MILE, 0.1),

#     'centerx1': hp.quniform('centerx1', centroids[1][0]-radius[1]/2, centroids[1][0]+radius[1]/2, radius[1]/50),
#     'centery1': hp.quniform('centery1', centroids[1][1]-radius[1]/2, centroids[1][1]+radius[1]/2, radius[1]/50),
#     'cradius1':  hp.quniform('cradius1',  0 , radius[1], radius[1]/50),
#     'ctoll1': hp.quniform('ctoll1', 0, MAX_PRICE_PER_MILE, 0.1),

#     'centerx2': hp.quniform('centerx2', centroids[2][0]-radius[2]/2, centroids[2][0]+radius[2]/2, radius[2]/50),
#     'centery2': hp.quniform('centery2', centroids[2][1]-radius[2]/2, centroids[2][1]+radius[2]/2, radius[2]/50),
#     'cradius2':  hp.quniform('cradius2',  0 , radius[2], radius[2]/50),
#     'ctoll2': hp.quniform('ctoll2', 0, MAX_PRICE_PER_MILE, 0.1),

#     'centerx3': hp.quniform('centerx3', centroids[3][0]-radius[3]/2, centroids[3][0]+radius[3]/2, radius[3]/50),
#     'centery3': hp.quniform('centery3', centroids[3][1]-radius[3]/2, centroids[3][1]+radius[3]/2, radius[3]/50),
#     'cradius3':  hp.quniform('cradius3',  0 , radius[3], radius[3]/50),
#     'ctoll3': hp.quniform('ctoll3', 0, MAX_PRICE_PER_MILE, 0.1),

#     'centerx4': hp.quniform('centerx4', centroids[4][0]-radius[4]/2, centroids[4][0]+radius[4]/2, radius[4]/50),
#     'centery4': hp.quniform('centery4', centroids[4][1]-radius[4]/2, centroids[4][1]+radius[4]/2, radius[4]/50),
#     'cradius4':  hp.quniform('cradius4',  0 , radius[4], radius[4]/50),
#     'ctoll4': hp.quniform('ctoll4', 0, MAX_PRICE_PER_MILE, 0.1)

# }


# def os_setup():
#     #In order to run mongodb and hyperopt, some file compying is necessary
#     copyfile("optimizer_per_mile_freeform_cl_sf.py", CONFIG["HYPEROPT_PATH"]+"optimizer_per_mile_freeform_cl_sf.py")
#     copyfile("convert_to_input_per_mile_freeform.py", CONFIG["HYPEROPT_PATH"]+"convert_to_input_per_mile_freeform.py")
#     copyfile("../../utilities/optimization_utils.py", CONFIG["HYPEROPT_PATH"]+"optimization_utils.py")
#     copyfile("settings.yaml", CONFIG["HYPEROPT_PATH"]+"settings.yaml")
#     copyfile("optimization_kpi.py", CONFIG["HYPEROPT_PATH"]+"optimization_kpi.py")
#     print("Copied optimizers to hyperopt local direcotry")     
#     return

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

def main():
    # logging.basicConfig(filename='debug.log', encoding='utf-8', level=logging.DEBUG)
    # logging.debug('This message should go to the log file')
    # logging.basicConfig(level=logging.INFO)

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

    params = {}
    
    # generate the search space in cordon once and randomly sample from them for each experiment with replacement 
    x, y = uniform_points_from_circle(centroids[i][0], centroids[i][1], radius[i], 50) # change the density of fill of the circle
    
    for i in range(len(radius)):
        # 'centerx0': hp.quniform('centerx0', centroids[0][0]-radius[0]/2, centroids[0][0]+radius[0]/2, radius[0]/50),
        # 'centery0': hp.quniform('centery0', centroids[0][1]-radius[0]/2, centroids[0][1]+radius[0]/2, radius[0]/50),
        # 'cradius0':  hp.quniform('cradius0',  0 , radius[0], radius[0]/50),
        # 'ctoll0': hp.quniform('ctoll0', 0, MAX_PRICE_PER_MILE, 0.1)

        # params['centerx'+str(i)] = np.random.uniform(centroids[0][0]-radius[0]/2, centroids[0][0]+radius[0]/2)
        # params['centery'+str(i)] = np.random.uniform(centroids[0][1]-radius[0]/2, centroids[0][1]+radius[0]/2)
        # params['cradius'+str(i)] = np.random.uniform(0 , radius[0])

        params['centerx' + str(i)] = round_nearest(np.random.choice(x), 0.005)
        params['centery' + str(i)] = np.random.choice(y)
        params['cradius' + str(i)] = np.random.uniform(MIN_RADIUS, MAX_RADIUS)
        params['ctoll' + str(i)] = np.random.uniform(MIN_PRICE_PER_MILE, MAX_PRICE_PER_MILE)

    # income threhsolds
    vl_thresh = np.random.uniform(MIN_INCOME_THRESH_VERY_LOW, MAX_INCOME_THRESH_VERY_LOW, 
                (MAX_INCOME_THRESH_VERY_LOW-MIN_INCOME_THRESH_VERY_LOW)/INCOME_THREH_INTERVAL)
    vl_thresh = np.random.choice(vl_thresh)

    l_thresh = np.random.uniform(MIN_INCOME_THRESH_LOW, MAX_INCOME_THRESH_LOW, 
               (MAX_INCOME_THRESH_LOW-MIN_INCOME_THRESH_LOW)/INCOME_THREH_INTERVAL)
    l_thresh = np.random.choice(l_thresh)

    vl_thresh = min(vl_thresh, l_thresh)                      
    params['low_income_thresh'] = l_thresh
    params['very_low_income_thresh'] = vl_thresh

    # subsidies: TNC
    tnc_subsidy = np.random.uniform(MIN_TNC_SUBSIDY, MAX_TNC_SUBSIDY, 
                     (MAX_TNC_SUBSIDY-MIN_TNC_SUBSIDY)/SUBSIDY_INTERVAL)
    vl_tnc_subsidy = np.random.choice(tnc_subsidy)
    l_tnc_subsidy = np.random.choice(tnc_subsidy)
    vl_tnc_subsidy = min(vl_tnc_subsidy, l_tnc_subsidy)

    params['low_tnc_subsidy'] = l_tnc_subsidy
    params['very_low_tnc_subsidy'] = vl_tnc_subsidy

    # subsidies: TRANSIT
    transit_subsidy = np.random.uniform(MIN_TRANSIT_SUBSIDY, MAX_TRANSIT_SUBSIDY, 
                     (MAX_TRANSIT_SUBSIDY-MIN_TRANSIT_SUBSIDY)/SUBSIDY_INTERVAL)
    vl_transit_subsidy = np.random.choice(transit_subsidy)
    l_transit_subsidy = np.random.choice(transit_subsidy)
    vl_transit_subsidy = min(vl_transit_subsidy, l_transit_subsidy)

    params['low_transit_subsidy'] = l_transit_subsidy
    params['very_low_transit_subsidy'] = vl_transit_subsidy
    
    objective(params)


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
    for result in bayes_trials_results:
        # logger.info("writting result to csv")
        writer.writerow(result)
        file.write(str(result))
        #of_connection.write(",".join(result))
    # of_connection.close()
    file.close()


if __name__ == "__main__":
    # os_setup()
    main()
    rc = Client()
    view = rc.load_balanced_view()

    for _ in range(200):
        view.apply_async(main)

# from ipyparallel import Client
# c = Client()
# c.ids

# dview = c[:]
# dview.block = True  # cause execution on master to wait while tasks sent to workers finish
# dview.apply(lambda : "Hello, World")

# # suppose I want to do leave-one-out cross-validation of a random forest statistical model
# # we define a function that fits to all but one observation and predicts for that observation
# def looFit(index, Ylocal, Xlocal):
#     rf = rfr(n_estimators=100)
#     fitted = rf.fit(np.delete(Xlocal, index, axis = 0), np.delete(Ylocal, index))
#     pred = rf.predict(np.array([Xlocal[index, :]]))
#     return(pred[0])

# dview.execute('from sklearn.ensemble import RandomForestRegressor as rfr')
# dview.execute('import numpy as np')
# # assume predictors are in 2-d array X and outcomes in 1-d array Y
# # here we generate random arrays for X and Y
# # we need to broadcast those data objects to the workers
# import numpy as np
# X = np.random.random((200,5))
# Y = np.random.random(200)
# mydict = dict(X = X, Y = Y, looFit = looFit)
# dview.push(mydict)

# # need a wrapper function because map() only operates on one argument
# def wrapper(i):
#     return(looFit(i, Y, X))

# n = len(Y)
# import time
# time.time()
# # run a parallel map, executing the wrapper function on indices 0,...,n-1
# lview = c.load_balanced_view()
# lview.block = True   # cause execution on master to wait while tasks sent to workers finish
# pred = lview.map(wrapper, range(n))
# time.time()

# print(pred[0:10])