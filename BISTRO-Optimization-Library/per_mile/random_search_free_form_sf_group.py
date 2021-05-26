#Filesystem management
import os
import sys

from shutil import copyfile
sys.path.append(os.path.abspath("../"))
sys.path.append(os.path.abspath("../../"))
sys.path.append(os.getcwd())

from utilities.optimization_utils import *
#from ipyparallel import Client

#Utils
import docker
import numpy as np

#Optimizers
from hyperopt import hp
from hyperopt.mongoexp import MongoTrials
from hyperopt import fmin
from hyperopt import tpe
from optimizer_per_mile_freeform_cl_sf_group import *

#Logging and settings import
import csv
import yaml 
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(filename='rslog',level=logging.INFO)



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

# group_number = CONFIG["GROUP_NUMBER"]
group_number = int(sys.argv[1])
print("group number:", group_number)

if group_number == 1:
	centroids=[[679513.9345290192, 4820946.961045628],
 [686062.4970744384, 4823389.294311632],
 [684251.2798413248, 4820287.10400092]]


	radius=[2391.5398767046877, 1796.1133447950126, 1796.1133447950126]
	min_price_per_mile = 0
	max_price_per_mile = 10

elif group_number == 2:
	centroids=[[685599.6791671999, 4823419.446916052],
 [679823.2008472716, 4820975.419121696],
 [683685.3619621331, 4820284.149058188]]


	radius=[1836.7568578298713, 1961.7685119458943, 1836.7568578298713]

	min_price_per_mile = 0
	max_price_per_mile = 10

elif group_number == 3:
	centroids=[[679219.6191634537, 4820207.260907956],
 [685699.1920853916, 4821068.818422115],
 [682684.6335944278, 4820451.167976001],
 [685938.3541477645, 4824170.815062044],
 [679926.8515083675, 4823801.063998943]]


	radius=[1736.7941490502928,
 1538.5914799766329,
 1538.5914799766329,
 1555.6013022468112,
 1831.3654909983468]

	min_price_per_mile = 0
	max_price_per_mile = 10

elif group_number == 4:
	centroids=[[684699.7649046486, 4824265.58954835],
 [679276.5106197045, 4819831.037554831],
 [685889.5788874996, 4820762.0931578325],
 [680129.1267930991, 4824699.273773672],
 [682756.039648429, 4820518.817513646]]

	radius=[1850.0097480931684,
 1773.4263117961361,
 1571.4842666926202,
 2295.58351808653,
 1571.4842666926202]

	min_price_per_mile = 0
	max_price_per_mile = 10

# MAX_PRICE_PER_MILE = CONFIG["MAX_PRICE_PER_MILE"]


def main():
    print('In main call')
    data_root = abspath2(os.path.join(CONFIG["RESULTS_PATH"],"/reference-data"))
    input_root = abspath2(os.path.join(CONFIG["RESULTS_PATH"],"/bayesian-input"))
    output_root = abspath2(os.path.join(CONFIG["RESULTS_PATH"],"/bayesian-output"))

    os.makedirs(input_root, exist_ok=True)
    os.makedirs(output_root, exist_ok=True)
    
    # Keep track of results
    
    # File to save first results
    # out_file = CONFIG["RESULTS_PATH"]+'/bayes_trials.csv'
    # of_connection = open(out_file, 'w')
    # writer = csv.writer(of_connection)

    # Write the headers to the file
    # writer.writerow(['loss', 'params', 'iteration', 'estimators', 'train_time'])

    params={}
    for i in range(len(radius)):
        params['centerx'+str(i)]=np.random.uniform(centroids[0][0]-radius[0]/2, centroids[0][0]+radius[0]/2)
        params['centery'+str(i)]=np.random.uniform(centroids[0][1]-radius[0]/2, centroids[0][1]+radius[0]/2)
        params['cradius'+str(i)]=np.random.uniform(0 , radius[0])
        params['ctoll'+str(i)]=np.random.uniform(min_price_per_mile, max_price_per_mile)

    print('Run objective')
    objective(params)


if __name__ == "__main__":
    for i in range(15):
        print('In loop #', i)
        main()

