import logging
import os
import shutil
import sys
from os import listdir
from os.path import isfile, join
from shutil import copyfile

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
hyperopt_path = os.path.abspath(os.path.dirname(__file__));
sys.path.append(os.path.abspath("../"))
sys.path.append(os.path.abspath("../../"))
sys.path.append(os.path.abspath("../../../"))
sys.path.append(os.path.abspath("../../../../"))
logger = logging.getLogger(__name__)
logging.basicConfig(filename='rslog_opt',level=logging.INFO)

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
from convert_to_input_per_mile_freeform_group import *
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
# DOCKER_IMAGE = "beammodel/bistro:0.0.4.4-SNAPSHOT"
# DOCKER_IMAGE = "beammodel/beam-competition:0.0.4.2-noacc-SNAPSHOT"
# DOCKER_IMAGE = "/global/scratch/chenjia_lu/beam-competition_0.0.4.2-noacc-SNAPSHOT.sif"
DOCKER_IMAGE = "beammodel/beam-competition:0.0.3-SNAPSHOT"
# DOCKER_IMAGE = "beammodel/beam-competition:0.0.3-SNAPSHOT"
CMD_TEMPLATE = "--config {0}"
# CONFIG_PATH = "/fixed-data/sf_light/urbansim-50k_Cal2_simpleNet.conf"
# CONFIG_PATH ="/fixed-data/sf_light/sf_light-25k.conf"
# CONFIG_PATH = "/fixed-data/sioux_faux/sioux_faux-15k.conf"
# CONFIG_PATH = "/global/scratch/chenjia_lu/BISTRO/fixed-data/sf_light/urbansim-25k_trial_65.conf"
CONFIG_PATH = "/fixed-data/sioux_faux/sioux_faux-15k.conf"
# CONFIG_PATH = "/fixed-data/sioux_faux/sioux_faux-15k_debugging.conf"
# SCENARIO_NAME = "sf_light"
SCENARIO_NAME = "sioux_faux"
# SCENARIO_NAME = "sioux_faux"
SCORES_PATH = ("competition", "submissionScores.csv")
DIR_DELIM = "-"
BEAM_PATH = CONFIG["BEAM_PATH"]
# print(BEAM_PATH)
OUT_PATH = CONFIG["RESULTS_PATH"]


logger = logging.getLogger(__name__)




def objective(params):
    """Objective function for Calling the Simulator"""
    # Keep track of evals
    # group_number = "g" + str(CONFIG["GROUP_NUMBER"])
    
    group_number = "g" + str(sys.argv[1])
    
    start = timer()

    print('Current directory: ', os.getcwd())

    # Create input directory
    input_suffix = uuid.uuid4()
    print('input suffix: ', input_suffix)
    input_dir = os.path.abspath(f"./randomsearch/submission-inputs/{group_number}/{input_suffix}")

    # input_dir = os.path.abspath(f"./submission-inputs/{input_suffix}")
    if not os.path.isdir('./submission-inputs'):
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

    # Create output directory
    output_suffix = uuid.uuid4()
    print('Output suffix: ', output_suffix)
    
    output_group = os.path.abspath(f"./randomsearch/output/{group_number}")
    if not os.path.exists(output_group):
        os.system(f'mkdir {output_group}')
    
    output_dir = os.path.abspath(f"{output_group}/{output_suffix}")

    if not os.path.exists(output_dir):
        os.system(f'mkdir {output_dir}')

    logger.info("Output_dir: "+output_dir)
    logger.info("Input_dir: "+input_dir)
    
    # Write params to input submission csv files
    print("output dir:", output_dir)
    convert_to_input(params, input_dir, output_dir)

    # Run simulation
    # tmpdir = "/global/scratch/chenjia_lu/tmp"
    # tmpdir_cmd = f'export SINGULARITY_TMPDIR="{tmpdir}"'

    # cachedir = "/global/scratch/chenjia_lu/s_cache"
    # cachedir_cmd = f'export SINGULARITY_CACHEDIR="{cachedir}"'

    # fixed_dir = "/global/scratch/chenjia_lu/BISTRO/fixed-data"

    cmd = f"docker run -it -v {output_dir}:/output -v {input_dir}:/submission-inputs -v {BEAM_PATH}fixed-data:/fixed-data:rw {DOCKER_IMAGE} {docker_cmd}"
    cmd = cmd + " > log.txt"
    logger.info("!!! execute simulator cmd: %s" % cmd)
    print("Running system command : ", cmd)

    # os.chdir('/')
    current_dir = os.getcwd()

    logger.info("Moved to root: %s" % current_dir)
    print("Moved to root: ", current_dir)

    # os.system(tmpdir_cmd)
    # os.system(cachedir_cmd)

    os.system(cmd)

    # os.chdir('/global/scratch/chenjia_lu/BISTRO/BISTRO-Optimization-Library/per_mile/random_search')
    # current_dir = os.getcwd()

    # logger.info("Moved to BISTRO: %s" % current_dir)
    # print("Moved to BISTRO:", current_dir )
    
    logger.info("BISTRO finished")
    print("BISTRO finished")
    
    #write VMT and PM25
    print("get score:", output_dir)
    score = get_score(output_dir)
    
    # Aggregate files for analysis
    aggregate_output(output_dir, group_number, output_suffix)

    #clean output
    output_dir = os.path.abspath(f"{output_dir}/sioux_faux")
    output_dir = only_subdir(output_dir)
    # output_dir = only_subdir(only_subdir(output_dir))
    shutil.copy(os.path.join(output_dir, *SCORES_PATH), input_dir)

    # Clean output folder
    logger.info("cleaning start")
    print('cleaning start')
    clean_output(output_dir)
    logger.info("clean output finished")
    print('cleaning finished')

    # logger.info("Score is "+ str(score))
    # print("SCORE :", score)
    # output_dir = only_subdir(only_subdir(output_dir))
    # shutil.copy(os.path.join(output_dir, *SCORES_PATH), input_dir)

    # paths = (input_dir, output_dir)

    # loss = score

    # run_time = timer() - start

    # print(loss)
    # logger.info("loss is "+ str(loss))
    # file = open("loss.txt","a")
    # file.write(str(loss))
    # file.close()
    # # Dictionary with information for evaluation
    # return {'loss': loss, 'params': params, 
    #         'train_time': run_time, 'status': STATUS_OK, 'paths': paths}
    return 0


def clean_output(output_dir):
    path = str(output_dir)

    # Set folder paths
    iters_folder = path + "/ITERS"
    competition_folder = path + "/competition"
    summary_folder = path + "/summaryStats"

    # Remove excess root folder files
    file_list = [f for f in listdir(path) if isfile(join(path, f))]
    keep_files = ["modeChoice.csv",
     "modeChoice.png",
     "summaryStats.csv",
     "summaryVehicleStats.csv"]
     
    for file in file_list:
        if file not in keep_files:
            if os.path.exists(path + "/" + file):
                file_path = path + "/" + file
                os.remove(file_path)

    # Remove excess competition files
    if os.path.exists(competition_folder + "/validation-errors.out"):
        os.remove(competition_folder + "/validation-errors.out")

    # Remove files in competition/viz folder
    viz_folder = competition_folder + "/viz"
    file_list = [f for f in listdir(viz_folder) if isfile(join(viz_folder, f))]
    keep_files = ["link_stats.csv"]
    for file in file_list:
        if file not in keep_files:
            if os.path.exists(path + "/" + file):
                file_path = viz_folder + "/" + file
                os.remove(file_path)

    # Remove summary stats files
    file_list = [f for f in listdir(summary_folder) if isfile(join(summary_folder, f))]
    for file in file_list:
        if os.path.exists(summary_folder + "/" + file):
            os.remove(summary_folder + "/" + file)
    
    # Remove summary stats directories
    folder_list = os.listdir(summary_folder)
    keep_folders = ["numberOfVehicles", "rawScores"]
    for folder in folder_list:
        if folder not in keep_folders:
            shutil.rmtree(summary_folder + "/" + folder)

    # Remove excess iter files
    iter_list = os.listdir(iters_folder)
    # keep_files = ["events.xml.gz", "modeChoice.csv", "modeChoice.png"]
    for folder in iter_list:
        folder_path = iters_folder + "/" + folder
        if os.path.exists(folder_path + "/tripHistogram"):
            shutil.rmtree(folder_path + "/tripHistogram")
        if os.path.exists(folder_path + "/graphs"):
            shutil.rmtree(folder_path + "/graphs")
            
        file_list = [f for f in listdir(folder_path) if isfile(join(folder_path, f))]
        for file in file_list:
            if file.endswith('events.xml.gz') == False and file.endswith('modeChoice.csv') == False and file.endswith('modeChoice.png') == False:
                os.remove(folder_path + "/" + file)

def aggregate_output(output_dir, group_number, output_suffix):
    agg_output = os.path.abspath(f"./randomsearch_agg_output")
    if not os.path.exists(agg_output):
        os.system(f'mkdir {agg_output}')
    
    agg_output = os.path.abspath(f"./randomsearch_agg_output/{group_number}")
    if not os.path.exists(agg_output):
        os.system(f'mkdir {agg_output}')
    
    # Copy circle_params
    if not os.path.exists(f'{agg_output}/circle_params'):
        os.system(f'mkdir {agg_output}/circle_params')
    if os.path.exists(f"{output_dir}/circle_params.txt"):
        copyfile(f"{output_dir}/circle_params.txt", f"{agg_output}/circle_params/circle_params_{output_suffix}.txt")
    
    # output_dir = only_subdir(only_subdir(output_dir))
    output_dir = os.path.abspath(f"{output_dir}/sioux_faux")
    output_dir = only_subdir(output_dir)
    
    # output_dir = str(output_dir)
    # shutil.copy(os.path.join(output_dir, *SCORES_PATH), input_dir)
    competition_folder = f"{output_dir}/competition"
       
    # Copy Submission scores from competition folder
    logger.info("start copy submission score")
    if not os.path.exists(f'{agg_output}/submissionScores'):
        os.system(f'mkdir {agg_output}/submissionScores')

    if os.path.exists(f"{competition_folder}/submissionScores.csv"):
        copyfile(competition_folder + "/submissionScores.csv", f"{agg_output}/submissionScores/submissionScores_{output_suffix}.csv")
    logger.info("end copy submission score")

    # Copy rawScores.csv from competition folder
    logger.info("start copy rawScores.csv")
    if not os.path.exists(f'{agg_output}/rawScores'):
        os.system(f'mkdir {agg_output}/rawScores')

    if os.path.exists(f"{competition_folder}/rawScores.csv"):
        copyfile(competition_folder + "/rawScores.csv", f"{agg_output}/rawScores/rawScores_{output_suffix}.csv")
    logger.info("end copy raw scores.")
    
    
    # Copy modeChoice from root folder
    logger.info("start copy realized modeChoice")
    if not os.path.exists(f'{agg_output}/modeChoice'):
        os.system(f'mkdir {agg_output}/modeChoice')
        
    root_dir = str(output_dir)
    if os.path.exists(root_dir + "/realizedModeChoice.csv"):
        copyfile(root_dir + "/realizedModeChoice.csv", f"{agg_output}/modeChoice/realizedModeChoice_{output_suffix}.csv")
    if os.path.exists(root_dir + "/realizedModeChoice.png"):
        copyfile(root_dir + "/realizedModeChoice.png", f"{agg_output}/modeChoice/realizedModeChoice_{output_suffix}.png")
    if os.path.exists(root_dir + "/modeChoice.csv"):
        copyfile(root_dir + "/modeChoice.csv", f"{agg_output}/modeChoice/modeChoice_{output_suffix}.csv")
    if os.path.exists(root_dir + "/modeChoice.png"):
        copyfile(root_dir + "/modeChoice.png", f"{agg_output}/modeChoice/modeChoice_{output_suffix}.png")
    
    logger.info("end copy realized modeChoice")

def get_score(output_dir):
    # logger.info("load_standards")
    standards = load_standards()
    # logger.info("raw_scores")
    raw_scores = read_raw_scores(output_dir)
    # logger.info("read_VMT_and_PM25")
    VMT=read_VMT_and_PM25(output_dir)
    raw_scores={**raw_scores, **VMT}
    # logger.info("compute_weighted_scores")
    return compute_weighted_scores(raw_scores, standards,output_dir)


#KPI is hard coded for now
def compute_weighted_scores(raw_scores, standards,output_dir):
    
    total_score = 0
    logger.info("Compute weighted scores: %s" % optim_KPI)
    for k in optim_KPI:
        total_score += optim_KPI[k]*(raw_scores[k] - standards[k][0])/standards[k][1]
        if k=="VMT":
            VMTscore=optim_KPI[k]*(raw_scores[k] - standards[k][0])/standards[k][1]
        if k=="sustainability_PM":
            PMscore=optim_KPI[k]*(raw_scores[k] - standards[k][0])/standards[k][1]
    # logger.info("compute_weighted_scores_before_VMT")
    #update weighted with VMT 
    # path = only_subdir(only_subdir(output_dir))
    path = os.path.abspath(f"{output_dir}/sioux_faux")
    path = only_subdir(path)
    
    submission_score_path = os.path.join(path, "competition/submissionScores.csv")
    submission_score = csv.reader(open(submission_score_path)) # Here your csv file
    submission_score = list(submission_score)
    submission_score[-1][-1]=str(total_score)
    submission_score[1][-1]=str(VMTscore)
    submission_score[8][-1]=str(VMTscore)
    writer = csv.writer(open(submission_score_path, 'w'))
    writer.writerows(submission_score)
    # logger.info("compute_weighted_scores_after_VMT")
    return total_score


def read_raw_scores(output_dir):
    # path = only_subdir(only_subdir(output_dir))
    path = os.path.abspath(f"{output_dir}/sioux_faux")
    path = only_subdir(path)
    print('path is',path)
    path = os.path.join(path, "competition/rawScores.csv")
    print('path is',path)
    dic = {}

    with open(path) as csvfile:
        df = pd.read_csv(csvfile)
        kpi_names = list(df.columns)
        for name in kpi_names:
            print(name)
            dic[trans_dict[name]] = list(df[name])[-1]

    dic['TollRevenue'] = read_toll_revenue(output_dir)
    # logger.info("TollRevenue")
    # logger.info(dic['TollRevenue'])
    return dic

def read_VMT_and_PM25(output_dir):
    # path = only_subdir(only_subdir(output_dir))
    path = os.path.abspath(f"{output_dir}/sioux_faux")
    path = only_subdir(path)
    
    path = os.path.join(path, "summaryVehicleStats.csv")
    dic = {}
    beamFuelTypes=CONFIG["beamFuelTypes"]
    beamFuelTypes_dict={}
    # logger.info("read_VMT_and_PM25_before_prep")
    with open(beamFuelTypes) as csvfile:
        df = pd.read_csv(csvfile)
        fuelTypeId_list=list(df["fuelTypeId"])
        pm25PerVMT_list=list(df["pm25PerVMT"])
        for i in range(len(fuelTypeId_list)):
            beamFuelTypes_dict[fuelTypeId_list[i]]=float(pm25PerVMT_list[i])
    vehicleTypes=CONFIG["vehicleTypes"]
    vehicleTypes_dict={}
    with open(vehicleTypes) as csvfile:
        df = pd.read_csv(csvfile)
        vehicleTypeId_list=list(df["vehicleTypeId"])
        primaryFuelType_list=list(df["primaryFuelType"])
        for i in range(len(vehicleTypeId_list)):
            vehicleTypes_dict[vehicleTypeId_list[i]]=primaryFuelType_list[i]
    # logger.info("read_VMT_and_PM25_after_prep")

    with open(path) as csvfile:
        # logger.info("read_VMT_and_PM25_after_prep_on")
        df = pd.read_csv(csvfile)
        iter_list=list(df["iteration"])
        last_iter=iter_list[-1]
        dic[trans_dict["VMT"]]=0
        dic['sustainability_PM']=0
        VMT_list=list(df["vehicleMilesTraveled"])
        vehicleType_list=list(df["vehicleType"])
        # logger.info("read_VMT_and_PM25_after_prep_on_before_iter")
        for i in range(len(iter_list)-1,-1,-1):
            if iter_list[i]!=last_iter:
                # logger.info("read_VMT_and_PM25_after_prep_on_before_iter_break")
                break
            else:
                if float(VMT_list[i])==0:
                    continue
                # logger.info("float(VMT_list[i])")
                # logger.info(float(VMT_list[i]))
                dic[trans_dict["VMT"]]+= float(VMT_list[i])
                vehicletype=vehicleType_list[i]
                # logger.info("vehicletype")
                # logger.info(vehicletype)
                if vehicletype=="CAR-TYPE-DEFAULT":
                    fueltype='gasoline'
                else:
                    fueltype=vehicleTypes_dict[vehicletype]
                # logger.info("fueltype")
                # logger.info(fueltype)
                if fueltype=="Food":
                    pm25PerVMT=0
                else:
                    pm25PerVMT=float(beamFuelTypes_dict[fueltype])
                # logger.info(pm25PerVMT)
                dic['sustainability_PM']+=pm25PerVMT*float(VMT_list[i])
                # logger.info("dic['sustainability_PM']")
                # logger.info(dic['sustainability_PM'])
    # logger.info("read_VMT_and_PM25_before_write")
    
    #modify the submissionscore.csv add VMT modify PM2.5 change final score
    # path = only_subdir(only_subdir(output_dir))
    path = os.path.abspath(f"{output_dir}/sioux_faux")
    path = only_subdir(path)
    
    submission_score_path = os.path.join(path, "competition/submissionScores.csv")
    submission_score = csv.reader(open(submission_score_path)) # Here your csv file
    submission_score = list(submission_score)
    for i in range(len(submission_score)):
        if submission_score[i][0]=='Sustainability: Total grams PM 2.5 Emitted':
            submission_score[i][4]=str(dic[trans_dict['Sustainability: Total grams PM 2.5 Emitted']])
    submission_score.insert(1, [trans_dict["VMT"],"0","0","0",str(dic[trans_dict["VMT"]]),"0"])
    writer = csv.writer(open(submission_score_path, 'w'))
    writer.writerows(submission_score)
    # logger.info("read_VMT_and_PM25_after_write")
    return dic

def read_toll_revenue(output_dir):
    # output_dir = only_subdir(only_subdir(output_dir))
    output_dir = os.path.abspath(f"{output_dir}/sioux_faux")
    output_dir = only_subdir(output_dir)
    
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