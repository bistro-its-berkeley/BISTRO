# Filesystem management
import os
import sys
from shutil import copyfile
sys.path.append(os.path.abspath("../"))
sys.path.append(os.path.abspath("../../"))
sys.path.append(os.getcwd())

# from utilities.optimization_utils import *
# from ipyparallel import Client
from optimizer import run_BISTRO
import numpy as np
import pandas as pd
from datetime import datetime

# projection conversion between lat/lon and projected coordinates
from pyproj import Proj, transform

# Logging and settings import
import csv
import yaml 

class RandomSearch:
    def __init__(self,settings_filename="settings.yaml",keepFiles_filename="keepFiles.csv"):
        self.CONFIG = None
        self.CONFIG = self.loadConfig(settings_filename)

        self.KEEP_FILES = None
        self.KEEP_FILES = self.loadKeepFiles(keepFiles_filename)
        self.setSearchSpaceParams()

        # BISTRO input files
        self.FREQ_FILE = "FrequencyAdjustment.csv"
        self.SUB_FILE = "ModeSubsidies.csv"
        self.FLEET_FILE = "VehicleFleetMix.csv"
        self.MASS_TRANSIT_FILE = "MassTransitFares.csv"

        self.inProj = Proj('epsg:3857')  # projection
        self.outProj = Proj('epsg:4326')  # lat/lon


    def loadConfig(self,settings_filename):
        # Load config
        config= {}
        with open(settings_filename) as stream:
            config = yaml.safe_load(stream)

        if not os.path.exists(config["RESULTS_PATH"]):
            os.makedirs(config["RESULTS_PATH"])
        
        return config

    def loadKeepFiles(self,keepFiles_filename):
        # headers: Folder	File	File type	Keep?	Analyze
        keepFiles = []
        csvfile = pd.read_csv(keepFiles_filename,header=None)[range(4)]
        csvfile[3].fillna(0,inplace=True)
        for i,row in csvfile.iterrows():
            if row[0]!='Folder':            
                if int(row[3])==1:
                    keepFiles.append(self.getPath(row[0],row[1],row[2]))
            
        return keepFiles

    def getPath(self, folder, f, filetype):
        # helper function for reconstructing keepFiles
        if folder =='root':
            return "{}.{}".format(f,filetype)
        elif folder =='ITERS':
            return "ITERS/it.{}/{}.{}.{}".format(self.CONFIG["LAST_ITERATION"]-1,self.CONFIG["LAST_ITERATION"]-1,f,filetype)
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
        # min_radius, max_radius: mininum & maximum radius; defines the search space for the radii of the cordons
        # fee_range: the [min, max] of the search space for the cordon fee
        # TODO: add fee type (per mile or cordon) default: per-mile
        # num_cordons: the number of cordons to include in the search space
        # TODO: check necessity of this param ^^
        if cordon_params is not None:
            if 'min_radius' in cordon_params.keys():
                self.setCordonSearchSpace(cordon_params['centroids'], cordon_params['radii'],cordon_params['min_radius'],cordon_params['max_radius'], fee_range=cordon_params['fee_range'],num_cordons = cordon_params['num_cordons'])
            else:
                self.setCordonSearchSpace(cordon_params['centroids'], cordon_params['radii'], fee_range= cordon_params['fee_range'],num_cordons = cordon_params['num_cordons'])
        else:
            self.setCordonSearchSpace(self.CONFIG['CORDON_CENTERS'],self.CONFIG['CORDON_RADII'])

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
        # sets the search spaces for all cordons either by input parameters or by using config parameters by default

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
        # sets the search spaces for all subsidies either by input parameters or by using config parameters by default

        self.MIN_INCOME_THRESH = []
        self.MAX_INCOME_THRESH = []
        self.SUBSIDY_MODES = []
        self.MIN_SUBSIDY=[]
        self.MAX_SUBSIDY=[]
        if income_thresholds is not None:
            count = 0
            for t in income_thresholds:
                self.MIN_INCOME_THRESH.append( t[0])
                self.MAX_INCOME_THRESH.append( t[1])
                count +=1
            self.INCOME_THRESH_INTERVAL = income_search_interval
            count = 0
            for m in modes:
                self.SUBSIDY_MODES.append( m)
                self.MIN_SUBSIDY.append( subsidy_ranges[count][0])
                self.MAX_SUBSIDY.append( subsidy_ranges[count][1])
                count+=1
            self.SUBSIDY_INTERVAL = subsidy_interval

        elif len(self.CONFIG['ICENTIVE_MODES'])>0 & self.CONFIG['NUM_LEVELS']>0:
            for l in range(self.CONFIG['NUM_LEVELS']):
                self.MIN_INCOME_THRESH.append(self.CONFIG["MIN_INCOME_THRESH"])
                self.MAX_INCOME_THRESH.append(self.CONFIG["MAX_INCOME_THRESH"])

            self.INCOME_THRESH_INTERVAL = self.CONFIG["INCOME_THRESH_INTERVAL"]
            # UPDATE SO CALLING EVERYTHING INCENTIES INSTEAD OF SUBSIDIES
            self.SUBSIDY_MODES = self.CONFIG['ICENTIVE_MODES']

            self.MIN_SUBSIDY.append(self.CONFIG["MIN_TNC_SUBSIDY"])
            self.MAX_SUBSIDY.append(self.CONFIG["MAX_TNC_SUBSIDY"])
            self.MIN_SUBSIDY.append(self.CONFIG["MIN_TRANSIT_SUBSIDY"])
            self.MAX_SUBSIDY.append(self.CONFIG["MAX_TRANSIT_SUBSIDY"])

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


def main():
    # args[0]: yaml random search config filename
    # args[1]: number of samples to generate
    # args[2]: (optional) which cordons to sample
    # args[3]: filename of the BEAM config with which to run BISTRO

    args = sys.argv[1:]
    
    search_object = RandomSearch(settings_filename=args[0])
    search_object.setSearchSpaceParams()

    num_samples = args[1]
    config_filename = args[3]

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

    # generate search spaces:
    x={}
    y={}
    for i in cordons:
        x[i], y[i] = search_object.uniform_points_from_circle(i, 50)  # change the density of fill of the circle

    income_thresh = []
    for i in range(len(search_object.MIN_INCOME_THRESH)):
        income_thresh.append(list(range(search_object.MIN_INCOME_THRESH[i],search_object.MAX_INCOME_THRESH[i],search_object.INCOME_THRESH_INTERVAL)))
    subsidies = []
    for i in range(len(search_object.SUBSIDY_MODES)):
        subsidies.append(list(range(search_object.MIN_SUBSIDY[i],search_object.MAX_SUBSIDY[i],search_object.SUBSIDY_INTERVAL)))


    input_root =  os.path.abspath(os.path.join(search_object.CONFIG["RESULTS_PATH"],"/random_search-input"))
    config_path = os.path.join("/fixed-data/sf_light/",config_filename)
    output_dir = os.path.abspath(f"{search_object.CONFIG['RESULTS_PATH']}")
    out_path = os.path.abspath("{}/{}cordons_{}_{}Subsidies/".format(output_dir,len(cordons),args[2],len(subsidies)))


    os.makedirs(input_root, exist_ok=True)
    os.makedirs(out_path, exist_ok=True)


    # File to save metadata of runs
    out_file = out_path+'/runLog.csv'

    # Write the headers to the file
    headers = ['sample_num','run_time','weightedSum','input_path','output_path','folderID']
    header_written = False

    params = {}
    print(search_object.MIN_PRICE_PER_MILE, search_object.MAX_PRICE_PER_MILE)
    for n in range(int(num_samples)):
        start_time = datetime.now()
        for i in cordons:
            params['centerx' + str(i)] = round_nearest(np.random.choice(x[i]), 0.005)
            params['centery' + str(i)] = round_nearest(np.random.choice(y[i]), 0.005)
            params['cradius' + str(i)] = round_nearest(np.random.uniform(search_object.MIN_RADIUS, search_object.MAX_RADIUS),500)
            params['ctoll' + str(i)] = round_nearest(np.random.uniform(search_object.MIN_PRICE_PER_MILE, search_object.MAX_PRICE_PER_MILE),0.25)
        for i in range(len(income_thresh)):
            if i == 0:
                params['incomeThresh'+str(i)] = np.random.choice(income_thresh[i])
            else:
                params['incomeThresh'+str(i)] = np.random.choice(income_thresh[i][np.where(income_thresh[i]>params['incomeThresh'+str(i-1)])[0][0]:])
            for j in range(len(subsidies)):
                params['subsidyModes'+str(j)] = search_object.SUBSIDY_MODES[j]
                if i==0:
                    params['subsidyVal_mode{}_level{}'.format(j,i)] = np.random.choice(subsidies[j])
                else:
                    params['subsidyVal_mode{}_level{}'.format(j, i)] = np.random.choice(subsidies[j][0:np.where(subsidies[j]<=params['subsidyVal_mode{}_level{}'.format(j,i-1)])[0][-1]+1])
        # run simulation with input (calls convert_to_input):
        result = run_BISTRO(params,search_object.CONFIG["NETWORK_PATH"], search_object.KEEP_FILES, config_path, out_path)

        if header_written==False:
            for k,p in params.items():
                headers.append(k)
            for k,v in result['kpi_scores'].items():
                if k!='Iteration':
                    headers.append(k)
            for k,v in result['mode_choices'].items():
                if k!='Iteration':
                    headers.append(k)

            with open(out_file, 'w') as of_connection:
                writer = csv.writer(of_connection)
                writer.writerow(headers)

            header_written=True
        # record output:
        process_results(result,headers,out_file,n)
        end_time = datetime.now()
        print("{} ({}): Sample {} complete".format(end_time,end_time-start_time,n))

    
def process_results(result_dict,headers,out_file,n):
    this_row ={}
    this_row['sample_num']=n
    p=0
    for h in headers[1:]:
        if h in list(result_dict['params'].keys()):
            this_row[h] = result_dict['params'][h]
        elif h in list(result_dict['kpi_scores'].keys()):
            this_row[h] = result_dict['kpi_scores'][h]
        elif h in list(result_dict['mode_choices'].keys()):
            this_row[h] = result_dict['mode_choices'][h]
        elif h in ['input_path','output_path']:
            this_row[h] = result_dict['paths'][p]
            p+=1
        else:
            if h in result_dict.keys():
                this_row[h] = result_dict[h]

    with open(out_file, 'a') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writerow(this_row)


def round_nearest(x, a):
    return round(x / a) * a


if __name__ == "__main__":

    main()