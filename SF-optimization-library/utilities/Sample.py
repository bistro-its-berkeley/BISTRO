#Defines a Sample class that stores all relevant information about a sample
import os

from navigate_data import *
from collect_inputs import *
from collect_outputs import *
from math import *

class Sample:

	directory = None; #Top level directory of the sample point
	timeStamp = None;
	n_iters = None; #Number of iterations of a sample

	#Inputs
	mass_transit_fares = {"AdultFare":None, "ChildrenFare":None};
	road_pricing = {"x":None, "y":None, "p":None, "r":None};

	#Outputs
	KPIS = None; #dict of {KPI: (it0, it1, ..., it.n)}
	mode_split = None;	

	def __str__(self):
		return "Sample at directory: " + self.directory + ", at timeStamp: " + str(self.timeStamp)


def init_sample(tpe_dir):
	s = Sample()
	s.directory = tpe_dir
	s.timeStamp = round(read_timestamp(tpe_dir))

	s.mass_transit_fares = getTransitFareInputs(tpe_dir)
	s.mode_split = getModeSplit(tpe_dir)
	#s.road_pricing = reconstructRoadPrincingArea(tpe_dir)
	s.road_pricing = collect_circle_fares_parameters(tpe_dir)

	s.KPIS = retrieve_KPIs(tpe_dir) #Those are RAW KPIS, getting the actual KPIs
	#requires to standardize them

	return s

#Returns a list score stored by iteration number
def computeWeightedScores(s, standards, weights, standarding = True):
	kpis_dict = s.KPIS
	scores = []
	iters = kpis_dict['Iteration']
	for i in iters:
		s = 0
		nb_params = 0
		for k in weights:
			nb_params+=1
			w = weights[k]
			mean, std = standards[k]
			value = kpis_dict[k][i]
			s += w*(value - mean)/std
		scores.append(s/sum([abs(w) for w in weights.values()]))

	return scores	


#Returns a list of samples ordered by timeStamp
def create_samples_list(exp_directory, dirs = None):
	if dirs == None:
		dirs = getTimeSortedDirs(exp_directory)
	print("Found " + str(len(dirs)) + " samples")

	samples = []
	i = 0

	for d in dirs:
		i += 1
		print("Loading sample " + str(i) + "...", end="\r")
		s = init_sample(d)
		if s.road_pricing["p"] != 0.0:
			samples.append(s)
		else:
			print(s.directory)

	print("\n")
	return samples