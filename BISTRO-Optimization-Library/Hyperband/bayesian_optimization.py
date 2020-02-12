import os
import sys
import math
import logging
import docker
import numpy as np
import hyperopt
from hyperopt import hp
from hyperopt.mongoexp import MongoTrials
import datetime

sys.path.append(os.path.abspath("../../"))
from optimizer import *

AGENCY = "sioux_faux_bus_lines"
budget_update=2
FREQ_FILE = "FrequencyAdjustment.csv"
SUB_FILE = "ModeSubsidies.csv"
FLEET_FILE = "VehicleFleetMix.csv"
MASS_TRANSIT_FILE = "MassTransitFares.csv"

logger = logging.getLogger(__name__)

# Define the search space
space = {
    # VehicleFleetMix
    'vehicleType_r1340': hp.choice('vehicleType1', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    'vehicleType_r1341': hp.choice('vehicleType2', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    'vehicleType_r1342': hp.choice('vehicleType3', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    'vehicleType_r1343': hp.choice('vehicleType4', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    'vehicleType_r1344': hp.choice('vehicleType5', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    'vehicleType_r1345': hp.choice('vehicleType6', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    'vehicleType_r1346': hp.choice('vehicleType7', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    'vehicleType_r1347': hp.choice('vehicleType8', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    'vehicleType_r1348': hp.choice('vehicleType9', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    'vehicleType_r1349': hp.choice('vehicleType10', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    'vehicleType_r1350': hp.choice('vehicleType11', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    'vehicleType_r1351': hp.choice('vehicleType12', ['BUS-SMALL-HD', 'BUS-DEFAULT', 'BUS-STD-HD', 'BUS-STD-ART']),
    # MassTransitFares
    # Simplied list
    'age1:15': hp.quniform('age1:5', 0.5, 10, 0.5),
    'age16:60': hp.quniform('age16:60', 0.5, 10, 0.5),
    'age61:120': hp.quniform('age61:120', 0.5, 10, 0.5),

    # ModeIncentives
    # Simplied list

    'walk_transit_age1:15_income0': hp.quniform('walk_transit_age1-15_income0', 0.5, 50, 0.5),
    'walk_transit_age1:15_income1': hp.quniform('walk_transit_age1-15_income1', 0.5, 50, 0.5),
    'walk_transit_age1:15_income2': hp.quniform('walk_transit_age1-15_income2', 0.5, 50, 0.5),
    'walk_transit_age1:15_income3': hp.quniform('walk_transit_age1-15_income3', 0.5, 50, 0.5),
    'walk_transit_age16:60_income0': hp.quniform('walk_transit_age16-60_income0', 0.5, 50, 0.5),
    'walk_transit_age16:60_income1': hp.quniform('walk_transit_age16-60_income1', 0.5, 50, 0.5),
    'walk_transit_age16:60_income2': hp.quniform('walk_transit_age16-60_income2', 0.5, 50, 0.5),
    'walk_transit_age16:60_income3': hp.quniform('walk_transit_age16-60_income3', 0.5, 50, 0.5),
    'walk_transit_age61:120_income0': hp.quniform('walk_transit_age61-120_income0', 0.5, 50, 0.5),
    'walk_transit_age61:120_income1': hp.quniform('walk_transit_age61-120_income1', 0.5, 50, 0.5),
    'walk_transit_age61:120_income2': hp.quniform('walk_transit_age61-120_income2', 0.5, 50, 0.5),
    'walk_transit_age61:120_income3': hp.quniform('walk_transit_age61-120_income3', 0.5, 50, 0.5),

    'drive_transit_age1:15_income0': hp.quniform('drive_transit_age1-15_income0', 0.5, 50, 0.5),
    'drive_transit_age1:15_income1': hp.quniform('drive_transit_age1-15_income1', 0.5, 50, 0.5),
    'drive_transit_age1:15_income2': hp.quniform('drive_transit_age1-15_income2', 0.5, 50, 0.5),
    'drive_transit_age1:15_income3': hp.quniform('drive_transit_age1-15_income3', 0.5, 50, 0.5),
    'drive_transit_age16:60_income0': hp.quniform('drive_transit_age16-60_income0', 0.5, 50, 0.5),
    'drive_transit_age16:60_income1': hp.quniform('drive_transit_age16-60_income1', 0.5, 50, 0.5),
    'drive_transit_age16:60_income2': hp.quniform('drive_transit_age16-60_income2', 0.5, 50, 0.5),
    'drive_transit_age16:60_income3': hp.quniform('drive_transit_age16-60_income3', 0.5, 50, 0.5),
    'drive_transit_age61:120_income0': hp.quniform('drive_transit_age61-120_income0', 0.5, 50, 0.5),
    'drive_transit_age61:120_income1': hp.quniform('drive_transit_age61-120_income1', 0.5, 50, 0.5),
    'drive_transit_age61:120_income2': hp.quniform('drive_transit_age61-120_income2', 0.5, 50, 0.5),
    'drive_transit_age61:120_income3': hp.quniform('drive_transit_age61-120_income3', 0.5, 50, 0.5),

    'OnDemand_ride_age1:15_income0': hp.quniform('OnDemand_ride_age1-15_income0', 0.5, 50, 0.5),
    'OnDemand_ride_age1:15_income1': hp.quniform('OnDemand_ride_age1-15_income1', 0.5, 50, 0.5),
    'OnDemand_ride_age1:15_income2': hp.quniform('OnDemand_ride_age1-15_income2', 0.5, 50, 0.5),
    'OnDemand_ride_age1:15_income3': hp.quniform('OnDemand_ride_age1-15_income3', 0.5, 50, 0.5),
    'OnDemand_ride_age16:60_income0': hp.quniform('OnDemand_ride_age16-60_income0', 0.5, 50, 0.5),
    'OnDemand_ride_age16:60_income1': hp.quniform('OnDemand_ride_age16-60_income1', 0.5, 50, 0.5),
    'OnDemand_ride_age16:60_income2': hp.quniform('OnDemand_ride_age16-60_income2', 0.5, 50, 0.5),
    'OnDemand_ride_age16:60_income3': hp.quniform('OnDemand_ride_age16-60_income3', 0.5, 50, 0.5),
    'OnDemand_ride_age61:120_income0': hp.quniform('OnDemand_ride_age61-120_income0', 0.5, 50, 0.5),
    'OnDemand_ride_age61:120_income1': hp.quniform('OnDemand_ride_age61-120_income1', 0.5, 50, 0.5),
    'OnDemand_ride_age61:120_income2': hp.quniform('OnDemand_ride_age61-120_income2', 0.5, 50, 0.5),
    'OnDemand_ride_age61:120_income3': hp.quniform('OnDemand_ride_age61-120_income3', 0.5, 50, 0.5),

    # FrequencyAdjustment
    # Simplied list

    # Midnight
    'r1340_18001_27955': hp.choice('r1340_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1341_18001_27955': hp.choice('r1341_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1342_18001_27955': hp.choice('r1342_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1343_18001_27955': hp.choice('r1343_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1344_18001_27955': hp.choice('r1344_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1345_18001_27955': hp.choice('r1345_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1346_18001_27955': hp.choice('r1346_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1347_18001_27955': hp.choice('r1347_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1348_18001_27955': hp.choice('r1348_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1349_18001_27955': hp.choice('r1349_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1350_18001_27955': hp.choice('r1350_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1351_18001_27955': hp.choice('r1351_18001_27955', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),

    # Morning rush
    'r1340_27956_37624': hp.choice('r1340_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1341_27956_37624': hp.choice('r1341_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1342_27956_37624': hp.choice('r1342_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1343_27956_37624': hp.choice('r1343_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1344_27956_37624': hp.choice('r1344_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1345_27956_37624': hp.choice('r1345_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1346_27956_37624': hp.choice('r1346_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1347_27956_37624': hp.choice('r1347_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1348_27956_37624': hp.choice('r1348_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1349_27956_37624': hp.choice('r1349_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1350_27956_37624': hp.choice('r1350_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1351_27956_37624': hp.choice('r1351_27956_37624', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),

    # Afternoon
    'r1340_37625_59311': hp.choice('r1340_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1341_37625_59311': hp.choice('r1341_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1342_37625_59311': hp.choice('r1342_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1343_37625_59311': hp.choice('r1343_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1344_37625_59311': hp.choice('r1344_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1345_37625_59311': hp.choice('r1345_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1346_37625_59311': hp.choice('r1346_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1347_37625_59311': hp.choice('r1347_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1348_37625_59311': hp.choice('r1348_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1349_37625_59311': hp.choice('r1349_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1350_37625_59311': hp.choice('r1350_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1351_37625_59311': hp.choice('r1351_37625_59311', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),

    # Afternoon rush
    'r1340_59312_72653': hp.choice('r1340_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1341_59312_72653': hp.choice('r1341_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1342_59312_72653': hp.choice('r1342_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1343_59312_72653': hp.choice('r1343_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1344_59312_72653': hp.choice('r1344_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1345_59312_72653': hp.choice('r1345_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1346_59312_72653': hp.choice('r1346_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1347_59312_72653': hp.choice('r1347_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1348_59312_72653': hp.choice('r1348_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1349_59312_72653': hp.choice('r1349_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1350_59312_72653': hp.choice('r1350_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1351_59312_72653': hp.choice('r1351_59312_72653', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),

    # Midnight
    'r1340_72654_79199': hp.choice('r1340_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1341_72654_79199': hp.choice('r1341_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1342_72654_79199': hp.choice('r1342_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1343_72654_79199': hp.choice('r1343_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1344_72654_79199': hp.choice('r1344_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1345_72654_79199': hp.choice('r1345_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1346_72654_79199': hp.choice('r1346_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1347_72654_79199': hp.choice('r1347_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1348_72654_79199': hp.choice('r1348_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1349_72654_79199': hp.choice('r1349_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1350_72654_79199': hp.choice('r1350_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120]),
    'r1351_72654_79199': hp.choice('r1351_72654_79199', [None, 3, 5, 10, 15, 30, 45, 60, 75, 90, 120])

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
    #logging.basicConfig(level=logging.INFO)

    data_root = abspath2("../reference-data")
    input_root = abspath2("../bayesian-input")
    output_root = abspath2("../bayesian-output")

    os.makedirs(input_root, exist_ok=True)
    os.makedirs(output_root, exist_ok=True)

    seed = 123

    np.random.seed(seed)

    # Global variable
    global ITERATION

    ITERATION = 0
    MAX_EVALS = 2
    from hyperopt import fmin
    from hyperopt import tpe
    
    portion=0.5

    
    
    budgetfile = "budget.csv"  
    if not os.path.exists('/home/ubuntu/BeamCompetitions/budget.csv'):
        data=pd.DataFrame(columns=['iter'])
        print(data)
        data.to_csv('/home/ubuntu/BeamCompetitions/budget.csv')
    
    #initialize the 1st mongotrail
    bayes_trials = MongoTrials('mongo://localhost:27017/wh_db/jobs', exp_key=str(datetime.datetime.now()))
    len_trial=21
    while len_trial>=20:
        #bayes_trials = MongoTrials('mongo://localhost:27017/wh_db/jobs', exp_key=str(datetime.datetime.now()))
        #print("After getting trials, I can print")

        best = fmin(fn=objective, space=space, algo=tpe.suggest, max_evals=MAX_EVALS, trials=bayes_trials,rstate=np.random.RandomState(50))
        
        budget=pd.read_csv("/home/ubuntu/BeamCompetitions/budget.csv")
        if(len(budget)==0): n_sim_iters=1   
        else:
            n_sim_iters=budget.loc[len(budget)-1,'iter']+budget_update
            n_sim_iters=int(n_sim_iters)
            
        #budget.loc[len(budget),'iter']=n_sim_iters
        budget = budget.append({'iter': n_sim_iters}, ignore_index=True)
        budget.to_csv("/home/ubuntu/BeamCompetitions/budget.csv",index=False)
        
        
        sorted_trial=sorted(list(bayes_trials.trials), key=lambda x: x['result']['loss'])
        list_trial=list(sorted_trial)
        cutted_trial=list_trial[0:math.floor(len(list_trial)*portion)]
        MAX_EVALS=math.floor(len(list_trial)*portion)
        #suppose the cutted_trial is correct
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
       
    
    if not os.path.exists('../bayesian-output/bayes_trials.csv'):
        data=pd.DataFrame(columns=['loss', 'params', 'iteration','train_time'])
        data.to_csv('../bayesian-output/bayes_trials.csv')
    outputfile=pd.read_csv("../bayesian-output/bayes_trials.csv")
    for result in list(bayes_trials.results):
        #of_connection.write(",".join(result))
        outputfile = outputfile.append({'loss': result['loss'],'params':list(result['params']),'iteration':result['iter'],'train_time':result['train_time']}, ignore_index=True)

        # trials = self.convertResultsToTrials(hyperparameterSpace, filteredResults),
        # iter=iter+1
    outputfile.to_csv('../bayesian-output/bayes_trials.csv')
    #of_connection.close()



if __name__ == "__main__":
    main()
