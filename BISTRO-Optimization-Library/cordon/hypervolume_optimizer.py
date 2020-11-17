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

from convert_to_input_cordon import *
from optimization_kpi import optim_KPI
from optimizer_cordon import *

import uuid
from timeit import default_timer as timer
import untangle
import xmltodict
import gzip
import yaml
import pandas as pd
import csv

from hyperopt import STATUS_OK
from pygmo import hypervolume

#Load config
CONFIG = {}
with open(os.path.join(hyperopt_path,"settings.yaml")) as stream:
    CONFIG = yaml.safe_load(stream)

sys.path.append(CONFIG["BEAM_PATH"])

logger = logging.getLogger(__name__)

# pre-existing results path - BEAM has already generated this data
RESULTS_PATH = "/Users/makenaschwinn/Desktop/bistro/AWS_samples/"

SCENARIO_NAME = "sioux_faux"

SCORING_WEIGHTS_RAW_PATH = BEAM_PATH + "BISTRO-Optimization-Library/fixed_data/scoringWeights.csv" 
BAU_STATS_PATH = CONFIG["BEAM_PATH"] + "BISTRO-Optimization-Library/fixed_data/" + SCENARIO_NAME + "/bau/stats/summaryStats-" + CONFIG["SAMPLE_SIZE"] +".csv"
OBJECTIVE_VAL_FILENAME = "objective_value.csv"

def hypervolume_score(raw_scores, standards, output_dir):
	# make reference point
	ref = make_reference_point(output_dir)

	if "Iteration" in raw_scores:
		removed_value = raw_scores.pop("Iteration")
		print("Removed 'Iteration' key from raw_scores")
		# handle keyError on Iteration (not in standards file), don't want to use Iteration in hypervolume computation

	# standardize raw scores,
	for k in raw_scores.keys():
		# raw_scores[k] = (raw_scores[k] - standards[k][0]) / standards[k][1]
		print(k)
		raw_scores[k] = (raw_scores[k] - standards.get(k, (0,1))[0]) / standards.get(k, (0,1))[1]

	print(raw_scores)

	# get pareto front
	# prev_pareto = get_pareto()

	# compute pareto front
	curr_pareto, ordered_kpi_names = pareto_front(raw_scores)

	# calculate hv score with pygmo utility
	hv = hypervolume(curr_pareto)
	score = -1 * hv.compute(ref)
	print(score)

	# update best-seen KPI values
	update_best_kpis()

	return score

def make_reference_point(output_dir):
	# TODO
	# implement a more sophisticated reference point

	bau_score_dic = get_raw_bau_scores(output_dir)
	kpi_colnames = sorted(list(bau_score_dic.keys()))

	ref = {}
	for key, val in bau_score_dic.items():
		ref[key] = bau_score_dic[key] * 5
	ref_arr = np.array([ref[kpi] for kpi in kpi_colnames]) # ordered
	print(f"ref: {ref_arr}")
	# logger.info(f"ref: {ref_arr}")
	return ref_arr 

def get_raw_bau_scores(output_dir, bau_output_dir=BAU_STATS_PATH, scoring_std_path=SCORING_WEIGHTS_RAW_PATH):
    # raw scores = std * score /BAU_score 
    # thus
    # raw bau score = std 
    # TODO: explore tollRevenue, VMT
    
    raw_scores = read_raw_scores(output_dir) # TODO: temp
    # want to make sure we're using the same keys as raw_scores, don't actually need to read the whole file
    raw_scores.pop("Iteration") # remove "Iteration" key

    weights_df = pd.read_csv(scoring_std_path, index_col=0)
    weights_dic = weights_df.to_dict(orient='list') # each key (kpi name) maps to one-element list (weight value, 1 in current file)

    bau_dic = {}
    for key in raw_scores.keys():
        bau_dic[key] = weights_dic.get(key, [1.0])[0]
        # bau_dic: {'driveSecondaryAccessibility': 1.0, ...}

    print(f"bau_dic: {bau_dic}")
    # logger.info(f"bau_dic: {bau_dic}")
    return bau_dic

def dominates(row, candidateRow):
    # returns true if candidateRow dominates row
    # modified from http://code.activestate.com/recipes/578287-multidimensional-pareto-front/
    # candidateRow dominates row if candidate_kpi_x <= row_kpi_x for all kpis x and at least one ineq is strict
    return (sum([row[x] >= candidateRow[x] for x in range(len(row))]) == len(row)) and (sum([row[x] > candidateRow[x] for x in range(len(row))]) >= 1)

def pareto_front(raw_scores, samples_dir=RESULTS_PATH):
    logger.info("pareto_front")
    print("pareto_front")
    csvfile = f"{samples_dir}/pareto_front.csv"
    # kpi_colnames = sorted(list(BAU_MAPPING.keys()))
    kpi_colnames = sorted(list(raw_scores.keys()))
    current_iter_kpis = np.array([raw_scores[kpi] for kpi in kpi_colnames]) # ordered

    if not os.path.exists(csvfile):
        # f = open(csvfile, 'w') # creates file if it doesn't exist (we are at first iteration)
        print(f"make file: {csvfile}")
        logger.info(f"kpi_colnames: {kpi_colnames}")
        logger.info(f"current_iter_kpis: {current_iter_kpis}")
        df = pd.DataFrame(data=np.array([current_iter_kpis]), columns=kpi_colnames)
        df.to_csv(csvfile)
        return np.array([current_iter_kpis]), kpi_colnames
    else:
        pareto_df = pd.read_csv(csvfile, index_col=0)
        pareto_2d_arr = pareto_df.to_numpy()
        logger.info(f"pareto_2d_arr from csvfile: {pareto_2d_arr}")
        print(isinstance(pareto_2d_arr[0], np.ndarray))
        logger.info(isinstance(pareto_2d_arr[0], np.ndarray))
        dominated_2d_arr = np.array([])
        # candidateRow = np.array(list(raw_scores.values())) # ORDER MATTERS - TODO
        candidateRow = current_iter_kpis
        rowNr = 0
        nonDominated = True
        while len(pareto_2d_arr) != 0 and rowNr < len(pareto_2d_arr) and nonDominated:
            row = pareto_2d_arr[rowNr]
            if dominates(candidateRow, row): # true if row dominates candidateRow
                nonDominated = False
                rowNr += 1
            elif dominates(row, candidateRow):
            	# If existing row is worse on all features remove the row from the pareto front array
                pareto_2d_arr = np.delete(pareto_2d_arr, rowNr, axis=0)
            else:
                rowNr += 1
        if nonDominated:
            # add the non-dominated point to the Pareto frontier
            pareto_2d_arr = np.append(pareto_2d_arr, np.array([candidateRow]), axis=0)
        # rewrite pareto file
        logger.info(f"pareto_front pareto_2d_arr: {pareto_2d_arr}")
        print(f"pareto_front pareto_2d_arr: {pareto_2d_arr}")
        if not isinstance(pareto_2d_arr[0], np.ndarray):
            logger.info(f"pareto_2d_arr is 1d")
            print(f"pareto_2d_arr is 1d")
            pareto_2d_arr = np.array([pareto_2d_arr])
        logger.info(f"pareto_2d_arr for df: {pareto_2d_arr}")
        pareto_df = pd.DataFrame(data=pareto_2d_arr, columns=kpi_colnames)
        pareto_df.to_csv(csvfile)
        return pareto_2d_arr, kpi_colnames
