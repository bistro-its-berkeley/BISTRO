import logging
import os
import shutil
import sys
from os import listdir
from os.path import isfile, join

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
hyperopt_path = os.path.abspath(os.path.dirname(__file__));
sys.path.append(os.path.abspath("../"))
sys.path.append(os.path.abspath("../../"))
sys.path.append(os.path.abspath("../../../"))
sys.path.append(os.path.abspath("../../../../"))
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from utilities.simulation_to_db import parse_and_store_data_to_db
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
from convert_to_input_per_mile_freeform import *
from optimization_kpi import optim_KPI

#Load config
CONFIG = {}
with open(os.path.join(hyperopt_path,"settings.yaml")) as stream:
    CONFIG = yaml.safe_load(stream)



sys.path.append(CONFIG["BEAM_PATH"])


#Score translations
# TODO: UPDATE SO KPIs to record is a param
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
# SECOND_BURDEN = "averageTravelCostBurden_Secondary"
BUS_CROWDING = "busCrowding"
COSTS_BENEFITS = "netPublicRevenue"
GHG = "sustainability_GHG"
PM = 'sustainability_PM'
TOLL_REVENUE = "TollRevenue"
VMT = 'motorizedVehicleMilesTraveled_total'
SUBMISSION = "Submission Score"

#Beam parameters
DOCKER_IMAGE ="beammodel/bistro:0.0.4.5.1-SNAPSHOT"
CMD_TEMPLATE = "--config {0}"
CONFIG_PATH ="/fixed-data/sf_light/sf_light-50k_final.conf"
SCENARIO_NAME = "sf_light"
SCORES_PATH = ("competition", "submissionScores.csv")
DIR_DELIM = "-"
BEAM_PATH = CONFIG["BEAM_PATH"]
OUT_PATH = CONFIG["RESULTS_PATH"]

logger = logging.getLogger(__name__)


def run_BISTRO(params, network_path,keep_files):
    """Objective function for Calling the Simulator"""
    # Keep track of evals

    start = timer()

    print(os.getcwd())

    input_suffix = uuid.uuid4()

    input_dir = os.path.abspath(f"./submission-inputs/{input_suffix}")
    if not os.path.isdir('/submission-inputs'):
        os.system("rm -f ./submission-inputs")
    if not os.path.exists('./submission-inputs'):
        os.system('mkdir ./submission-inputs')
    if not os.path.exists(input_dir):
        os.system(f'mkdir {input_dir}')
        os.system('chmod -R 777 ./submission-inputs')

    # Run simulator, return a score
    # sample_size = CONFIG["SAMPLE_SIZE"]
    # n_sim_iters = CONFIG["SIMULATION_ITERS"]
    docker_cmd = CMD_TEMPLATE.format(CONFIG_PATH)

    # Write params to input submission csv files
    convert_to_input(params, input_dir,network_path)

    output_suffix = uuid.uuid4()
    output_dir = os.path.abspath(f"./output/{output_suffix}")
    logger.info("Output_dir: "+output_dir)
    logger.info("Input_dir: "+input_dir)

    cmd = f"sudo docker run -it -v {output_dir}:/app/output:rw -v {input_dir}:/submission-inputs:ro -v {BEAM_PATH}fixed-data:/fixed-data:rw {DOCKER_IMAGE} {docker_cmd}"
    cmd = cmd + " > log.txt"
    logger.info("!!! execute simulator cmd: %s" % cmd)
    print("Running system command : " + cmd)
    os.system(cmd)
    print("BISTRO finished")
    logger.info("BISTRO finished")

    kpi_scores = get_kpis(output_dir)
    score = get_score(output_dir)
    print("SCORE :", score)
    logger.info("Score is "+ str(score))
    output_dir = only_subdir(only_subdir(output_dir))
    shutil.copy(os.path.join(output_dir, *SCORES_PATH), input_dir)

    # Clean output folder
    logger.info("cleaning start")
    clean_output(output_dir, keep_files)
    logger.info("clean output finished")

    # Upload data
    fixed_data = os.path.abspath(f"{BEAM_PATH}fixed-data")
    logger.info("fixed_data path is "+fixed_data)
    # name='sioux_faux_upload_test'
    # logger.info("Upload parameters are"+str(output_dir)+str(fixed_data)+str(SCENARIO_NAME)+str(sample_size)+str(n_sim_iters)+str(name))
    # parse_and_store_data_to_db(output_dir, fixed_data, SCENARIO_NAME, sample_size, n_sim_iters, 
    #                        name=name) #can update name
    # logger.info("upload to db as name "+name)

    paths = (input_dir, output_dir)
    loss = score
    run_time = timer() - start

    print(loss)
    logger.info("loss is "+ str(loss))
    file = open("loss.txt","a")
    file.write(str(loss))
    file.close()

    # Dictionary with information for evaluation
    # TODO: ADD MODE SPLITS TO OUTPUT
    # TODO: UPDATE OBJECTIVE FUNCTION
    return {'objective': loss, 'params': params,
            'run_time': run_time, 'paths': paths,'kpi_scores':kpi_scores}



def clean_output(output_dir,keep_files):
    path = str(output_dir)

    # Set folder paths
    iters_folder = path + "/ITERS"
    competition_folder = path + "/competition"
    summary_folder = path + "/summaryStats"

    # Remove excess root folder files
    file_list = [f for f in listdir(path) if isfile(join(path, f))]

    #keep_files = ["outputEvents.xml.gz", "realizedModeChoice.csv", "summaryStats.csv", "outputHouseholds.xml.gz", "outputNetwork.xml.gz"]
    for file in file_list:
        if file not in keep_files:
            if os.path.exists(path + "/" + file):
                file_path = path + "/" + file
                os.remove(file_path)

    # Remove excess competition files
    if os.path.exists(competition_folder + "/submission-inputs"):
        shutil.rmtree(competition_folder + "/submission-inputs")
    if os.path.exists(competition_folder + "/submissionScores.csv"):
        os.remove(competition_folder + "/submissionScores.csv")
    if os.path.exists(competition_folder + "/validation-errors.out"):
        os.remove(competition_folder + "/validation-errors.out")

    # Remove files in competition/viz folder
    viz_folder = competition_folder + "/viz"
    file_list = [f for f in listdir(path) if isfile(join(viz_folder, f))]
    keep_files = ["link_stats.csv"]
    for file in file_list:
        if file not in keep_files:
            if os.path.exists(path + "/" + file):
                file_path = viz_folder + "/" + file
                os.remove(file_path)

    # Remove summary stats directory
    if os.path.exists(summary_folder):
        shutil.rmtree(summary_folder)

    # Remove excess iter files
    iter_list = os.listdir(iters_folder)
    keep_files = [ "averageTravelTimes.csv","events.csv.gz","ridehailRides.csv.gz","linkstats.csv.gz"]
    for folder in iter_list:
        folder_path = iters_folder + "/" + folder
        if folder != "it.{}".format(CONFIG['SIMULATION_ITERS']):
            if os.path.exists(folder_path + "/tripHistogram"):
                shutil.rmtree(folder_path + "/tripHistogram")
            file_list = [f for f in listdir(folder_path) if isfile(join(folder_path, f))]
            for file in file_list:
                os.remove(folder_path + "/" + file)
        else:
            if os.path.exists(folder_path + "/tripHistogram"):
                shutil.rmtree(folder_path + "/tripHistogram")
            file_list = [f for f in listdir(folder_path) if isfile(join(folder_path, f))]
            for file in file_list:
                os.remove(folder_path + "/" + file)
                if file not in keep_files:
                    os.remove(folder_path + "/" + file)

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

def only_subdir(path):
    subdir, = os.listdir(path)  # Validates only returned element
    path = os.path.join(path, subdir)
    return path