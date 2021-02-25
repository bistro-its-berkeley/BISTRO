#Filesystem management
import os
import sys
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from shutil import copyfile
sys.path.append(os.path.abspath("../"))
sys.path.append(os.path.abspath("../../"))
sys.path.append(os.getcwd())

from utilities.optimization_utils import *

#Utils
import docker
import numpy as np

#Optimizers
from hyperopt import hp
from hyperopt.mongoexp import MongoTrials
from hyperopt import fmin
from hyperopt import tpe
from optimizer_per_mile_freeform_cl_sf import *

#Logging and settings import
import csv
import yaml 



#Load config
CONFIG = {}
with open("settings.yaml") as stream:
    CONFIG = yaml.safe_load(stream)

if not os.path.exists(CONFIG["RESULTS_PATH"]):
    os.makedirs(CONFIG["RESULTS_PATH"])

#BISTRO input files
# AGENCY = "sioux_faux_bus_lines"
FREQ_FILE = "FrequencyAdjustment.csv"
SUB_FILE = "ModeSubsidies.csv"
FLEET_FILE = "VehicleFleetMix.csv"
MASS_TRANSIT_FILE = "MassTransitFares.csv"


centroids=[[686497.8718080967, 4822235.745489025],
 [679510.8833787036, 4819979.04337517],
 [685501.9673044116, 4824476.617015609],
 [680233.4897498745, 4823718.955980723],
 [683815.8005387684, 4821232.363487416]]


radius=[1226.104703840097,
 1904.5410382051648,
 1226.104703840097,
 1904.5410382051648,
 1431.8067026407666]

#radius=[r/2 for r in radius] #added in debuging to avoid intersection, will realized this step in preprocessing


MIN_X = 676949
MAX_X = 689624

MIN_Y = 4818750
MAX_Y = 4832294

MAX_PRICE_PER_MILE = CONFIG["MAX_PRICE_PER_MILE"]

logger = logging.getLogger(__name__)

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

space = {


    # 'centerx': hp.quniform('centerx', MIN_X, MAX_X, (MAX_X - MIN_X)/50),
    # 'centery': hp.quniform('centery', MIN_Y, MAX_Y, (MAX_Y - MIN_Y)/50),
    # 'cradius':  hp.quniform('cradius',  0 , MAX_Y - MIN_Y, (MAX_Y - MIN_Y)/50),
    # 'ctoll': hp.quniform('ctoll', 0, MAX_PRICE_PER_MILE, 0.1)

    'centerx0': hp.quniform('centerx0', centroids[0][0]-radius[0]/2, centroids[0][0]+radius[0]/2, radius[0]/50),
    'centery0': hp.quniform('centery0', centroids[0][1]-radius[0]/2, centroids[0][1]+radius[0]/2, radius[0]/50),
    'cradius0':  hp.quniform('cradius0',  0 , radius[0], radius[0]/50),
    'ctoll0': hp.quniform('ctoll0', 0, MAX_PRICE_PER_MILE, 0.1),

    'centerx1': hp.quniform('centerx1', centroids[1][0]-radius[1]/2, centroids[1][0]+radius[1]/2, radius[1]/50),
    'centery1': hp.quniform('centery1', centroids[1][1]-radius[1]/2, centroids[1][1]+radius[1]/2, radius[1]/50),
    'cradius1':  hp.quniform('cradius1',  0 , radius[1], radius[1]/50),
    'ctoll1': hp.quniform('ctoll1', 0, MAX_PRICE_PER_MILE, 0.1),

    'centerx2': hp.quniform('centerx2', centroids[2][0]-radius[2]/2, centroids[2][0]+radius[2]/2, radius[2]/50),
    'centery2': hp.quniform('centery2', centroids[2][1]-radius[2]/2, centroids[2][1]+radius[2]/2, radius[2]/50),
    'cradius2':  hp.quniform('cradius2',  0 , radius[2], radius[2]/50),
    'ctoll2': hp.quniform('ctoll2', 0, MAX_PRICE_PER_MILE, 0.1),

    'centerx3': hp.quniform('centerx3', centroids[3][0]-radius[3]/2, centroids[3][0]+radius[3]/2, radius[3]/50),
    'centery3': hp.quniform('centery3', centroids[3][1]-radius[3]/2, centroids[3][1]+radius[3]/2, radius[3]/50),
    'cradius3':  hp.quniform('cradius3',  0 , radius[3], radius[3]/50),
    'ctoll3': hp.quniform('ctoll3', 0, MAX_PRICE_PER_MILE, 0.1),

    'centerx4': hp.quniform('centerx4', centroids[4][0]-radius[4]/2, centroids[4][0]+radius[4]/2, radius[4]/50),
    'centery4': hp.quniform('centery4', centroids[4][1]-radius[4]/2, centroids[4][1]+radius[4]/2, radius[4]/50),
    'cradius4':  hp.quniform('cradius4',  0 , radius[4], radius[4]/50),
    'ctoll4': hp.quniform('ctoll4', 0, MAX_PRICE_PER_MILE, 0.1)

}




def os_setup():
    #In order to run mongodb and hyperopt, some file compying is necessary
    copyfile("optimizer_per_mile_freeform_cl_sf.py", CONFIG["HYPEROPT_PATH"]+"optimizer_per_mile_freeform_cl_sf.py")
    copyfile("convert_to_input_per_mile_freeform.py", CONFIG["HYPEROPT_PATH"]+"convert_to_input_per_mile_freeform.py")
    copyfile("../../utilities/optimization_utils.py", CONFIG["HYPEROPT_PATH"]+"optimization_utils.py")
    copyfile("settings.yaml", CONFIG["HYPEROPT_PATH"]+"settings.yaml")
    copyfile("optimization_kpi.py", CONFIG["HYPEROPT_PATH"]+"optimization_kpi.py")
    print("Copied optimizers to hyperopt local direcotry")     
    return



def main():
    logging.basicConfig(filename='debug.log', encoding='utf-8', level=logging.DEBUG)
    logging.debug('This message should go to the log file')
    logging.basicConfig(level=logging.INFO)

    data_root = abspath2(os.path.join(CONFIG["RESULTS_PATH"],"/reference-data"))
    input_root = abspath2(os.path.join(CONFIG["RESULTS_PATH"],"/bayesian-input"))
    output_root = abspath2(os.path.join(CONFIG["RESULTS_PATH"],"/bayesian-output"))

    os.makedirs(input_root, exist_ok=True)
    os.makedirs(output_root, exist_ok=True)

    seed = 123
    # TODO also consider setting pyseed
    np.random.seed(seed)

    # Global variable
    global ITERATION
    logger.info("experiment start\n")
    ITERATION = 0
    MAX_EVALS = CONFIG["NUMBER_OF_SAMPLES"]

    
    # Keep track of results
    bayes_trials = MongoTrials('mongo://localhost:27017/wh_db_circle/jobs', exp_key=CONFIG['UNIQUE_KEY'])
    
    # File to save first results
    out_file = CONFIG["RESULTS_PATH"]+'/bayes_trials.csv'
    of_connection = open(out_file, 'w')
    writer = csv.writer(of_connection)

    # Write the headers to the file
    logger.info("write row start\n")
    logger.debug("write row start\n")
    writer.writerow(['loss', 'params', 'iteration', 'estimators', 'train_time'])
    logger.info("write row done\n")
    logger.debug("write row done\n")
    # Run optimization
    best = fmin(fn=objective, space=space, algo=tpe.suggest,
                max_evals=MAX_EVALS, trials=bayes_trials, rstate=np.random.RandomState(50))

    logger.info("after best\n")
    logger.debug("after best\n")
    #Post optimization cleanup
    bayes_trials_results = sorted(bayes_trials.results, key=lambda x: x['loss'])
    logger.info("experiment end")
    logger.debug("experiment end")
    logger.info(str(bayes_trials_results))
    logger.info("saving experiment result to txt")
    logger.debug(str(bayes_trials_results))
    logger.debug("saving experiment result to txt")
    file = open("result.txt","w")
    for result in bayes_trials_results:
        logger.info("writting result to csv")
        writer.writerow(result)
        file.write(str(result))
        #of_connection.write(",".join(result))
    of_connection.close()
    file.close()


if __name__ == "__main__":
    os_setup()
    main()
