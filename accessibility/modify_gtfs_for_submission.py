import shutil
from collections import defaultdict
from datetime import time
from pathlib import Path
from zipfile import ZipFile
import os

import numpy as np
import pandas as pd
import logging

TIME_FORMAT = '%H:%M:%S'  # strftime compatible format code


def to_time(time_in_secs):
	"""Convert time in seconds to python `datetime.time` object.

	:param time_in_secs:
	:return: a `datetime.time` object representing the time of day.
	"""
	hr = time_in_secs // 3600
	if hr > 23:
		hr = hr % 24  # reset hrs to 0 if trip ends after midnight.
	secs_remaining = time_in_secs % 3600
	mins, secs = secs_remaining // 60, secs_remaining % 60
	return time(hr, mins, secs)


def compute_stop_times(stop_time_data, route_id, trip_id):
	"""Given arrival times at uneven intervals for a trip, interpolate intermediate stop times.

	:param stop_time_data: pandas Dataframe of stop_times.txt data with columns `ats` and `dts` as arrival and departure
			times in seconds, respectively.
	:param route_id: identifier for route
	:param trip_id: trip_id for route
	:return:
	"""
	idx0 = 1
	ft = stop_time_data.xs(route_id).loc[trip_id]
	ft['shape_dist_diff'] = ft['shape_dist_traveled'].diff()
	at0 = ft.iloc[0]['ats']
	sdt0 = 0
	for idx1, row in ft[~np.isnan(ft.ats)].iloc[1:].iterrows():
		at1 = row['ats']
		sdt1 = row['shape_dist_traveled']
		speed_subseq = (sdt1 - sdt0) / (at1 - at0)
		next_time = at0
		for i in range(idx0 + 1, idx1):
			time_diff = ft.loc[i, 'shape_dist_diff'] / speed_subseq
			ft.loc[i, 'time_diff'] = time_diff
			next_time = next_time + time_diff
			ft.loc[i, 'ats'] = next_time

		at0, sdt0, idx0 = at1, sdt1, idx1
	return ft


def copy_gtfs(source_path, target_directory):
	"""Copies GTFS zip file from source path to target directory and unzips it there.
	"""
	target_path = Path(target_directory) / "gtfs"

	if not target_path.exists():
		target_path.mkdir()

	for file in os.listdir(source_path):
		if file.endswith(".zip"):

			shutil.copyfile(source_path+"/"+file, Path(target_directory) / file)

			if not (target_path / file.split(".")[0]).exists():
				Path(target_path / file.split(".")[0]).mkdir()

			with ZipFile(Path(target_directory)/file) as z:
				for f in z.namelist():
					(target_path/file.split(".")[0]/f).write_bytes(z.open(f).read())

	print("Done copying gtfs to {}".format(target_directory))



def load_stop_times_and_trips_from_zip(gtfs_zip_path):
	"""Loads disk-backed gtfs data for urbanaccess
	as zipfile into memory by first unzipping to a temporary directory.

	Directory is deleted upon return of data.
	"""
	with ZipFile(gtfs_zip_path) as z:
		for file in z.namelist():
			if file.endswith(".txt"):
				if 'stop_time' in file:
					stop_times = pd.read_csv(z.open(file))
				elif 'trips' in file:
					trips = pd.read_csv(z.open(file), index_col='trip_id')
					trips['route_id'] = trips['route_id'].astype(str)
		return stop_times, trips


if __name__ == '__main__':
	import sys
	GTFS_ZIP_PATH = f"fixed-data/sf_light/r5/{sys.argv[1]}"

	FREQUENCY_ADJUSTMENT_PATH = "submission-inputs/FrequencyAdjustment.csv"
	TARGET_DIRECTORY = "tmp-data"
	frequencies = pd.read_csv(FREQUENCY_ADJUSTMENT_PATH)
	frequencies['start_time'], frequencies['end_time'] = pd.TimedeltaIndex(frequencies['start_time']).seconds, pd.TimedeltaIndex(
		frequencies['end_time']).seconds
	frequencies.set_index(['route_id','start_time'], inplace=True)
	copy_gtfs(GTFS_ZIP_PATH, TARGET_DIRECTORY)

	if frequencies.empty:
		print("FrequencyAdjustment is empty. Nothing to be updated.")
	else:
		file_dict = dict()
		count = 0
		for file in os.listdir(GTFS_ZIP_PATH):
			count += 1
			if file.endswith(".zip"):
				stop_times, trips = load_stop_times_and_trips_from_zip(GTFS_ZIP_PATH+"/"+file)
				stop_times['route_id'] = stop_times.trip_id.apply(lambda x: trips.loc[x] if x in trips.index else 0)['route_id']
				stop_times = stop_times.set_index(['route_id', 'trip_id',   'stop_sequence'])
				stop_times['ats'], stop_times['dts'] = pd.TimedeltaIndex(stop_times['arrival_time']).seconds, pd.TimedeltaIndex(
			stop_times['departure_time']).seconds

				# Update stop_times
				new_trip_data_dict = defaultdict(list)
				route_ids_used = []
				route_data = []
				trips_update = pd.DataFrame({}, columns=trips.columns)

				new_freq = frequencies[frequencies.file_name.str.contains(file)]

				for i, freq in enumerate(new_freq.itertuples()):

					route_id, start_time = freq.Index

					service_trip_idx = 0
					pos_trips = stop_times.xs(route_id)
					try:
						# Of trips on route w/ departure time greater than or equal to start_time take the one w/ the earliest arrival time
						service_trip_template = pos_trips[(pos_trips.ats >= start_time)].iloc[0]
					except IndexError as e:
						service_trip_template = pos_trips.iloc[-1]
						log(f"No possible arrival time found greater than or equal to {start_time}; Using last trip of day {service_trip_template.name[0]} on Route {route_id} as trip template", name=__name__, level=logging.ERROR,filename='./gtfs_mod')

					old_trip_id = service_trip_template.name[0]
					old_shape_id = trips.loc[old_trip_id, 'shape_id']
					new_stop_times = compute_stop_times(stop_times, route_id, old_trip_id)
					old_service_id = trips.loc[old_trip_id, 'service_id']

					tmp_trip_data = {'route_id': route_id, 'shape_id': old_shape_id, 'service_id': old_service_id}

					new_trips = []
					# The following loop will create a new trip offset by headway_secs
					while start_time < freq.end_time:
						# Compute new keys common to updated trips and stop_times files
						new_trip_id = str(old_trip_id) + "_" + str(start_time) + "_" + str(service_trip_idx)

						new_trip_data = tmp_trip_data.copy()

						new_trip_data['trip_id'] = new_trip_id
						new_trips.append(new_trip_data)

						new_stop_times.loc[:, 'trip_id'] = new_trip_id
						new_stop_times.loc[:, 'route_id'] = route_id

						new_trip_data_dict[route_id].append(new_stop_times.copy(deep=True))
						new_stop_times['ats'] = new_stop_times['ats'] + freq.headway_secs

						# Increment counters
						start_time += freq.headway_secs
						service_trip_idx += 1

					# Combine data along routes
					try:
						new_route_data = pd.concat(new_trip_data_dict[route_id], axis=0).sort_values(['trip_id', 'ats'])
						new_route_data.arrival_time = new_route_data.ats.apply(lambda x: to_time(int(x)).strftime(TIME_FORMAT))
						new_route_data.departure_time = new_route_data.arrival_time
						new_route_data = new_route_data.reset_index().set_index('trip_id')
						new_route_data.loc[:, 'route_id'] = route_id

						# Concat new trip data to update DF
						trips_update = pd.concat([trips_update, pd.DataFrame(new_trips)], sort=False)

						route_data.append(new_route_data)
						if route_id not in route_ids_used:
							route_ids_used.append(route_id)
					except ValueError:
						print("No need to modify new route data")

				# Update stop_times and write to file
				stop_times.drop(sorted(route_ids_used))
				if len(route_data) != 0:
					final = pd.concat(route_data, axis=0)
				final = final.drop(['ats', 'dts', 'shape_dist_diff'], axis=1).reset_index().set_index(
					['route_id', 'trip_id', 'stop_sequence'])
				mod_stop_times = pd.concat([final, stop_times], sort=False).reset_index()
				mod_stop_times.to_csv(Path(TARGET_DIRECTORY) / "gtfs" / file.split(".")[0] / "stop_times.txt", index=False)

				# Update trip_times and write to file
				trips.reset_index().set_index('route_id').drop(route_ids_used, inplace=True)
				new_trips = pd.concat([trips_update.set_index('trip_id').reset_index(), trips.reset_index()], sort=False)
				new_trips.to_csv(Path(TARGET_DIRECTORY) / "gtfs" / file.split(".")[0]/ "trips.txt", index=False)

				# Update frequencies.csv
				freq_df = new_freq.reset_index()
				trips_df = trips.reset_index()
				freq_df['trip_id'] = freq_df['route_id'].apply(lambda x: trips_df[trips_df.route_id == x].trip_id.iloc[0])
				freq_df = freq_df.drop('route_id', axis=1)
				freq_df = freq_df.set_index('trip_id').reset_index()
				freq_df.to_csv(Path(TARGET_DIRECTORY) / "gtfs" / file.split(".")[0] / "frequencies.txt", index=False)
