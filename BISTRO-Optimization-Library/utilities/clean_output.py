import sys
import os
from os import listdir
from os.path import isfile, join
import shutil


def clean_output(path):
    """
    Open xml and xml.gz files into ElementTree

    Parameters
    ----------
    path: string
        Absolute path of the output folder to clean
    """
    # Make sure that the path is a string (and not a pathlib.Path object)
    path = str(path)

    # Set folder paths
    iters_folder = path + "/ITERS"
    competition_folder = path + "/competition"
    summary_folder = path + "/summaryStats"

    # Remove excess root folder files
    file_list = [f for f in listdir(path) if isfile(join(path, f))]
    keep_files = ["outputEvents.xml.gz", "realizedModeChoice.csv", "summaryStats.csv"]
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
    for folder in iter_list:
        folder_path = iters_folder + "/" + folder
        if os.path.exists(folder_path + "/tripHistogram"):
            shutil.rmtree(folder_path + "/tripHistogram")
        file_list = [f for f in listdir(folder_path) if isfile(join(folder_path, f))]
        for file in file_list:
            if file.endswith('events.xml.gz') == False:
                os.remove(folder_path + "/" + file)