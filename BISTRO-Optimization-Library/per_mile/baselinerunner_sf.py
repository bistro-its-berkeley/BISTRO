import logging
import os
import shutil
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
hyperopt_path = os.path.abspath(os.path.dirname(__file__));
sys.path.append(os.path.abspath("../"))
# sys.path.append(os.path.abspath("../"))
sys.path.append(os.path.abspath("../../"))
sys.path.append(os.getcwd())

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
# from convert_to_input_per_mile import *
from hyperopt import STATUS_OK
from optimization_kpi import optim_KPI

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

#Beam parameters
DOCKER_IMAGE = "beammodel/beam-competition:0.0.4.2-noacc-SNAPSHOT"
CMD_TEMPLATE = "--config {0}"
CONFIG_PATH = "/fixed-data/sf_light/urbansim-25k_trial_27.conf"
SCENARIO_NAME = "sf_light"
SCORES_PATH = ("competition", "submissionScores.csv")
DIR_DELIM = "-"
BEAM_PATH = CONFIG["BEAM_PATH"]

OUT_PATH = CONFIG["RESULTS_PATH"]


logger = logging.getLogger(__name__)


def get_score(output_dir):
    standards = load_standards()
    raw_scores = read_raw_scores(output_dir)
    return compute_weighted_scores(raw_scores, standards)


#KPI is hard coded for now
def compute_weighted_scores(raw_scores, standards):
    
    total_score = 0

    for k in optim_KPI:
        total_score += optim_KPI[k]*(raw_scores[k] - standards[k][0])/standards[k][1]

    return total_score


def read_raw_scores(output_dir):
    path = only_subdir(only_subdir(output_dir))
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



# Keep track of evals

start = timer()

print(os.getcwd())

input_dir = os.path.abspath(f"./submission-inputs/baseline_sf")
if not os.path.isdir('/submission-inputs'):
    os.system("rm -f ./submission-inputs")
if not os.path.exists('./submission-inputs'):
    os.system('mkdir ./submission-inputs')
if not os.path.exists(input_dir):
    os.system(f'mkdir {input_dir}')
    os.system('chmod -R 777 ./submission-inputs')

# Run simulator, return a score
sample_size = CONFIG["SAMPLE_SIZE"]
n_sim_iters = CONFIG["SIMULATION_ITERS"]
docker_cmd = CMD_TEMPLATE.format(CONFIG_PATH)

# Write params to input submission csv files
# convert_to_input(params, input_dir)
#add blank input files to the input submission flolder manually

output_dir = os.path.abspath(f"./output/baseline_sf")
cmd = f"docker run -it -v {output_dir}:/output -v {input_dir}:/submission-inputs -v {BEAM_PATH}fixed-data:/fixed-data:rw {DOCKER_IMAGE} {docker_cmd}"
cmd = cmd + " > log.txt"
logger.info("!!! execute simulator cmd: %s" % cmd)
print("Running system command : " + cmd)
os.system(cmd)
print("BISTRO finished")

# score = get_score(output_dir)
# print("SCORE :", score)

# output_dir = only_subdir(only_subdir(output_dir))
# shutil.copy(os.path.join(output_dir, *SCORES_PATH), input_dir)

# paths = (input_dir, output_dir)

# loss = score

# run_time = timer() - start

# print(loss)



