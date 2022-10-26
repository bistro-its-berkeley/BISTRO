import logging
import os
import shutil
import sys
from os import listdir
from os.path import isfile, join
import uuid
from timeit import default_timer as timer
#import untangle
# import xmltodict
import gzip
import yaml
import pandas as pd
import csv
from convert_to_input import *

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
hyperopt_path = os.path.abspath(os.path.dirname(__file__));
sys.path.append(os.path.abspath("../"))
sys.path.append(os.path.abspath("../../"))
sys.path.append(os.path.abspath("../../../"))
sys.path.append(os.path.abspath("../../../../"))
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
#from utilities.simulation_to_db import parse_and_store_data_to_db
#try:
#    from optimization_utils import *

#except:
#    from utilities.optimization_utils import *


#Load config
CONFIG = {}
with open(os.path.join(hyperopt_path,"settings.yaml")) as stream:
    CONFIG = yaml.safe_load(stream)

sys.path.append(CONFIG["BEAM_PATH"])


#Score translations
# TODO: UPDATE so that the KPIs to record is a parameter of the script
trans_dict = {

    'Iteration':'Iteration',

    'Accessibility: number of secondary locations accessible by car within 15 minutes':'driveSecondaryAccessibility',
    'Accessibility: number of secondary locations accessible by transit within 15 minutes':'transitSecondaryAccessibility',
    'Accessibility: number of work locations accessible by car within 15 minutes':'driveWorkAccessibility',
    'Accessibility: number of work locations accessible by transit within 15 minutes':'transitWorkAccessibility',

    'Congestion: average vehicle delay per passenger trip':'averageVehicleDelayPerPassengerTrip',
    'Congestion: total vehicle miles traveled':'motorizedVehicleMilesTraveled_total',
    #'Equity: average travel cost burden -  secondary':'averageTravelCostBurden_Secondary',
    'Equity: average travel cost burden - work':'averageTravelCostBurden_Work',
    'Level of service: average bus crowding experienced':'busCrowding',
    'Level of service: costs and benefits':'netPublicRevenue',

    'Sustainability: Total grams GHGe Emissions':'sustainability_GHG',
    'Sustainability: Total grams PM 2.5 Emitted':'sustainability_PM',
    'Total Road Pricing Revenue':'TollRevenue'
}


AVG_DELAY = "averageVehicleDelayPerPassengerTrip"
WORK_BURDEN = "averageTravelCostBurden_Work"
BUS_CROWDING = "busCrowding"
COSTS_BENEFITS = "netPublicRevenue"
GHG = "sustainability_GHG"
PM = 'sustainability_PM'
TOLL_REVENUE = "TollRevenue"
VMT = 'motorizedVehicleMilesTraveled_total'
SUBMISSION = "Submission Score"

# KPIs to include in score:
optim_KPI = {AVG_DELAY:1,WORK_BURDEN:1,BUS_CROWDING:1,COSTS_BENEFITS:-1,GHG:1,PM:1,VMT:1}

#Beam parameters
DOCKER_IMAGE ="beammodel/bistro:0.0.4.5.0.25-SNAPSHOT"
CMD_TEMPLATE = "--config {0}"
SCENARIO_NAME = "sf_light"
SCORES_PATH = ("competition", "submissionScores.csv")
DIR_DELIM = "-"
BEAM_PATH = CONFIG["BEAM_PATH"]
# OUT_PATH = CONFIG["RESULTS_PATH"]

logger = logging.getLogger(__name__)


def run_BISTRO(params, network_path,keep_files, config_filename, OUT_PATH):
    """Objective function for Calling the Simulator"""
    
    start = timer()

    print(os.getcwd())

    run_suffix = uuid.uuid4()
    input_dir = os.path.abspath(f"./submission-inputs/{run_suffix}")

    if not os.path.isdir('/submission-inputs'):
        os.system("rm -f ./submission-inputs")
    if not os.path.exists('./submission-inputs'):
        os.system('mkdir ./submission-inputs')
    if not os.path.exists(input_dir):
        os.system(f'mkdir {input_dir}')
        os.system('chmod -R 777 ./submission-inputs')

    # Run simulator, return a score
    docker_cmd = CMD_TEMPLATE.format(config_filename)

    # Write params to input submission csv files
    convert_to_input(params, input_dir,network_path)
    output_dir = os.path.abspath(f"{OUT_PATH}/output")
    if not os.path.exists(output_dir):
        os.system(f'mkdir {output_dir}')
    output_dir = os.path.abspath(f"{OUT_PATH}/output/{run_suffix}")
    if not os.path.exists(output_dir):
        os.system(f'mkdir {output_dir}')

    logger.info("Output_dir: "+output_dir)
    logger.info("Input_dir: "+input_dir)

    cmd = f"sudo docker run -v {output_dir}:/app/output:rw -v {input_dir}:/submission-inputs:ro -v {BEAM_PATH}fixed-data:/fixed-data:rw {DOCKER_IMAGE} {docker_cmd}"
    cmd = cmd + " > log.txt"
    logger.info("!!! execute simulator cmd: %s" % cmd)
    print("Running system command : " + cmd)
    os.system(cmd)
    print("BISTRO finished")
    logger.info("BISTRO finished")

    raw_scores = read_raw_scores(output_dir)
    score = get_score(output_dir,raw_scores)

    logger.info("Score is "+ str(score))

    output_dir = only_subdir(output_dir)
    shutil.copy(os.path.join(output_dir, *SCORES_PATH), input_dir)

    mode_choices = read_mode_choices(output_dir)

    # Clean output folder
    logger.info("cleaning start")
    clean_output(output_dir, keep_files)
    logger.info("clean output finished")
    #copy input files
    os.system(f'cp -r {input_dir} {output_dir}/submission-inputs/')

    # Upload data
    fixed_data = os.path.abspath(f"{BEAM_PATH}fixed-data")
    logger.info("fixed_data path is "+fixed_data)

    run_time = timer() - start

    # Dictionary with information for evaluation
    # TODO: UPDATE OBJECTIVE FUNCTION
    return {'weightedSum': score, 'params': params,
            'run_time': run_time, 'paths': (input_dir, output_dir),
            'kpi_scores':raw_scores, 'mode_choices': mode_choices,'folderID':run_suffix}


def clean_output(output_dir,keep_files):
    path = str(output_dir)

    # Set folder paths
    iters_folder = path + "/ITERS"
    competition_folder = path + "/competition"
    summary_folder = path + "/summaryStats"

    # Remove excess root folder files
    file_list = [f for f in listdir(path) if isfile(join(path, f))]

    for f in file_list:
        if f not in keep_files:
            if os.path.exists(path + "/" + f):
                file_path = path + "/" + f
                os.remove(file_path)

    # Remove excess competition files
    # if os.path.exists(competition_folder + "/submission-inputs"):
    #     shutil.rmtree(competition_folder + "/submission-inputs")
    # if os.path.exists(competition_folder + "/submissionScores.csv"):
    #     os.remove(competition_folder + "/submissionScores.csv")
    if os.path.exists(competition_folder + "/validation-errors.out"):
        os.remove(competition_folder + "/validation-errors.out")

    # Remove files in competition/viz folder
    viz_folder = competition_folder + "/viz"
    file_list = [f for f in listdir(path) if isfile(join(viz_folder, f))]
    keep_files = ["link_stats.csv"]
    for f in file_list:
        if f  not in keep_files:
            if os.path.exists(path + "/" + f):
                file_path = viz_folder + "/" + f
                os.remove(file_path)

    # Remove summary stats directory
    if os.path.exists(summary_folder):
        shutil.rmtree(summary_folder)

    # Remove excess iter files
    iter_list = os.listdir(iters_folder)
    keep_files = [ "averageTravelTimes.csv","events.csv.gz","ridehailRides.csv.gz","linkstats.csv.gz"]
    for folder in iter_list:
        folder_path = iters_folder + "/" + folder
        print(folder_path)
        if folder != "it.{}".format(CONFIG['LAST_ITERATION']-1):
            if os.path.exists(folder_path + "/tripHistogram"):
                shutil.rmtree(folder_path + "/tripHistogram")
            file_list = [f for f in listdir(folder_path) if isfile(join(folder_path, f))]
            for f in file_list:
                os.remove(folder_path + "/" + f)
        else:
            print(folder)
            if os.path.exists(folder_path + "/tripHistogram"):
                shutil.rmtree(folder_path + "/tripHistogram")
            file_list = [f for f in listdir(folder_path) if isfile(join(folder_path, f))]
            print(file_list)
            print(keep_files)
            for f in file_list:
                if f[2:] not in keep_files:
                    os.remove(folder_path + "/" + f)
                else:
                    print('saved: ',f)

def get_score(output_dir,raw_scores):
    standards = load_standards()
    return compute_weighted_scores(raw_scores, standards)


# optim_KPI is hard coded for now
def compute_weighted_scores(raw_scores, standards):
    total_score = 0
    for long_name,short in trans_dict.items():
        if short in optim_KPI.keys():
            total_score += optim_KPI[short]*(raw_scores[short] - standards[short][0])/standards[short][1]

    return total_score


def read_raw_scores(output_dir):
    path = only_subdir(output_dir)
    path = os.path.join(path, "competition/rawScores.csv")
    dic = {}

    with open(path) as csvfile:
        df = pd.read_csv(csvfile)
        kpi_names = list(df.columns)
        for name in kpi_names:
            if name in trans_dict.keys():
                dic[trans_dict[name]] = list(df[name])[-1]
    return dic

def read_mode_choices(output_dir):
    
    path = os.path.join(output_dir, "realizedModeChoice.csv")

    dic = {}
    with open(path) as csvfile:
        df = pd.read_csv(csvfile)
        modes = list(df.columns[1:])
        df['total_trips']=df[modes].sum(axis=1)
        total = list(df['total_trips'])[-1]
        for m in modes:
            dic[m] = list(df[m])[-1]/total
    return dic
            
def load_standards(file = CONFIG["STANDARDS"]):
    dict_name = file
    params = {}
    with open(dict_name, mode='r', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            params[row[0]] = (float(row[1]), float(row[2]))
    return params

def only_subdir(path):
    subdir = os.listdir(path)[0]  # Validates only returned element
    path = os.path.join(path, subdir)
    return path
