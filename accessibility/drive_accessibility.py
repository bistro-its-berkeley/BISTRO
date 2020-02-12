import gzip
import ntpath
import re
from collections import defaultdict

import numpy as np
import pandana as pdna
import pandas as pd
import utm
from lxml import etree as ET


def open_xml(path):
	# Open xml and xml.gz files into ElementTree
	if path.endswith('.gz'):
		return ET.parse(gzip.open(path))
	else:
		return ET.parse(path)


def csv_from_dict(d):
	header = ",".join([str(x) for x in d.keys()])
	return header + "\n" + ",".join([str(x) for x in d.values()])


class DriveAccessibilityAnalysis:

	def __init__(self,
				 network_file,
				 linkstats_file,
				 population_file,
				 noOfIters,
				 utm_zone):
		self.network_file = network_file
		self.linkstats_file = linkstats_file
		self.population_file = population_file
		self.noOfIters = noOfIters
		self.utm_zone_number = int(re.findall("(\d+)", utm_zone)[0])
		self.utm_zone_letter = re.findall("([N|S])", utm_zone)[0]
		self.poi_dict = self._make_poi_dict()

	def _convert_crs(self, c):
		return utm.to_latlon(c[0], c[1],
							 self.utm_zone_number,
							 self.utm_zone_letter)

	@staticmethod
	def _create_pandana_net(nodes, edges):
		return pdna.Network(nodes.x, nodes.y, edges['from'], edges['to'],
							edges.xs('traveltime', axis=1, level=1))

	def _make_net_for_timeranges(self, timeranges):
		traveltime_df = self._make_traveltime_df(timeranges)
		node_df = self._make_node_df()
		return self._create_pandana_net(node_df, traveltime_df)

	def make_pandana_net(self, poi_types, timeranges, max_time):
		"""
		Make Pandana networks for each poi type over each specified time range using max_time
		as the maximum search distance.

		poi_types : list(str)
			The opportunities of interest upon which to run accessibility analysis
		timeranges : dict[string,iterable[int]]
			The time ranges over which analysis will be performed
		max_time : int
			The maximum search "distance", which is a parameter for Pandana
		return : list(pdna.Network)

		"""

		net = self._make_net_for_timeranges(timeranges)
		for poi_type in poi_types:
			net.precompute(max_time)
			poi_locs = np.array(self.poi_dict[poi_type])
			x, y = poi_locs[:, 1], poi_locs[:, 0]
			net.set_pois(poi_type, max_time, 100, x, y)
			poi_nodes = net.get_node_ids(x, y)
			net.set(poi_nodes, name=poi_type)
		return net

	def _make_node_df(self):
		matsimnet = open_xml(self.network_file).getroot()
		nodes = matsimnet[1]
		node_data = []

		# populate node dataframes
		for node in nodes:
			coords = self._convert_crs((float(node.get('x')), float(node.get('y'))))
			node_data.append([int(node.get('id')), coords[1], coords[0]])
		node_data = np.array(node_data)

		node_df = pd.DataFrame({'x': node_data[:, 1], 'y': node_data[:, 2]}, index=node_data[:, 0].astype(int))
		node_df.index.name = 'id'
		return node_df

	def _make_traveltime_df(self, timeranges):
		"""
		Preprocess the linkstats.csv file.

		Remove extraneous rows and select only the relevant timerange

		timerange : Iterable[int]
			The time range over which analysis will be conducted. Should be a Python range(low,high) object.

		return : pd.DataFrame
			A preprocessed DataFrame containing the link travel times during the target time range at intervals
			specific to the originating BEAM simulation run.
		"""
		link_df = self._make_avg_traveltime_src_df()

		traveltime_link_df = pd.concat([link_df[link_df.hour.map(lambda x: x in timerange)].groupby('link').mean()[
											['from', 'to', 'traveltime']].set_index(['from', 'to'])
										for timerange in timeranges.values()], keys=timeranges.keys(),
									   names=['timerange', 'from'], axis=1).reset_index()

		return traveltime_link_df

	def _make_avg_traveltime_src_df(self):
		path_head, path_tail = ntpath.split(self.linkstats_file)

		last_iter = int(re.search(r'\d+', path_tail).group())

		selected_iters = []
		iters_dfs = []


		for i in range(last_iter, last_iter - self.noOfIters, -1):
			try:
				stats_file = '/'.join([path_head, path_tail]).replace(str(last_iter), str(i), 2)

				link_df = pd.read_csv(stats_file, compression='gzip')
				link_df = link_df[link_df.stat == 'AVG']
				#link_df.drop(link_df.hour[link_df.hour == '0.0 - 30.0'].index, inplace=True)
				selected_iters.append(i)
				iters_dfs.append(link_df)
			except:
				print(stats_file)
				print("path not found")

		all_df = pd.concat(iters_dfs, keys=selected_iters)
		all_df = all_df.groupby(['link', 'hour']).mean().reset_index()
		all_df.hour = all_df.hour.astype(float).astype(int)
		return all_df

	def _make_poi_dict(self):
		population_xml = open_xml(self.population_file).getroot()
		persons = population_xml.findall('person')
		poi_dict = defaultdict(list)
		for person in persons:
			for activity in person[1]:
				act_type = activity.get('type')
				if act_type != None:
					if act_type == "Eatout" or act_type == "Escort" or act_type == "Other" or act_type == "School" or act_type == "Shopping" or act_type == "Social":
						act_type = "Secondary"
					elif act_type == "Work" or act_type == "University":
						act_type = "Commute"
					act_type = act_type.lower()
					coords = self._convert_crs([float(activity.get('x')), float(activity.get('y'))])
					poi_dict[act_type].append(coords)
		return poi_dict
