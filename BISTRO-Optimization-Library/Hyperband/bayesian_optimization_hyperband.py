#Filesystem management
import os
import sys
import datetime
import math
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
from optimizer_hyperband import *

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
AGENCY = "sioux_faux_bus_lines"
FREQ_FILE = "FrequencyAdjustment.csv"
SUB_FILE = "ModeSubsidies.csv"
FLEET_FILE = "VehicleFleetMix.csv"
MASS_TRANSIT_FILE = "MassTransitFares.csv"


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


    'centerx': hp.quniform('centerx', MIN_X, MAX_X, (MAX_X - MIN_X)/50),
    'centery': hp.quniform('centery', MIN_Y, MAX_Y, (MAX_Y - MIN_Y)/50),
    'cradius':  hp.quniform('cradius',  0 , MAX_Y - MIN_Y, (MAX_Y - MIN_Y)/50),
    'ctoll': hp.quniform('ctoll', 0, MAX_PRICE_PER_MILE, 0.1)

}




def os_setup():
    #In order to run mongodb and hyperopt, some file compying is necessary
    copyfile("optimizer_hyperband.py", CONFIG["HYPEROPT_PATH"]+"optimizer_hyperband.py")
    copyfile("convert_to_input_hyperband.py", CONFIG["HYPEROPT_PATH"]+"convert_to_input_hyperband.py")
    copyfile("../utilities/optimization_utils.py", CONFIG["HYPEROPT_PATH"]+"optimization_utils.py")
    copyfile("settings.yaml", CONFIG["HYPEROPT_PATH"]+"settings.yaml")
    copyfile("optimization_kpi.py", CONFIG["HYPEROPT_PATH"]+"optimization_kpi.py")
    print("Copied optimizers to hyperopt local direcotry")     
    return



def main():

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

    ITERATION = 0
    MAX_EVALS = CONFIG["NUMBER_OF_SAMPLES"]
    
    #add discard portion
    portion=0.8
    
    #add budget modification
    budget_update = 2
    budgetpath = CONFIG["RESULTS_PATH"] + "budget.csv"
    if not os.path.exists(budgetpath):
        data=pd.DataFrame(columns=['iter'])
        print(data)
        data.to_csv(budgetpath)
    
    
    # Keep track of results
    #bayes_trials = MongoTrials('mongo://localhost:27017/wh_db_circle/jobs', exp_key=CONFIG['UNIQUE_KEY'])
    bayes_trials = MongoTrials('mongo://localhost:27017/wh_db/jobs', exp_key=str(datetime.datetime.now()))
    len_trial=21
    while len_trial>=20:
        best = fmin(fn=objective, space=space, algo=tpe.suggest, max_evals=MAX_EVALS, trials=bayes_trials,rstate=np.random.RandomState(50))
        budget=pd.read_csv(budgetpath)
        if(len(budget)==0): n_sim_iters=1  
        else:
            n_sim_iters=budget.loc[len(budget)-1,'iter']*budget_update
            n_sim_iters=int(n_sim_iters)
        budget = budget.append({'iter': n_sim_iters}, ignore_index=True)
        budget.to_csv(budgetpath,index=False)
        
        sorted_trial=sorted(list(bayes_trials.trials), key=lambda x: x['result']['loss'])
        list_trial=list(sorted_trial)
        cutted_trial=list_trial[0:math.floor(len(list_trial)*portion)]
        MAX_EVALS=math.floor(len(list_trial)*portion)
        new_exp=str(datetime.datetime.now())
        test_trials=MongoTrials('mongo://localhost:27017/wh_db/jobs', exp_key=new_exp)
        for trial in cutted_trial:
            hyperopt_trial = hyperopt.Trials(new_exp).new_trial_docs(
                tids=[trial['tid']],
                specs=[trial['spec']], 
                results=[trial['result']],  
                miscs=[trial['misc']]
            )
            hyperopt_trial[0]['state'] = hyperopt.JOB_STATE_DONE
            test_trials.insert_trial_docs(hyperopt_trial) 
            test_trials.refresh()
        bayes_trials=test_trials
        len_trial=len(list(bayes_trials.trials))

    
    # File to save first results
    out_file = CONFIG["RESULTS_PATH"]+'/bayes_trials.csv'
    of_connection = open(out_file, 'w')
    writer = csv.writer(of_connection)

    # Write the headers to the file
    writer.writerow(['loss', 'params', 'iteration', 'estimators', 'train_time'])




    #Post optimization cleanup
    bayes_trials_results = sorted(bayes_trials.results, key=lambda x: x['loss'])
    for result in bayes_trials_results:
        of_connection.write(",".join(result))
    of_connection.close()


if __name__ == "__main__":
    os_setup()
    main()
