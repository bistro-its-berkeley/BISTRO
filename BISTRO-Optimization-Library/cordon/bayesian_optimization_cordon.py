#Filesystem management
import os
import sys
from shutil import copyfile
sys.path.append(os.path.abspath("../"))

from utilities.optimization_utils import *

#Utils
import docker
import numpy as np

#Optimizers
from hyperopt import hp
from hyperopt.mongoexp import MongoTrials
from hyperopt import fmin
from hyperopt import tpe
from optimizer_cordon import *

#Logging and settings import
import csv
import yaml 
import stat


#Load config
CONFIG = {}
with open("settings.yaml") as stream:
    CONFIG = yaml.safe_load(stream)

if not os.path.exists(CONFIG["RESULTS_PATH"]):
    os.makedirs(CONFIG["RESULTS_PATH"])

#BISTRO input files
AGENCY = "sioux_faux_bus_lines"
FREQ_FILE = "FrequencyAdjustment.csv"
SUB_FILE = "ModeSubsidies.csv"
FLEET_FILE = "VehicleFleetMix.csv"
MASS_TRANSIT_FILE = "MassTransitFares.csv"


MIN_X = 676949
MAX_X = 689624

MIN_Y = 4818750
MAX_Y = 4832294
MAX_PRICE_PER_MILE = CONFIG["MAX_TOLL"]

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


    'centerx': hp.quniform('centerx', MIN_X, MAX_X, (MAX_X - MIN_X)/50),
    'centery': hp.quniform('centery', MIN_Y, MAX_Y, (MAX_Y - MIN_Y)/50),
    'cradius':  hp.quniform('cradius',  0 , MAX_Y - MIN_Y, (MAX_Y - MIN_Y)/50),
    'ctoll': hp.quniform('ctoll', 0, MAX_PRICE_PER_MILE, 0.1)

}




def os_setup():
    #In order to run mongodb and hyperopt, some file compying is necessary
    copyfile("optimizer_cordon.py", CONFIG["HYPEROPT_PATH"]+"optimizer_cordon.py")
    copyfile("hypervolume_optimizer.py", CONFIG["HYPEROPT_PATH"]+"hypervolume_optimizer.py")
    copyfile("convert_to_input_cordon.py", CONFIG["HYPEROPT_PATH"]+"convert_to_input_cordon.py")
    copyfile("../utilities/optimization_utils.py", CONFIG["HYPEROPT_PATH"]+"optimization_utils.py")
    copyfile("settings.yaml", CONFIG["HYPEROPT_PATH"]+"settings.yaml")
    copyfile("optimization_kpi.py", CONFIG["HYPEROPT_PATH"]+"optimization_kpi.py")

    # 11_03 update - also copy to hyperopt_mongo_worker directory
    # not fully sure this is necessary
    print("path:")
    print(CONFIG["HYPEROPT_MONGO_WORKER_PATH"]+"optimizer_cordon.py")
    print()
    copyfile("optimizer_cordon.py", CONFIG["HYPEROPT_MONGO_WORKER_PATH"]+"optimizer_cordon.py")
    copyfile("hypervolume_optimizer.py", CONFIG["HYPEROPT_MONGO_WORKER_PATH"]+"hypervolume_optimizer.py")
    copyfile("convert_to_input_cordon.py", CONFIG["HYPEROPT_MONGO_WORKER_PATH"]+"convert_to_input_cordon.py")
    copyfile("../utilities/optimization_utils.py", CONFIG["HYPEROPT_MONGO_WORKER_PATH"]+"optimization_utils.py")
    copyfile("settings.yaml", CONFIG["HYPEROPT_MONGO_WORKER_PATH"]+"settings.yaml")
    copyfile("optimization_kpi.py", CONFIG["HYPEROPT_MONGO_WORKER_PATH"]+"optimization_kpi.py")

    print("Copied optimizers to hyperopt local direcotry")     
    return



def main():

    logging.basicConfig(level=logging.INFO)

    data_root = abspath2(os.path.join(CONFIG["RESULTS_PATH"],"/reference-data"))
    input_root = abspath2(os.path.join(CONFIG["RESULTS_PATH"],"/bayesian-input"))
    output_root = abspath2(os.path.join(CONFIG["RESULTS_PATH"],"/bayesian-output"))

    # had to skip makedirs because of read-only permission errors from iOS Catalina upgrade (?)
    # ran with sudo and still had these issues
    os.makedirs(input_root, stat.S_IWUSR, exist_ok=True)
    os.makedirs(output_root, exist_ok=True)

    seed = 123
    # TODO also consider setting pyseed
    np.random.seed(seed)

    # Global variable
    global ITERATION

    ITERATION = 0
    MAX_EVALS = CONFIG["NUMBER_OF_SAMPLES"]

    
    # Keep track of results
    bayes_trials = MongoTrials('mongo://localhost:27017/wh_db_circle/jobs', exp_key=CONFIG['UNIQUE_KEY'])
    
    # File to save first results
    out_file = CONFIG["RESULTS_PATH"]+'/bayes_trials.csv'
    of_connection = open(out_file, 'w')
    writer = csv.writer(of_connection)

    # Write the headers to the file
    writer.writerow(['loss', 'params', 'iteration', 'estimators', 'train_time'])

    # Run optimization
    best = fmin(fn=objective, space=space, algo=tpe.suggest,
                max_evals=MAX_EVALS, trials=bayes_trials, rstate=np.random.RandomState(50))


    #Post optimization cleanup
    bayes_trials_results = sorted(bayes_trials.results, key=lambda x: x['loss'])
    for result in bayes_trials_results:
        of_connection.write(",".join(result))
    of_connection.close()


if __name__ == "__main__":
    os_setup()
    main()
