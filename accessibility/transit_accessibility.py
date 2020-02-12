import os.path as osp
import tempfile
from pathlib import Path
from zipfile import ZipFile
import os

import pandas as pd
import urbanaccess as ua
from urbanaccess.gtfs.gtfsfeeds_dataframe import gtfsfeeds_dfs

TIME_RANGES = {'morning_peak': (7, 10), "midday": (10, 17)}
TIME_FORMAT = '%H:%M:%S'
DATA_ROOT = Path("tmp-data/")
SUB_GTFS_PATH = DATA_ROOT / "gtfs"


def run_path_data(r5_subpath=None):
	return {"bau": {"gtfs_path": Path("fixed-data/sf_light/r5", r5_subpath).resolve(),
									"net_path": DATA_ROOT / "bau_transit_net.h5"},
					"sub": {"gtfs_path": SUB_GTFS_PATH,
									"net_path": DATA_ROOT / "sub_transit_net.h5"}}


class TransitAccessibilityAnalysis:
	def __init__(self, run_type, bbox, timerange_spec, verbose=False, r5_subpath=None):
		self.run_type = run_type
		self.bbox = bbox
		self.timerange = timerange_spec[1]
		self.timerange_label = timerange_spec[0]
		self.verbose = verbose
		self.validation = True
		self.run_path_data = run_path_data(r5_subpath)[run_type]
		self.loaded_feeds = self._load_gtfs()
		self.ua_net = self._load_or_create_net()

	def _load_gtfs_from_zip(self, gtfs_zip_path):
		"""Loads disk-backed gtfs data for urbanaccess 
		as zipfile into memory by first unzipping to a temporary directory. 

		Directory is deleted upon return of data.
		"""
		with ZipFile(gtfs_zip_path) as z:
				with tempfile.TemporaryDirectory() as tmpdir:
						for file in z.namelist():
								if file.endswith(".txt"):
										with open(osp.join(tmpdir, file), 'wb') as f:
												f.write(z.read(file))
												f.close()
						return ua.gtfs.load.gtfsfeed_to_df(gtfsfeed_path=tmpdir,
																							 validation=True,
																							 verbose=self.verbose,
																							 bbox=self.bbox,
																							 remove_stops_outsidebbox=True,
																							 append_definitions=True)

	def _load_gtfs(self):
		loaded_feeds = []
		for file in os.listdir(str(self.run_path_data['gtfs_path'].absolute())):
				if file.endswith(".zip"):
						loaded_feeds.append((file,self._load_gtfs_from_zip(os.path.join(str(self.run_path_data['gtfs_path'].absolute()), file))))
		return loaded_feeds

	def _load_or_create_net(self):
		result = []

		for file,loaded_feed in self.loaded_feeds:
				ua.gtfs.network.create_transit_net(gtfsfeeds_dfs=loaded_feed,
																					 day='wednesday',
																					 timerange=self.timerange,
																					 calendar_dates_lookup=None)
				urbanaccess_net = ua.ua_network

				final_net_path = str(self.run_path_data['net_path'] / self.timerange_label)
				# if not osp.exists(final_net_path):
				osm_walk_path = (DATA_ROOT / f"{self.run_type}_osm_walk_data")
				nodes_path = (osm_walk_path / "nodes.csv")
				edges_path = (osm_walk_path / "edges.csv")
				# if osm_walk_path.exists() and nodes_path.exists() and edges_path.exists():
				#     nodes, edges = pd.read_csv(str(nodes_path)), pd.read_csv(
				#         str(edges_path))
				# else:
				#     osm_walk_path.mkdir(exist_ok=True)
				nodes, edges = ua.osm.load.ua_network_from_bbox(bbox=self.bbox, network_type='walk',
																														remove_lcn=True)
				# nodes.to_csv(str(nodes_path), index=False)
				# edges.to_csv(str(edges_path), index=False)
				ua.osm.network.create_osm_net(osm_edges=edges,
																			osm_nodes=nodes,
																			travel_speed_mph=3,
																			network_type='walk')

				urbanaccess_net = ua.network.integrate_network(urbanaccess_network=urbanaccess_net,
																											 headways=False)
				ua.gtfs.headways.headways(gtfsfeeds_df=loaded_feed,
																	headway_timerange=self.timerange)

				ua.network.integrate_network(urbanaccess_network=urbanaccess_net,
																		 headways=True,
																		 urbanaccess_gtfsfeeds_df=loaded_feed,
																		 headway_statistic='mean')
				ua.network.save_network(urbanaccess_network=urbanaccess_net,
																dir=final_net_path,
																filename='{}_transit_net.h5'.format(self.run_type, self),
																overwrite_key=True, overwrite_hdf5=True)
				# else:
				#     urbanaccess_net = ua.network.load_network(filename=f'{self.run_type}_transit_net.h5',
				#                                               dir=final_net_path)

				result.append((file,urbanaccess_net))
		return result
