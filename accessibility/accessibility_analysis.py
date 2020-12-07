#! /usr/bin/env python3
"""
Computes time-based measures of access to important locations based on link travel times
provided as output of a BEAM simulation. The link travel times are (preferably) the result of executing
AgentSim events on the PhysSim network (see BEAM documentation for specifics). We use Pandanas to
efficiently aggregate over the network. This script will be run from the host docker container with embedded Python 3
that has been packaged with the numerous (and onerous to build) dependencies for Pandana (see Notes below for further
details).

Notes:
------
	Build and execution: Run the DockerFile in parent directory to build the image containing
	this script and push to DockerHub (this may take a while if a cache has not yet been generated on the host
	machine). The gradle `dockerBuildImage` command can then be used to complete the full build for
	BeamCompetitions.

"""
from datetime import time
from pathlib import Path
import csv

from drive_accessibility import *
from transit_accessibility import TransitAccessibilityAnalysis, DATA_ROOT

# Constants defining accessibility analysis dimensions

POI_TYPES = ['commute', 'secondary']
#POI_TYPES= ['work']

TIME_RANGES = {'morning_peak': (7, 10), "midday": (10, 17)}

MAX_TIME = 900  # 15 minutes in seconds... specifies search distance for Pandana

# Other Constants
TIME_FORMAT = '%H:%M:%S'
a_net = dict()


def analyze_accessibility_for_mode(current_mode, daa, taas, drive_net, aggs):
	aggs[current_mode] = {}

	for poi_name in POI_TYPES:
		if poi_name not in POI_TYPES:
			continue

		total_poi_avg = []
		for timerange_name in TIME_RANGES:
			if poi_name == 'commute' and timerange_name != 'morning_peak':
				continue
			if current_mode == 'drive':
				a = drive_net.aggregate(MAX_TIME, type="sum", decay="linear", name=poi_name, imp_name=timerange_name)
				total_poi_avg += [a.mean()]
			else:
				for file,cur_urbanaccess_net in taas[timerange_name].ua_net:
					transit_net = pdna.Network(cur_urbanaccess_net.net_nodes["x"],
											   cur_urbanaccess_net.net_nodes["y"],
											   cur_urbanaccess_net.net_edges["from_int"],
											   cur_urbanaccess_net.net_edges["to_int"],
											   cur_urbanaccess_net.net_edges[["weight"]],
											   twoway=False)
					node_coords = np.array(daa.poi_dict[poi_name])
					node_ids = transit_net.get_node_ids(node_coords[:, 1], node_coords[:, 0])
					transit_net.set(node_ids, name=poi_name)
					a = transit_net.aggregate(int(MAX_TIME / 60), type="sum", decay="linear", name=poi_name)
					a_net[file] = a
					total_poi_avg += [a.mean()]
		aggs[current_mode][poi_name] = np.mean(total_poi_avg)
	return aggs


if __name__ == '__main__':

	import sys

	network_file = "output/tmp-data/physsim-network.xml"
	population_file = "output/tmp-data/population.xml" if Path(
		"output/tmp-data/population.xml").exists() else "fixed-data/sf_light/sample/population2.xml"
	frequency_file = "submission-inputs/FrequencyAdjustment.csv"
	#bbox = (-96.840732, 43.465438, -96.651134, 43.616366)
	bbox = (-122.544380,37.616035,-122.251793,37.87404)
	#utm_zone = "14N"  # Sioux Faux utm zone
	utm_zone = "10S"

	linkstats_file = f"{sys.argv[1]}"  # link-by-link travel times; primary output of the BEAM PhysSim

	prefix = "bau" if "bau" in linkstats_file else "sub"

	if prefix == "bau" and Path('output/tmp-data/bau_accessibility_output.csv').exists():
		exit(1)

	noOfIters = int(sys.argv[2])

	r5_subpath = sys.argv[3]

	aggs = {}

	daa = DriveAccessibilityAnalysis(network_file, linkstats_file, population_file, noOfIters, utm_zone)
	drive_net = daa.make_pandana_net(POI_TYPES, TIME_RANGES, MAX_TIME)

	taas = {}
	transit_data = None
	if noOfIters < 2:  # Transit access only needs to be computed once
		mode_types = ['drive', 'transit']
		for time_label, time_range in TIME_RANGES.items():
			hrs_0 = time(time_range[0], 0, 0).strftime(TIME_FORMAT)
			hrs_1 = time(time_range[1], 0, 0).strftime(TIME_FORMAT)
			time_range_spec = [time_label, [hrs_0, hrs_1]]
			taas[time_label] = TransitAccessibilityAnalysis(prefix, bbox, time_range_spec, verbose=False,
															r5_subpath=r5_subpath)
	else:
		mode_types = ['drive']
		transit_data = pd.read_csv('output/tmp-data/sub_accessibility_output.csv', index_col=0)

	for mode in mode_types:
		aggs = analyze_accessibility_for_mode(mode, daa, taas, drive_net, aggs)
		if transit_data is not None:
			aggs['transit'] = transit_data['transit']

	pd.DataFrame(aggs).to_csv(str(DATA_ROOT.parent / f"output/tmp-data/{prefix}_accessibility_output.csv"))

	# keep record for debug purposes:
	if prefix == 'sub' and Path('output/tmp-data/bau_accessibility_output.csv').exists():
		current_iter = int(Path(linkstats_file).name.split('.')[0])
		sub_iter_file = pd.read_csv("output/tmp-data/sub_accessibility_output.csv", index_col=0)
		bau_iter_file = pd.read_csv("output/tmp-data/bau_accessibility_output.csv", index_col=0)
		data_set = pd.concat([sub_iter_file, bau_iter_file], axis=1, keys=['bau', 'sub']).T.reset_index()
		data_set['iteration'] = current_iter
		data_set.rename(columns={'level_0': 'bau_or_sub', 'level_1': 'mode'}, inplace=True)
		data_set = data_set.melt(id_vars=['bau_or_sub', 'mode', 'iteration'], value_vars=['secondary','commute'],
								 var_name='poi_type', value_name='accessibility')
		iteration_data_path = Path('output/tmp-data/iteration_data.csv')
		if iteration_data_path.exists():
			existing_data = pd.read_csv('output/tmp-data/iteration_data.csv', index_col=0)
			data_set = pd.concat([existing_data, data_set])
		data_set.to_csv('output/tmp-data/iteration_data.csv')

	with open('output/tmp-data/aggregate.csv', 'w') as f:
	    for key in a_net.keys():
	        f.write("%s,%s\n"%(key,a_net[key]))
