import logging
import os
import shutil
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
hyperopt_path = os.path.abspath(os.path.dirname(__file__));
# hyperopt_path = config["HYPEROPT_PATH"]
# sys.path.append(hyperopt_path)
sys.path.append(os.path.abspath("../"))
sys.path.append(os.path.join(os.path.dirname(__file__), '..')) 


try:
    from optimization_utils import *
except:
    from utilities.optimization_utils import *

import uuid
from timeit import default_timer as timer
import untangle
import xmltodict
import gzip
import yaml
import pandas as pd
import csv
from convert_to_input_cordon import *
from hyperopt import STATUS_OK
from optimization_kpi import optim_KPI
from hypervolume_optimizer import *

#Load config
CONFIG = {}
with open(os.path.join(hyperopt_path,"settings.yaml")) as stream:
    CONFIG = yaml.safe_load(stream)



sys.path.append(CONFIG["BEAM_PATH"])


#Score translations
trans_dict = {

    'Iteration':'Iteration',

    'Accessibility: number of secondary locations accessible by car within 15 minutes':'driveSecondaryAccessibility',
    'Accessibility: number of secondary locations accessible by transit within 15 minutes':'transitSecondaryAccessibility',
    'Accessibility: number of work locations accessible by car within 15 minutes':'driveWorkAccessibility',
    'Accessibility: number of work locations accessible by transit within 15 minutes':'transitWorkAccessibility',

    'Congestion: average vehicle delay per passenger trip':'averageVehicleDelayPerPassengerTrip',
    'Congestion: total vehicle miles traveled':'motorizedVehicleMilesTraveled_total',
    'Equity: average travel cost burden -  secondary':'averageTravelCostBurden_Secondary',
    'Equity: average travel cost burden - work':'averageTravelCostBurden_Work',
    'Level of service: average bus crowding experienced':'busCrowding',
    'Level of service: costs and benefits':'costBenefitAnalysis',

    'Sustainability: Total grams GHGe Emissions':'sustainability_GHG',
    'Sustainability: Total grams PM 2.5 Emitted':'sustainability_PM',
    'TollRevenue':'TollRevenue',
    'VMT':'VMT'
}

AVG_DELAY = "averageVehicleDelayPerPassengerTrip"
WORK_BURDEN = "averageTravelCostBurden_Work"
SECOND_BURDEN = "averageTravelCostBurden_Secondary"
BUS_CROWDING = "busCrowding"
COSTS_BENEFITS = "costBenefitAnalysis"
GHG = "sustainability_GHG"
TOLL_REVENUE = "TollRevenue"
SUBMISSION = "Submission Score"


logger = logging.getLogger(__name__)

# pre-existing results path - BEAM has already generated this data
RESULTS_PATH = "/Users/makenaschwinn/Desktop/bistro/AWS_samples/"

def test_objective(sample_dir):
    output_dir = sample_dir_path+"/output/"
    output_dir = only_subdir(output_dir)
    # /Users/makenaschwinn/Desktop/bistro/AWS_samples/5eb6e67825f364718ddb1527/output/f3d0b47f-a106-406c-9529-1765ec830f69/
    print(f"output_dir: {output_dir}")
    # output_dir = only_subdir(only_subdir(only_subdir(output_dir)))
    # /Users/makenaschwinn/Desktop/bistro/AWS_samples/5eb6e67825f364718ddb1527/output/f3d0b47f-a106-406c-9529-1765ec830f69/sioux_faux/sioux_faux-15k__2020-05-09_17-21-06
    # content directory

    # get current BISTRO iteration... 

    score = get_score(output_dir, hv_method=CONFIG["HYPERVOLUME"])
    print("SCORE :", score)


def objective(params):
    """Objective function for Calling the Simulator"""
    # Keep track of evals

    start = timer()

    print(os.getcwd())

    input_dir = os.path.abspath(f"./submission-inputs/{input_suffix}")
    
    # Run simulator, return a score
    sample_size = CONFIG["SAMPLE_SIZE"]
    n_sim_iters = CONFIG["SIMULATION_ITERS"]

    output_dir = os.path.abspath(f"./output/{output_suffix}")
    
    score = get_score(output_dir, hv_method=CONFIG["HYPERVOLUME"])
    print("SCORE :", score)

    output_dir = only_subdir(only_subdir(output_dir))
    shutil.copy(os.path.join(output_dir, *SCORES_PATH), input_dir)

    paths = (input_dir, output_dir)

    loss = score

    run_time = timer() - start

    print(loss)

    # Dictionary with information for evaluation
    return {'loss': loss, 'params': params, 
            'train_time': run_time, 'status': STATUS_OK, 'paths': paths}



def get_score(output_dir, hv_method=False):
    standards = load_standards()
    raw_scores = read_raw_scores(output_dir)
    if hv_method:
        return hypervolume_score(raw_scores, standards, output_dir)
    else: 
        return compute_weighted_scores(raw_scores, standards)


#KPI is hard coded for now
def compute_weighted_scores(raw_scores, standards):
    
    total_score = 0

    for k in optim_KPI:
        total_score += optim_KPI[k]*(raw_scores[k] - standards[k][0])/standards[k][1]

    return total_score


def read_raw_scores(output_dir):
    # output_dir is already the appropriate path
    # path = output_dir
    path = only_subdir(only_subdir(output_dir))
    

    # SKIP for pre-existing results - they were already copied
    #Copy outevents
    if not os.path.isfile(os.path.join(path, "outputEvents.xml.gz")):
        print("COPYING")
        print("SHOULD SKIP")
        shutil.copy(os.path.join(path, "ITERS/it.0/0.events.xml.gz"), os.path.join(path, "outputEvents.xml.gz"))
        # shutil.copy(os.path.join(path, "ITERS/it.30/30.events.xml.gz"), os.path.join(path, "outputEvents.xml.gz"))


    path = os.path.join(path, "competition/rawScores.csv")
    dic = {}

    with open(path) as csvfile:
        df = pd.read_csv(csvfile)
        kpi_names = list(df.columns)
        for name in kpi_names:
            dic[trans_dict[name]] = list(df[name])[-1]

    dic['TollRevenue'] = read_toll_revenue(output_dir)
    return dic


def read_toll_revenue(output_dir):

    # remove only_subdir here because already modified 
    output_dir = only_subdir(only_subdir(output_dir))
    f = gzip.open(os.path.join(output_dir,'outputEvents.xml.gz'), 'rb')
    print("Loading events")
    doc = xmltodict.parse(f.read())
    print("Parsing tolls paid")
    totalTolls = 0
    for event in doc['events']['event']:
        if '@tollPaid' in event.keys():
            totalTolls += float(event['@tollPaid'])

    return totalTolls
            
def load_standards(file = CONFIG["STANDARDS"]):
    dict_name = file
    params = {}
    with open(dict_name) as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            params[row[0]] = (float(row[1]), float(row[2]))
    return params

if __name__=="__main__":
    # do things
    # find output directories
    samples_dirs = []
    for sample_dir in os.listdir(RESULTS_PATH):
        if not sample_dir.startswith('.'):
            # MacOS sometimes generates .DS_Store - exclude this
            samples_dirs.append(sample_dir)
    print("Results directories: ")
    print(samples_dirs)

    for sample_dir in samples_dirs:
        # TODO
        sample_dir_path = RESULTS_PATH + sample_dir
        test_objective(sample_dir_path)

