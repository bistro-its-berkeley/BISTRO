import os
import sys
import csv
import matplotlib.pyplot as plt
import pandas as pd
from mpl_toolkits.mplot3d import Axes3D
import random
from scipy.interpolate import griddata
import numpy as np

#### The next few functions help navigate data points directories

#Get the current working directory
def get_dir():
	return os.getcwd()

#Get only subdir of a directory
def only_subdir(current_dir = os.getcwd()):
	return next(os.walk(current_dir))[1][0]

#Get a list of all subdirectories
def sub_list(current_dir = os.getcwd()):
	dirs = next(os.walk(current_dir))[1]
	dirs = [os.path.join(current_dir, d) for d in dirs if d[0]=='5']
	dirs = [d for d in dirs if  check_file_existence(d)]
	return dirs


#Read the timestamp of a data point
def read_timestamp(tpe_dir):
	results_dir = get_results_dir(tpe_dir)
	outfile = os.path.join(results_dir, "submissionScores.csv")
	timestamp = os.path.getmtime(outfile)
	return timestamp

#Check data existence and input validity
def check_file_existence(tpe_dir):
	outputs =  os.path.exists(os.path.join(get_results_dir(tpe_dir), "rawScores.csv"))
	outputs = outputs and os.path.exists(os.path.join(get_results_dir(tpe_dir), "submissionScores.csv"))
	inputs = os.path.exists(os.path.join(getInputsDir(tpe_dir), "MassTransitFares.csv"))
	circle_params = os.path.exists(os.path.join(tpe_dir, 'circle_params.txt'))
	return inputs and outputs and circle_params

#Return a list of data points sorted by time
def getTimeSortedDirs(exp_directory):
	dirs = sub_list(exp_directory)
	dirs = sorted(dirs, key = lambda x:read_timestamp(x))
	print("Number of complete result directories : "+str(len(dirs)))
	return dirs

#Get the path of the result file given a TPE folder
def get_results_dir(dir):
	abs_path = os.path.join(get_dir(), dir)
	abs_path = os.path.join(abs_path, 'output')
	abs_path = os.path.join(abs_path, only_subdir(abs_path))
	abs_path = os.path.join(abs_path, only_subdir(abs_path))
	abs_path = os.path.join(abs_path, only_subdir(abs_path))
	abs_path = os.path.join(abs_path, 'competition')
	return abs_path

def getInputsDir(tpe_dir):
	abs_path = os.path.join(get_dir(), tpe_dir)
	abs_path = os.path.join(abs_path, 'submission-inputs')
	abs_path = os.path.join(abs_path, only_subdir(abs_path))
	return abs_path



