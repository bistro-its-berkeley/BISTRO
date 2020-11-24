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
# from optimizer_cordon import * # didn't work - read_raw_scores is not defined" - circular dependency

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

logger = logging.getLogger(__name__)

SCENARIO_NAME = "sioux_faux"

SCORING_WEIGHTS_RAW_PATH = CONFIG["BEAM_PATH"] + "BISTRO-Optimization-Library/fixed_data/scoringWeights.csv" 
BAU_STATS_PATH = CONFIG["BEAM_PATH"] + "BISTRO-Optimization-Library/fixed_data/" + SCENARIO_NAME + "/bau/stats/summaryStats-" + CONFIG["SAMPLE_SIZE"] +".csv"
OBJECTIVE_VAL_FILENAME = "objective_value.csv"

def hypervolume_score(raw_scores, standards, output_dir, samples_dir, curr_bistro_iter):
	# make reference point
	ref = make_reference_point(output_dir)

	if "Iteration" in raw_scores:
		removed_value = raw_scores.pop("Iteration")
		print("Removed 'Iteration' key from raw_scores")
		# handle keyError on Iteration (not in standards file), don't want to use Iteration in hypervolume computation

	# standardize raw scores,
	for k in raw_scores.keys():
		# raw_scores[k] = (raw_scores[k] - standards[k][0]) / standards[k][1]
		if ("Accessibility" in k) or (k == "costBenefitAnalysis"):
			raw_scores[k] = -1 * raw_scores[k]
		print(k)
		raw_scores[k] = (raw_scores[k] - standards.get(k, (0,1))[0]) / standards.get(k, (0,1))[1]

	# get pareto front
	# prev_pareto = get_pareto()

	# compute pareto front
	curr_pareto, ordered_kpi_names = pareto_front(raw_scores, curr_bistro_iter, samples_dir)

	# write pareto front
	# record_pareto()

	# calculate hv score with pygmo utility
	hv = hypervolume(curr_pareto)
	score = -1 * hv.compute(ref)
	print(score)
	write_hv_score(score, curr_bistro_iter, samples_dir)

	# update best-seen KPI values
	update_best_kpis(curr_pareto, ordered_kpi_names, curr_bistro_iter, output_dir, samples_dir)

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
    logger.info(f"bau_dic: {bau_dic}")
    return bau_dic

def dominates(row, candidateRow):
    # returns true if candidateRow dominates row
    # modified from http://code.activestate.com/recipes/578287-multidimensional-pareto-front/
    # candidateRow dominates row if candidate_kpi_x <= row_kpi_x for all kpis x and at least one ineq is strict
    return (sum([row[x] >= candidateRow[x] for x in range(len(row))]) == len(row)) and (sum([row[x] > candidateRow[x] for x in range(len(row))]) >= 1)

def pareto_front(raw_scores, curr_bistro_iter, samples_dir):
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
        cols = ["BISTRO Iteration"] + kpi_colnames
        data = [1] + list(current_iter_kpis) # first column to track pareto front at each iteration
        with open(csvfile, "w") as f:
        	csvwriter = csv.writer(f)
        	csvwriter.writerow(cols)
        	csvwriter.writerow(data)
        	f.close()
        # df = pd.DataFrame(data=np.array([data]), columns=cols)
        # df.to_csv(csvfile)
        return np.array([current_iter_kpis]), kpi_colnames
    else:
        pareto_df = pd.read_csv(csvfile).drop("BISTRO Iteration", axis=1) # don't use BISTRO Iteration column in pareto calc
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

        # open file for appending/reading
        # switch from "a+" to "w" if filesize with appending is becoming too large - this will overwrite previous iterations' pareto fronts
        # and remove column writer line
        with open(csvfile, 'w') as f: 
        	csvwriter = csv.writer(f)
        	cols = ["BISTRO Iteration"] + kpi_colnames
        	csvwriter.writerow(cols)
	        for row in pareto_2d_arr:
	        	# write data with current iteration as first column
	        	csvwriter.writerow([curr_bistro_iter] + list(row))
	        f.close()
        # pareto_df = pd.DataFrame(data=pareto_2d_arr, columns=kpi_colnames)
        # pareto_df.to_csv(csvfile)
        return pareto_2d_arr, kpi_colnames

def write_hv_score(score, iteration, samples_dir, filename=OBJECTIVE_VAL_FILENAME):
    csvfile  = f"{samples_dir}/{OBJECTIVE_VAL_FILENAME}"
    with open(csvfile, 'a') as obj_csvfile:
        csvwriter = csv.writer(obj_csvfile)
        csvwriter.writerow([iteration, score]) 

def update_best_kpis(pareto_2d_arr, kpi_colnames, bistro_iter, output_dir, samples_dir, filename=None):
    """
    Update the last row of best_achieved_kpis.csv
    Return the current BISTRO iteration #
    """
    csvfile  = f"{samples_dir}/best_achieved_KPIS.csv"
    logger.info(f"curr_bistro_iter: {bistro_iter}")

    if not os.path.exists(csvfile):
    	logger.info(f"Creating best_achieved_kpis file in {samples_dir}")
    	bau_dic = get_raw_bau_scores(output_dir) # kpi:value
    	kpi_colnames = sorted(list(bau_dic.keys()))
    	bau_kpis_values = np.array([bau_dic[kpi] for kpi in kpi_colnames]) # ordered

    	kpi_colnames = ["BISTRO Iteration"] + kpi_colnames
    	bau_kpis_values = [1] + list(bau_kpis_values)

    	logger.info(f"kpi_colnames: {kpi_colnames}")
    	logger.info(f"bau_kpis_values: {bau_kpis_values}")

    	with open(csvfile, 'a') as best_kpis_csv:
    		csvwriter = csv.writer(best_kpis_csv)
    		csvwriter.writerow(kpi_colnames)
    		csvwriter.writerow(bau_kpis_values) 
    		best_kpis_csv.close()
    else:
    	best_kpis_df = pd.read_csv(csvfile)
    	pareto_df = pd.DataFrame(data=pareto_2d_arr, columns=kpi_colnames) # already ordered
    	min_values = [pareto_df[colname].min() for colname in pareto_df.columns]
    	logger.info(f"min_values: {min_values}")

    	curr_data = [bistro_iter] + min_values # create row of df: BISTRO ITERATION, KPI1, KPI2, ...

    	with open(csvfile, 'a') as best_kpis_csv:
    		csvwriter = csv.writer(best_kpis_csv)
    		csvwriter.writerow(curr_data) 
    		best_kpis_csv.close()

def read_raw_scores(output_dir):
    path = only_subdir(only_subdir(output_dir))


    #Copy outevents
    if not os.path.isfile(os.path.join(path, "outputEvents.xml.gz")):
        shutil.copy(os.path.join(path, "ITERS/it.30/30.events.xml.gz"), os.path.join(path, "outputEvents.xml.gz"))


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
