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
logging.basicConfig(filename='upload_info',
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%H:%M:%S',
                            level=logging.INFO)
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
DOCKER_IMAGE = "beammodel/beam-competition:0.0.3-SNAPSHOT"
CMD_TEMPLATE = "--scenario {0} --sample-size {1} --iters {2} --config {3}"
CONFIG_PATH = "/fixed-data/sioux_faux/sioux_faux-15k_debugging.conf"
SCENARIO_NAME = "sioux_faux"
SCORES_PATH = ("competition", "submissionScores.csv")
DIR_DELIM = "-"
BEAM_PATH = CONFIG["BEAM_PATH"]

OUT_PATH = CONFIG["RESULTS_PATH"]


logger = logging.getLogger(__name__)


# Run simulator, return a score
sample_size = CONFIG["SAMPLE_SIZE"]
n_sim_iters = CONFIG["SIMULATION_ITERS"]

# output_suffix = "" # edit here
# output_dir = os.path.abspath(f"./output/{output_suffix}")
output_dir = "/home/ubuntu/BISTRO/HaochongXia-OPT/per_mile/debugging/output/16/5feab4de32e0981e9de9c21f/output/d8016e32-a1b5-4e91-be9c-c7108b75536b/sioux_faux/sioux_faux-15k__2020-12-29_04-53-35"
logger.info("Output_dir: "+output_dir)

# Upload data
fixed_data = "/home/ubuntu/BISTRO/fixed-data"
logger.info("Fixed_data: "+fixed_data)
name='sioux_faux_15k_freeform_optimal'
logger.info("Upload parameters are"+str(output_dir)+str(fixed_data)+str(SCENARIO_NAME)+str(sample_size)+str(n_sim_iters)+str(name))
print("Upload parameters are"+str(output_dir)+str(fixed_data)+str(SCENARIO_NAME)+str(sample_size)+str(n_sim_iters)+str(name))
simulation_id=parse_and_store_data_to_db(output_dir, fixed_data, SCENARIO_NAME, sample_size, n_sim_iters, 
                        name=name) #can update name
logger.info("upload to db as name "+name+' and simulation_id is '+simulation_id)
print("upload to db as name "+name+' and simulation_id is '+simulation_id)




# parse_and_store_data_to_db(
        # output_path, fixed_data, city, sample_size, iteration, name='test',
        # cordon=False, standardize_score=False, local=False, db_name='bistro'):

#     # city = 'sf_light'
#     # sample_size = '25k'
#     # iteration = 0

#     city = 'sioux_faux'
#     sample_size = '15k'
#     iteration = 99

#     output_root = '/Users/zangnanyu/bistro/BeamCompetitions/output'
#     input_root = '/Users/zangnanyu/bistro/BeamCompetitions/submission-inputs'
#     fixed_data = '/Users/zangnanyu/bistro/BeamCompetitions/fixed-data'

#     print("start running simulation")
#     # log = os.popen(
#     #     """docker run -it --memory=8g --cpus=4 -v {}:/submission-inputs:ro
#     #     -v {}:/output:rw beammodel/beam-competition:0.0.3-SNAPSHOT
#     #     --scenario {} --sample-size {} --iters {}
#     #     """.format(input_root, output_root, city, sample_size, iteration)
#     # ).read()
#     # print(log)

#     # use regex to match the special format in BEAM output directory path
#     # '__yyyy-mm-dd_hh-mm-ss'

#     # datetime_pattern = r"__(\d+)-(\d+)-(\d+)_(\d+)-(\d+)-(\d+)"
#     # match = re.search(datetime_pattern, log)

#     # output_root += '/' if output_root[-1] != '/' else ''
#     # output_path = (output_root + city + '/' +  city + '-' + sample_size + match.group())
#     output_path = '/Users/zangnanyu/bistro/BeamCompetitions/fixed-data/sioux_faux/bau/warm-start/sioux_faux-15k__warm-start'

#     parse_and_store_data_to_db(output_path, fixed_data, city, sample_size, iteration)




