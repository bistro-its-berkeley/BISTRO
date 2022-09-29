# Filesystem management
import os
import sys
# import logging
# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)
from shutil import copyfile
sys.path.append(os.path.abspath("../"))
sys.path.append(os.path.abspath("../../"))
sys.path.append(os.getcwd())

# from utilities.optimization_utils import *
# from ipyparallel import Client
from optimizer_per_mile_freeform_cl_sf import run_BISTRO

# Utils
import docker
import numpy as np
import pandas as pd
from datetime import datetime

# Optimizers
# from hyperopt import hp
# from hyperopt.mongoexp import MongoTrials
# from hyperopt import fmin
# from hyperopt import tpe
# from optimizer_per_mile_freeform_cl_sf import *

# projection conversion between lat/lon and projected coordinates
from pyproj import Proj, transform

# Logging and settings import
import csv
import yaml 

class RandomSearch:
    def __init__(self,settings_filename="settings.yaml",keepFiles_filename="keepFiles.csv"):
        self.CONFIG = None
        self.loadConfig(settings_filename)

        self.loadKeepFiles(keepFiles_filename)

        # BISTRO input files
        # AGENCY = "sioux_faux_bus_lines"
        self.FREQ_FILE = "FrequencyAdjustment.csv"
        self.SUB_FILE = "ModeSubsidies.csv"
        self.FLEET_FILE = "VehicleFleetMix.csv"
        self.MASS_TRANSIT_FILE = "MassTransitFares.csv"

        self.inProj = Proj('epsg:3857')  # projection
        self.outProj = Proj('epsg:4326')  # lat/lon


    def loadConfig(self,settings_filename):
        # Load config
        CONFIG = {}
        with open(settings_filename) as stream:
            self.CONFIG = yaml.safe_load(stream)

        if not os.path.exists(CONFIG["RESULTS_PATH"]):
            os.makedirs(CONFIG["RESULTS_PATH"])

    def loadKeepFiles(self,keepFiles_filename):
        # headers: Folder	File	File type	Keep?	Analyze
        # return list of filenames with Keep? = 1
        keepFiles = []
        with open(keepFiles_filename, "rt") as csvfile:
            datareader = csv.reader(csvfile)
            yield next(datareader)
            for row in datareader:
                if int(row[3])==1:
                    keepFiles.append(self.getPath(row[0],row[1],row[2]))
            return keepFiles

    def getPath(self, folder, file, filetype):
        if folder =='root':
            return "{}.{}".format(file,filetype)
        if folder =='ITERS':
            return "ITERS/it.{}/{}.{}".format(self.CONFIG["LAST_ITERATION"],file,filetype)
        else:
            return "{}/{}.{}".format(folder,file,filetype)

    def setProjections(self,inProj,outProj):
        # to update the default input and output projections
        if inProj !=None:
            self.inProj = inProj
        if outProj != None:
            self.outProj = outProj

    def setSearchSpaceParams(self,cordon_params=None,subsidy_params=None):
        # add other params for other policies here

        # cordon_params should be a dictionary containing the following:
        # centroids: a list of centroids; one for each cordon
        # radii: a list of radii; one for each cordon
        ## the centroids & radii define the search space for the centroid of each cordon
        # min_radius: minimum radius; defines the search space the radii of the cordons
        # max_radius: maximum radius; defines the search space the radii of the cordons
        # fee_range: the [min, max] of the search space for the cordon fee
        # TODO: add fee type
        # num_cordons: the number of cordons to include in the search space
        # TODO: check necessity of this param ^^
        if cordon_params is not None:
            if 'min_radius' in cordon_params.keys():
                self.setCordonSearchSpace(cordon_params['centroids'], cordon_params['radii'],cordon_params['min_radius'],cordon_params['max_radius'], fee_range=cordon_params['fee_range'],num_cordons = cordon_params['num_cordons'])
            else:
                self.setCordonSearchSpace(cordon_params['centroids'], cordon_params['radii'], fee_range= cordon_params['fee_range'],num_cordons = cordon_params['num_cordons'])

        # subsidy_params should include the following:
        # income_thresholds: a list of [min,max] income thresholds for each eligibility level (e.g., very low, low, etc.)
        # income_search_interval: length of intervals with which to search (note, this results in a grid search for income thresholds)
        # modes: modes to subsidize (can be grouped) e.g., ['RIDE_HAIL_POOLED', ['WALK_TRANSIT','BIKE_TRANSIT','DRIVE_TRANSIT', 'RIDE_HAIL_TRANSIT']
        # subsidy_ranges: [min, max] income threshold values to search for each eligibility level. NOTE: the search spaces may overlap across thresholds, but by default, the random search will ensure increasing thresholds
        # subsidy_interval: length of interval with which to search subsidy values (note, this results in a grid search)
        if subsidy_params is not None:
            # TODO: add error message, since this is all or nothing
            self.setSubsidySearchSpace(subsidy_params['income_thresholds'], subsidy_params['income_search_interval'], subsidy_params['modes'],subsidy_params['subsidy_ranges'],subsidy_params['subsidy_interval'])
        else:
            self.setSubsidySearchSpace()

    def setCordonSearchSpace(self,centroid_list,radii_list,min_radius=None, max_radius=None, fee_range = None, num_cordons = None):
        # [
        #     [-13629234.999116288, 4546248.731626279],
        #     [-13626639.261281533, 4550349.175273786],
        #     [-13633881.839333337, 4541056.829664177],
        # ]
        # [
        #     2411.4568215553545,
        #     2411.4568215553545,
        #     3607.5806132652624
        # ]
        # TODO: ADD CHECK OF PROJECTIONS
        if len(centroid_list)!= len(radii_list):
            print("ERROR: centroid list and radii list are of different lengths")
        else:
            for l in centroid_list:
                if len(l) !=2:
                    print("ERROR: centroid {} wrong dimension".format(l))

            self.CENTROIDS = centroid_list
            self.RADII = radii_list
        if min_radius != None:
            self.MIN_RADIUS = min_radius
        else:
            self.MIN_RADIUS = self.CONFIG["MIN_RADIUS"]
        if max_radius != None:
            self.MAX_RADIUS = max_radius
        else:
            self.MAX_RADIUS = self.CONFIG["MAX_RADIUS"]

        if fee_range!=None:
            self.MAX_PRICE_PER_MILE = fee_range[1]
            self.MIN_PRICE_PER_MILE = fee_range[0]
        else:
            self.MAX_PRICE_PER_MILE = self.CONFIG["MAX_PRICE_PER_MILE"]
            self.MIN_PRICE_PER_MILE = self.CONFIG["MIN_PRICE_PER_MILE"]

        if num_cordons != None:
            self.NUM_CORDONS = num_cordons
        else:
            self.NUM_CORDONS = self.CONFIG["NUM_CORDONS"]

    def setSubsidySearchSpace(self, income_thresholds = None, income_search_interval = 1000, modes = None, subsidy_ranges = None, subsidy_interval = 0.5):
        self.MIN_INCOME_THRESH = []
        self.MAX_INCOME_THRESH = []
        self.SUBSIDY_MODES = []
        if income_thresholds is not None:
            count = 0
            for t in income_thresholds:
                self.MIN_INCOME_THRESH[count] = t[0]
                self.MAX_INCOME_THRESH[count] = t[1]
                count +=1
            self.INCOME_THRESH_INTERVAL = income_search_interval
            count = 0
            for m in modes:
                self.SUBSIDY_MODES[count] = m
                self.MIN_SUBSIDY[count] = subsidy_ranges[count][0]
                self.MAX_SUBSIDY[count] = subsidy_ranges[count][1]
                count+=1
            self.SUBSIDY_INTERVAL = subsidy_interval

        else:
            self.MIN_INCOME_THRESH[0] = self.CONFIG["MIN_INCOME_THRESH_VERY_LOW"]
            self.MAX_INCOME_THRESH[0] = self.CONFIG["MAX_INCOME_THRESH_VERY_LOW"]
            self.MIN_INCOME_THRESH[1] = self.CONFIG["MIN_INCOME_THRESH_LOW"]
            self.MAX_INCOME_THRESH[1] = self.CONFIG["MAX_INCOME_THRESH_LOW"]

            self.INCOME_THRESH_INTERVAL = self.CONFIG["INCOME_THRESH_INTERVAL"]

            self.SUBSIDY_MODES = ['RIDE_HAIL_POOLED',['WALK_TRANSIT','BIKE_TRANSIT','RIDE_HAIL_TRANIST','DRIVE_TRANSIT']]

            self.MIN_SUBSIDY[0] = self.CONFIG["MIN_TNC_SUBSIDY"]
            self.MAX_SUBSIDY[0] = self.CONFIG["MAX_TNC_SUBSIDY"]
            self.MIN_SUBSIDY[1] = self.CONFIG["MIN_TRANSIT_SUBSIDY"]
            self.MAX_SUBSIDY[1] = self.CONFIG["MAX_TRANSIT_SUBSIDY"]

            self.SUBSIDY_INTERVAL = self.CONFIG["SUBSIDY_INTERVAL"]

    def uniform_points_from_circle(self, cordon_idx, N):
        """
        generating points in a cordon that are uniformly distributed
        """
        # np.random.seed(1)

        theta = np.random.uniform(0, 2 * np.pi, N)
        radius = np.random.uniform(0, self.RADII[cordon_idx], N) ** 0.5

        x = self.CENTROIDS[cordon_idx][0] + radius * np.cos(theta)
        y = self.CENTROIDS[cordon_idx][1] + radius * np.sin(theta)

        return x, y




# logger = logging.getLogger(__name__)



# def os_setup():
#     #In order to run mongodb and hyperopt, some file copying is necessary
#     copyfile("optimizer_per_mile_freeform_cl_sf.py", CONFIG["HYPEROPT_PATH"]+"optimizer_per_mile_freeform_cl_sf.py")
#     copyfile("convert_to_input_per_mile_freeform.py", CONFIG["HYPEROPT_PATH"]+"convert_to_input_per_mile_freeform.py")
#     copyfile("../../utilities/optimization_utils.py", CONFIG["HYPEROPT_PATH"]+"optimization_utils.py")
#     copyfile("settings.yaml", CONFIG["HYPEROPT_PATH"]+"settings.yaml")
#     copyfile("optimization_kpi.py", CONFIG["HYPEROPT_PATH"]+"optimization_kpi.py")
#     print("Copied optimizers to hyperopt local direcotry")     
#     return



def main():

    args = sys.argv[1:]
    # args[0]: config filename
    # args[1]: number of samples to generate
    # args[2]: (optional) which cordons to sample

    search_object = RandomSearch(args[0])
    search_object.setSearchSpaceParams()

    num_samples = args[1]

    cordon_dict = {'1':[0],'2':[1],'3':[2],'1_2':[0,1],'1_3':[0,2],'2_3':[1,2],'1_2_3':[0,1,2]}
    if len(args)>2:
        cordons = cordon_dict[args[2]]
    else:
        if search_object.NUM_CORDONS ==3:
            cordons = [0,1,2]
        elif search_object.NUM_CORDONS ==2:
            cordons = [0,1]
        else:
            cordons= [0]
    x={}
    y={}
    # generate search spaces:
    for i in cordons:
        x[i], y[i] = search_object.uniform_points_from_circle(i, 50)  # change the density of fill of the circle

    income_thresh = []
    for i in len(search_object.MIN_INCOME_THRESH):
        income_thresh[i] = list(range(search_object.MIN_INCOME_THRESH[i],search_object.MAX_INCOME_THRESH[i],search_object.INCOME_THRESH_INTERVAL))
    subsidies = []
    for i in len(search_object.SUBSIDY_MODES):
        subsidies[i]  = list(range(search_object.MIN_SUBSIDY[i],search_object.MAX_SUBSIDY[i],search_object.SUBSIDY_INTERVAL))

    # logging.basicConfig(filename='debug.log', encoding='utf-8', level=logging.DEBUG)
    # logging.debug('This message should go to the log file')
    # logging.basicConfig(level=logging.INFO)

    # TODO: MAKE SURE abspath2 IS IMPORTED & UPDATE THESE DIRECTORIES
    input_root = abspath2(os.path.join(search_object.CONFIG["RESULTS_PATH"],"/random_search-input"))
    output_root = abspath2(os.path.join(search_object.CONFIG["RESULTS_PATH"],"/random_search-output"))

    os.makedirs(input_root, exist_ok=True)
    os.makedirs(output_root, exist_ok=True)

    # Keep track of results
    # File to save first results
    out_file = search_object.CONFIG["RESULTS_PATH"]+'/random_search_samples.csv'

    # TODO: ALTER THE OUTPUT ROW HEADERS
    # Write the headers to the file
    headers = ['sample_num','run_time','objective']
    header_written = False

    params = {}

    for n in range(num_samples):
        start_time = datetime.now()
        for i in cordons:
            params['centerx' + str(i)] = round_nearest(np.random.choice(x[i]), 0.005)
            params['centery' + str(i)] = np.random.choice(y[i]) # TODO: JARVIS, why not round nearest?
            params['cradius' + str(i)] = np.random.uniform(search_object.MIN_RADIUS, search_object.MAX_RADIUS)
            params['ctoll' + str(i)] = np.random.uniform(search_object.MIN_PRICE_PER_MILE, search_object.MAX_PRICE_PER_MILE)

        for i in range(len(income_thresh)):
            if i == 0:
                params['incomeThresh'+str(i)] = np.random.choice(income_thresh[i])
            else:
                params['incomeThresh'+str(i)] = np.random.choice(income_thresh[i][np.where(income_thresh[i]>params['incomeThresh'+str(i-1)])[0]])

            for j in subsidies:
                params['subsidyModes'+str(j)] = search_object.SUBSIDY_MODES[j]
                if i==0:
                    params['subsidyVal_mode{}_level{}'.format(j,i)] = np.random.choice(subsidies[j])
                else:
                    params['subsidyVal_mode{}_level{}'.format(j, i)] = np.random.choice(subsidies[j][np.where(subsidies[j]<subsidies[j-1])[0]])
        if header_written==False:
            for k,p in params.items():
                headers.append(k)
            for k in search_object.CONFIG["KPI_LIST"]:
                # TODO: ADD MODE CHOICES
                headers.append(k)
            with open(out_file, 'w') as of_connection:
                writer = csv.writer(of_connection)
                writer.writerow(headers)

            header_written=True

        # # convert params to input:
        # convert_to_input(params, input_root, search_object.CONFIG["SUB_NETWORK_PATH"])

        # run simulation with input (calls convert_to_input):
        result = run_BISTRO(params,search_object.CONFIG["SUB_NETWORK_PATH"], search_object.KEEP_FILES)

        # record output:
        process_results(result,headers,out_file)
        end_time = datetime.now()
        print("{} ({}): Sample {} complete".format(end_time,end_time-start_time,n))

    # logger.info("write row done\n")
    # logger.debug("write row done\n")
    # Run optimization
    # best = fmin(fn=objective, space=space, algo=tpe.suggest,
    #             max_evals=MAX_EVALS, trials=bayes_trials, rstate=np.random.RandomState(50))

    # logger.info("after best\n")
    # logger.debug("after best\n")
    #Post optimization cleanup
    # bayes_trials_results = sorted(bayes_trials.results, key=lambda x: x['loss'])
    # logger.info("experiment end")
    # logger.debug("experiment end")
    # logger.info(str(bayes_trials_results))
    # logger.info("saving experiment result to txt")
    # logger.debug(str(bayes_trials_results))
    # logger.debug("saving experiment result to txt")
    # file = open("result.txt", "w")
    # # for result in bayes_trials_results:
    # #     # logger.info("writting result to csv")
    # #     writer.writerow(result)
    # #     file.write(str(result))
    #     #of_connection.write(",".join(result))
    # # of_connection.close()
    # file.close()
def process_results(result_dict,headers,out_file):
    this_row = {}

    for k, v in result_dict.items():
        if k in headers:
            this_row[k] = v
        elif k in ['params', 'kpi_scores']:
            for k_2, v_2 in v.items():
                if k_2 in headers:
                    this_row[k_2] = v_2

    with open(out_file, 'a') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writerow(this_row)


def round_nearest(x, a):
    return round(x / a) * a

if __name__ == "__main__":
    # set-up the random search:


    # os_setup()
    main()
    rc = Client()
    view = rc.load_balanced_view()

    for _ in range(200):
        view.apply_async(main)

# from ipyparallel import Client
# c = Client()
# c.ids

# dview = c[:]
# dview.block = True  # cause execution on master to wait while tasks sent to workers finish
# dview.apply(lambda : "Hello, World")

# # suppose I want to do leave-one-out cross-validation of a random forest statistical model
# # we define a function that fits to all but one observation and predicts for that observation
# def looFit(index, Ylocal, Xlocal):
#     rf = rfr(n_estimators=100)
#     fitted = rf.fit(np.delete(Xlocal, index, axis = 0), np.delete(Ylocal, index))
#     pred = rf.predict(np.array([Xlocal[index, :]]))
#     return(pred[0])

# dview.execute('from sklearn.ensemble import RandomForestRegressor as rfr')
# dview.execute('import numpy as np')
# # assume predictors are in 2-d array X and outcomes in 1-d array Y
# # here we generate random arrays for X and Y
# # we need to broadcast those data objects to the workers
# import numpy as np
# X = np.random.random((200,5))
# Y = np.random.random(200)
# mydict = dict(X = X, Y = Y, looFit = looFit)
# dview.push(mydict)

# # need a wrapper function because map() only operates on one argument
# def wrapper(i):
#     return(looFit(i, Y, X))

# n = len(Y)
# import time
# time.time()
# # run a parallel map, executing the wrapper function on indices 0,...,n-1
# lview = c.load_balanced_view()
# lview.block = True   # cause execution on master to wait while tasks sent to workers finish
# pred = lview.map(wrapper, range(n))
# time.time()

# print(pred[0:10])
