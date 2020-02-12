
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
import numpy as np
import pandas as pd
import seaborn as sns
from pathlib import Path

from lxml import etree as ET
import zipfile
import gzip
import math
import re
import shutil
import zipfile

import utm
from shapely.geometry import Point, Polygon
from collections import defaultdict



# Defining matplolib parameters
from .fixed_data_visualization import ReferenceData

plt.rcParams["axes.titlesize"] = 15
plt.rcParams["axes.titleweight"] = "bold"
plt.rcParams["axes.titlepad"] = 12
plt.rcParams["axes.labelsize"] = 11
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.bbox'] = 'tight'
plt.rcParams["xtick.labelsize"] = 11
plt.rcParams["ytick.labelsize"] = 11


def unzip_file(element_path):
    """Checking if the path points to an existing folder or to its .zip format; if only the .zip format exists,
    it unzips the folder.

    Parameters
    ----------
    element_path: PosixPath
        Absolute path of the folder or file of interest.

    Returns
    -------
        Absolute path of the (unzipped) folder of interest.
    """
    if element_path.exists():
        return element_path

    elif Path(str(element_path) + ".zip").exists():
        zip_folder = zipfile.ZipFile(str(element_path) + ".zip", 'r')
        zip_folder.extractall(element_path.resolve().parent)
        zip_folder.close()
        return element_path

    elif Path(str(element_path) + ".gz").exists():
        with gzip.open(str(element_path) + ".gz", 'rb') as f_in:
            with open(str(element_path), 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        return element_path

    else:
        raise FileNotFoundError("{} does not exist".format(element_path))


def open_xml(path):
    # Open xml and xml.gz files into ElementTree
    if path.endswith('.gz'):
        return ET.parse(gzip.open(path))
    else:
        return ET.parse(path)


########## PROCESS AND PLOT STATISTICS ##########

### 1- INPUTS ###

def splitting_min_max(df, name_column):
    """ Parsing and splitting the ranges in the "age" (or "income") columns into two new columns:
    "min_age" (or "min_income") with the bottom value of the range and "max_age" (or "max_income") with the top value
    of the range. Ex: [0:120] --> 0, 120

    Parameters
    ----------
    df: pandas dataframe
        ModeIncentives.csv or MassTransitFares.csv input file

    name_column: str
        Column containing the range values to parse

    Returns
    -------
    df: pandas dataframe
        New input dataframe with two "min" and "max" columns with floats int values instead of ranges values

    """
    # Parsing the ranges and creating two new columns with the min and max values of the range
    if df.empty:
        df["min_{0}".format(name_column)] = [0]
        df["max_{0}".format(name_column)] = [0]
    else:
        min_max = df[name_column].str.replace("[", "").str.replace("]", "").str.replace("(", "").str.replace(")", "") \
            .str.split(":", expand=True)
        df["min_{0}".format(name_column)] = min_max.iloc[:, 0].astype(int)
        df["max_{0}".format(name_column)] = min_max.iloc[:, 1].astype(int)

    return df


def process_incentives_data(incentives_data, max_incentive):
    """ Processing and reorganizing the data in an input dataframe to be ready for plotting

    Parameters
    ----------
    incentives_data: pandas DataFrame
        from ModeIncentives.csv input file

    max_incentive: float
        Maximum amount allowed for an incentive as defined in the Starter Kit "Inputs Specifications" page

    Returns
    -------
    incentives: pandas dataframe
        Incentives input data that is ready for plotting
    """
    incentives = incentives_data
    incentives["amount"] = incentives["amount"].astype(float)

    # Completing the dataframe with the missing subsidized modes (so that they appear in the plot)
    df = pd.DataFrame(["", "(0:0)", "(0:0)", 0.00]).T
    df.columns = ["mode", "age", "income", "amount"]

    modes = ["drive_transit", "walk_transit", "OnDemand_ride"]
    for mode in modes:
        if mode not in incentives["mode"].values:
            df["mode"] = mode
            incentives = incentives.append(df)

    # Splitting age and income columns
    splitting_min_max(incentives, "age")
    splitting_min_max(incentives, "income")

    # Creating a new column with normalized incentives amount for the colormap
    if np.max(incentives["amount"]) == 0:
        incentives["amount_normalized"] = 0
    else:
        incentives["amount_normalized"] = incentives["amount"] / max_incentive

    incentives["amount_normalized"] = incentives["amount_normalized"].astype('float')
    incentives = incentives.drop(labels=["age", "income"], axis=1)

    # Changing the type of the "mode" column to 'category' to reorder the modes
    incentives["mode"] = incentives["mode"].astype('category').cat.reorder_categories([
        'OnDemand_ride',
        'drive_transit',
        'walk_transit'])

    incentives = incentives.sort_values(by="mode")
    return incentives


def plot_incentives_inputs(incentives_data, max_incentive, max_age, max_income, name_run):
    """Plot the incentives input

    Parameters
    ----------
    incentives_data: pandas DataFrame
        from the ModeIncentives.csv input file

    max_incentive: float
        Maximum amount allowed for an incentive as defined in the Starter Kit "Inputs Specifications" page

    max_age: int
        Maximum age of any resident in Sioux Faux as defined in the Starter Kit "Inputs Specifications" page

    max_income: int
        Maximum income of any resident in Sioux Faux as defined in the Starter Kit "Inputs Specifications" page

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object

    """
    incentives = process_incentives_data(incentives_data, max_incentive)

    fig, ax = plt.subplots(1, 2, figsize=(14, 5), sharey=True, gridspec_kw={'width_ratios': [4, 5]})

    # color map
    my_cmap = plt.cm.get_cmap('YlOrRd')
    colors = my_cmap(incentives["amount_normalized"])

    # plot
    ax[0].barh(incentives["mode"], incentives["max_age"] - incentives["min_age"], left=incentives["min_age"],
               color=colors)
    ax[1].barh(incentives["mode"], incentives["max_income"] - incentives["min_income"], left=incentives["min_income"],
               color=colors)

    ax[0].set_xlabel("age")
    ax[0].set_xlim((0, max_age))

    ax[1].set_xlabel("income")
    ax[1].set_xlim((0, max_income))

    plt.suptitle("Input - Incentives by age and income group - {}".format(name_run), fontsize=15, fontweight="bold")

    sm = ScalarMappable(cmap=my_cmap, norm=plt.Normalize(0, np.max(incentives["amount"])))
    sm.set_array([])
    sm.set_clim(0, max_incentive)
    cbar = fig.colorbar(sm, ticks=[i for i in range(0, max_incentive + 1, 10)])
    cbar.set_label('Incentive amount [$/person-trip]', rotation=270, labelpad=25)

    return ax


def process_bus_data(vehicle_fleet_mix_data, route_ids, buses_list, agency_ids):
    """Processing and reorganizing the data in an input dataframe to be ready for plotting

    Parameters
    ----------
    vehicle_fleet_mix_data: pandas DataFrame
        from the FleetMix.csv input file

    route_ids: list
        All routes ids where buses operate (from `routes.txt` file in the GTFS data)

    buses_list: list
        All available buses, ordered as follow: the DEFAULT bus first and then the buses ordered by ascending bus size
        (from availableVehicleTypes.csv in the `reference-data` folder of the Starter Kit)

    agency_ids: list
        All agencies operating buses in the city (from `agencies.txt` file in the GTFS data)

    Returns
    -------
    fleet_mic: pandas dataframe
        FleetMix input data that is ready for plotting

    """
    fleet_mix = vehicle_fleet_mix_data

    if fleet_mix.empty:
        fleet_mix = pd.DataFrame(
            [[agency_id, "{}".format(route_id), "BUS-DEFAULT"] for route_id in route_ids for agency_id in agency_ids],
            columns=["agencyId", "routeId", "vehicleTypeId"])

    df = pd.DataFrame([agency_ids[0], 1, buses_list[0]]).T
    df.columns = ["agencyId", "routeId", "vehicleTypeId"]

    # Adding the missing bus types in the dataframe so that they appear in the plot
    for bus in buses_list:
        if bus not in fleet_mix["vehicleTypeId"].values:
            df["vehicleTypeId"] = bus
            fleet_mix = fleet_mix.append(df)

    # Adding the missing bus routes in the dataframe so that they appear in the plot
    fleet_mix["routeId"] = fleet_mix["routeId"].astype(int)

    df = pd.DataFrame([agency_ids[0], "", buses_list[0]]).T
    df.columns = ["agencyId", "routeId", "vehicleTypeId"]

    for route in [i for i in route_ids]:
        if route not in fleet_mix["routeId"].values:
            df["routeId"] = route
            fleet_mix = fleet_mix.append(df)

    # Reodering bus types starting by "BUS-DEFAULT" and then by ascending bus size order
    fleet_mix["vehicleTypeId"] = fleet_mix["vehicleTypeId"].astype('category').cat.reorder_categories(
        buses_list)

    fleet_mix = fleet_mix.drop(labels="agencyId", axis=1)
    fleet_mix.sort_values(by="vehicleTypeId", inplace=True)
    fleet_mix.reset_index(inplace=True, drop=True)

    return fleet_mix


def plot_vehicle_fleet_mix_inputs(vehicle_fleet_mix_data, route_ids, buses_list, agency_ids, name_run):
    """Plot the vehicle fleet mix input

    Parameters
    ----------
    See `process_bus_data()`

    name_run: str
    Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object

    """
    buses = process_bus_data(vehicle_fleet_mix_data, route_ids, buses_list, agency_ids)

    fig, ax = plt.subplots(figsize=(6.5, 5))

    ax = sns.scatterplot(x="vehicleTypeId", y="routeId", data=buses, s=80)

    plt.xlabel("Bus type")
    plt.ylabel("Bus route")
    plt.ylim((1339.5, 1351.5))
    ax.yaxis.set_major_locator(plt.MultipleLocator(1))

    plt.title("Input - Bus fleet mix - {}".format(name_run))

    return ax


def process_fares_data(fares_data, bau_fares_data, max_fare, route_ids):
    """Processing and reorganizing the data in an input dataframe to be ready for plotting


    Parameters
    ----------
    fares_data: pandas DataFrame
        From the MassTransitFares.csv input file

    bau_fares_data: pandas DataFrame
        From the BAU FleetMix.csv input file

    max_fare: float
        Maximum fare of a bus trip as defined in the Starter Kit "Inputs Specifications" page

    route_ids: list
        All routes ids where buses operate (from `routes.txt` file in the GTFS data)


    Returns
    -------
    fares: pandas DataFrame
        Mass Transit Fares input data that is ready for plotting
    """
    fares = fares_data
    fares_bau = bau_fares_data

    fares["age"] = fares["age"].astype(str)

    df = pd.DataFrame(columns=["agencyId", "routeId", "age", "amount"])

    # Replace RouteId = NaN values by all bus lines (12 rows)
    for row in range(len(fares)):
        if math.isnan(fares.iloc[row, 1]):
            df1 = pd.DataFrame(
                [[fares.iloc[row, 0], route, fares.iloc[row, 2], fares.iloc[row, 3]] for route in route_ids],
                columns=["agencyId", "routeId", "age", "amount"])
            df = df.append(df1)

        else:
            df = fares

    # Adding the missing bus types in the dataframe so that they appear in the plot
    for route_id in route_ids:
        if route_id not in df["routeId"].values:
            fares_bau["routeId"] = [route_id, route_id]
            df = df.append(fares_bau)

    # Splitting age ranges into 2 columns (min_age and max_age)
    fares = splitting_min_max(df, "age")
    fares["routeId"] = fares["routeId"].astype(int)
    fares["amount"] = fares["amount"].astype(float)

    fares = fares.drop(labels=["age"], axis=1)
    fares = fares.sort_values(by=["amount", "routeId"])
    fares["amount_normalized"] = fares["amount"] / max_fare

    return fares


def plot_mass_transit_fares_inputs(fares_data, bau_fares_data, max_fare, route_ids, name_run):
    """Plot the Mass Transit Fares input

    Parameters
    ----------
    See `process_fares_data()`

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object

    """
    fares = process_fares_data(fares_data, bau_fares_data, max_fare, route_ids)

    fig, ax = plt.subplots(figsize=(7, 5))

    # color map
    my_cmap = plt.cm.get_cmap('YlOrRd')
    colors = my_cmap(fares["amount_normalized"])

    plt.barh(fares["routeId"], fares["max_age"] - fares["min_age"], left=fares["min_age"], color=colors)

    plt.xlabel("Age")
    plt.ylabel("Bus route")
    plt.ylim((1339.5, 1351.5))
    plt.xlim((0, 120))
    ax.yaxis.set_major_locator(plt.MultipleLocator(1))
    ax.xaxis.set_major_locator(plt.MultipleLocator(10))

    sm = ScalarMappable(cmap=my_cmap, norm=plt.Normalize(0, np.max(fares["amount"])))
    sm.set_array([])
    sm.set_clim(0, max_fare)
    cbar = fig.colorbar(sm, ticks=[i for i in range(0, max_fare + 1)])
    cbar.set_label('Fare amount [$]', rotation=270, labelpad=25)

    # Replace the 0 by 0.01 in the color scale as fares must be greater than 0
    y_ticks_labels = ["{0}".format(i) for i in range(0, 10 + 1)]
    y_ticks_labels[0] = "0.01"
    cbar.ax.set_yticklabels(y_ticks_labels)

    plt.title("Input - Mass Transit Fares - {}".format(name_run))
    return ax


def process_frequency_data(bus_frequencies_data, route_ids):
    """Processing and reorganizing the data in an input dataframe to be ready for plotting

    Parameters
    ----------
    bus_frequencies_data : pandas DataFrame
        From the `FrequencyAdjustment.csv` input file

    route_ids: list
        All routes ids where buses operate (from `routes.txt` file in the GTFS data)

    Returns
    -------
    frequency : pandas DataFrame
        Frequency Adjustment input data that is ready for plotting.

    """
    frequency = bus_frequencies_data

    # Add all missing routes (the ones that were not changed) in the DF so that they appear int he plot
    df = pd.DataFrame([0, 0, 0, 1]).T
    df.columns = ["route_id", "start_time", "end_time", "headway_secs"]

    if len(frequency["route_id"]) > 0:
        for route in route_ids:
            if route not in frequency["route_id"].values:
                df["route_id"] = route
                frequency = frequency.append(df)

        frequency["start_time"] = (frequency["start_time"].astype(int) / 3600).round(1)
        frequency["end_time"] = (frequency["end_time"].astype(int) / 3600).round(1)
        frequency["headway_secs"] = (frequency["headway_secs"].astype(int) / 3600).round(1)
        frequency["route_id"] = frequency["route_id"].astype(int)

        frequency = frequency.sort_values(by="route_id")
        frequency = frequency.set_index("route_id")

    return frequency


def plot_bus_frequency(bus_frequencies_data, route_ids, name_run):
    """Plotting the Frequency Adjustment input

    Parameters
    ----------
    See `process_frequency_data()`

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object

    """

    frequencies = process_frequency_data(bus_frequencies_data, route_ids)

    fig, ax = plt.subplots(figsize=(15, 4))
    plotted_lines = []

    # Defines a set of 12 colors for the bus lines
    colors = ['blue', 'red', 'green', 'orange', 'purple', 'yellow', 'pink', 'gold', 'lime', 'steelblue', 'm',
              'limegreen']
    if len(frequencies) > 0:
        color_dict = {frequencies.index.unique()[i]: colors[i] for i in range(12)}

        for idx in range(len(frequencies)):
            row_freq = frequencies.iloc[idx]
            height = row_freq.headway_secs
            height = height + np.random.normal(0, 0.03, 1)
            if row_freq.name not in plotted_lines:
                ax.plot([row_freq.start_time, row_freq.end_time], [height, height],
                        label=row_freq.name, linewidth=5, alpha=0.8, color=color_dict[row_freq.name])
                plotted_lines.append(row_freq.name)
            else:
                ax.plot([row_freq.start_time, row_freq.end_time], [height, height],
                        linewidth=5, alpha=0.8, color=color_dict[row_freq.name])

    plt.legend(bbox_to_anchor=(1.1, 1.0), title='Bus line')
    plt.ylim(0.0, 2.0)
    plt.xticks(np.arange(0, 25, 1))
    ax.set_xlim(0, 24)
    plt.ylabel("Headway [h]")
    plt.xlabel("Hours of the day")
    plt.title("Input - Frequency Adjustment - {}".format(name_run))

    return ax


### 2 - OUTPUTS ###

def process_overall_mode_choice(mode_choice_data):
    """Processing and reorganizing the data in a dataframe ready for plotting

    Parameters
    ----------
    mode_choice_data:  pandas DataFrame
        From the `modeChoice.csv` input file (located in the output directory of the simulation)

    Returns
    -------
    mode_choice: pandas DataFrame
        Mode choice data that is ready for plotting.

    """
    mode_choice = mode_choice_data
    # Select columns w/ modes
    mode_choice = mode_choice.iloc[-1, :]
    mode_choice = mode_choice.drop(["iterations"])
    # Replace "ride_hail" by "on_demand ride"
    mode_choice.rename({"ride_hail": "on-demand ride"}, inplace=True)
    return mode_choice


def plot_overall_mode_choice(mode_choice_data, name_run):
    """Plotting the Overall Mode choice output

    Parameters
    ----------
    see process_overall_mode_choice()

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object

    """
    mode_choice = process_overall_mode_choice(mode_choice_data)
    fig, ax = plt.subplots(figsize=(7, 5))
    mode_choice.plot(kind="pie", startangle=90, labels=None, autopct='%1.1f%%', pctdistance=0.8)
    plt.axis("image")
    plt.ylabel("")

    labels = mode_choice.index.values
    ax.legend(labels, bbox_to_anchor=(1.1, 0.5), loc="center right", fontsize=11, bbox_transform=plt.gcf().transFigure,
              title="Mode")

    ax.set_title("Output - Overall mode choice - {}".format(name_run))
    return ax


def process_mode_choice_by_hour(mode_choice_by_hour_data_path):
    """Processing and reorganizing the data in a dataframe ready for plotting

    Parameters
    ----------
    mode_choice_by_hour_data_path:  pathlib.Path object
        Absolute path of the `{ITER_NUMBER}modeChoice.csv` input file (located in the
        <output directory>/ITERS/it.<ITER_NUMBER>/ directory of the simulation)

    Returns
    -------
    mode_choice_by_hour: pandas DataFrame
        Mode choice by hour data ready for plotting.

        """
    mode_choice_by_hour = pd.read_csv(mode_choice_by_hour_data_path, index_col=0).T
    mode_choice_by_hour.reset_index(inplace=True)
    mode_choice_by_hour.dropna(inplace=True)
    mode_choice_by_hour.loc[:, "hours"] = mode_choice_by_hour["index"].apply(lambda x: x.split("_")[1])
    mode_choice_by_hour = mode_choice_by_hour.set_index("hours")
    mode_choice_by_hour.rename({"ride_hail": "on-demand ride"}, inplace=True)
    mode_choice_by_hour = mode_choice_by_hour.drop(labels="index", axis=1)

    return mode_choice_by_hour


def plot_mode_choice_by_hour(mode_choice_by_hour_data_path, name_run):
    """Plotting the Overall Mode choice By Hour output

    Parameters
    ----------
    see process_mode_choice_by_hour()

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object
    """
    mode_choice_per_hour = process_mode_choice_by_hour(mode_choice_by_hour_data_path)

    mode_choice_per_hour.plot.bar(stacked=True, figsize=(15, 5))
    plt.legend(bbox_to_anchor=(1.01, 1), loc="upper left", title="Mode")
    plt.xlabel("Hours")
    plt.ylabel("Number of trips chosing the mode")
    plt.grid(alpha=0.9)

    plt.title("Output - Mode choice over the agent's day \n (goes past midnight) - {}".format(name_run))


def plot_mode_choice_by_income_group(person_df, trips_df, name_run):
    """Plotting the Overall Mode choice By Income Group output

    Parameters
    ----------
    person_df: pandas DataFrame
        parsed and processed xml.files

    trips_df: pandas DataFrame
        parsed and processed xml.files

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object
    """
    person_df = person_df[['PID', 'Age', 'income']]
    mode_df = trips_df[['PID', 'realizedTripMode']]
    people_age_income_mode = person_df.merge(mode_df, on=['PID'])
    people_age_income_mode['income_group'] = pd.cut(people_age_income_mode.income,
                                                    [0, 10000, 25000, 50000, 75000, 100000, float('inf')],
                                                    right=False)
    people_income_mode_grouped = people_age_income_mode.groupby(by=['realizedTripMode', 'income_group']).agg(
        'count').reset_index()

    # rename df column to num_people due to grouping
    people_income_mode_grouped = people_income_mode_grouped.rename(
        index=str, columns={'PID': 'num_people'})

    # plot
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.barplot(data=people_income_mode_grouped, x="realizedTripMode", y="num_people", hue="income_group", ax=ax)
    ax.legend(title="Income group", bbox_to_anchor=(1.0, 1.01))
    ax.set_title("Output - Mode choice by income group - {}".format(name_run))
    return ax

def plot_mode_choice_per_income_group(person_df, trips_df, name_run):
    """Plotting the Overall Mode choice percentages per Income Group output

    Parameters
    ----------
    person_df: pandas DataFrame
        parsed and processed xml.files

    trips_df: pandas DataFrame
        parsed and processed xml.files

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object
    """
    person_df = person_df[['PID', 'Age', 'income']]
    mode_df = trips_df[['PID', 'realizedTripMode']]
    people_age_income_mode = person_df.merge(mode_df, on=['PID'])
    people_age_income_mode['income_group'] = pd.cut(people_age_income_mode.income,
                                                    [0, 10000, 25000, 50000, 75000, 100000, float('inf')],
                                                    right=False)
    people_income_mode_grouped = people_age_income_mode.groupby(by=['realizedTripMode', 'income_group']).agg('count').reset_index()

    # rename df column to num_people due to grouping
    people_income_mode_grouped = people_income_mode_grouped.rename(
        index=str, columns={'PID': 'num_people'})
    
    mode_df_dub_grouped = people_income_mode_grouped.groupby(by='income_group').agg('sum')
    mode_df_dub_grouped = mode_df_dub_grouped.rename(index=str, columns={'Age': 'total_trips_by_income'})
    
    people_income_mode_grouped['total_trips_by_income'] = np.zeros(people_income_mode_grouped.shape[0])
    for d in people_income_mode_grouped['income_group'].unique():
        people_income_mode_grouped.loc[people_income_mode_grouped['income_group']==d,'total_trips_by_income'] = mode_df_dub_grouped.loc[str(d),'total_trips_by_income']
    
    people_income_mode_grouped['percent_trips_by_income']=  people_income_mode_grouped['num_people']/people_income_mode_grouped['total_trips_by_income']
    
    # plot
    fig, ax = plt.subplots(figsize=(9, 6))
    sns.barplot(data=people_income_mode_grouped, x="income_group", y="percent_trips_by_income", hue="realizedTripMode", ax=ax)
    ax.legend(title="Income group", bbox_to_anchor=(1.0, 1.01))
    ax.set_title("Output - Mode choice by income group - {}".format(name_run))
    return ax


def plot_mode_choice_by_age_group(person_df, trips_df, name_run):
    """Plotting the Overall Mode choice By Age Group output

    Parameters
    ----------
    person_df: pandas DataFrame
        parsed and processed xml.files

    trips_df: pandas DataFrame
        parsed and processed xml.files

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object
    """
    person_df = person_df[['PID', 'Age', 'income']]
    mode_df = trips_df[['PID', 'realizedTripMode']]
    people_age_mode = person_df.merge(mode_df, on=['PID'])

    people_age_mode['age_group'] = pd.cut(people_age_mode.Age,
                                          [0, 18, 30, 40, 50, 60, float('inf')],
                                          right=False)

    # group the data and reset index to keep as consistent dataframe
    people_age_mode_grouped = people_age_mode.groupby(
        by=['realizedTripMode', 'age_group']).agg('count').reset_index()

    # rename df column to num_people due to grouping
    people_age_mode_grouped = people_age_mode_grouped.rename(index=str, columns={'PID': 'num_people'})
    fig, ax = plt.subplots(figsize=(9, 6))
    sns.barplot(data=people_age_mode_grouped, x="realizedTripMode", y="num_people", hue="age_group")
    ax.legend(title="Age group", bbox_to_anchor=(1.0, 1.01))
    plt.title("Output - Mode choice by age group - {}".format(name_run))

    return ax

def plot_mode_choice_by_trip_distance(trips_df, name_run):
    """Plotting the Overall Mode choice By Trip Distance output

    Parameters
    ----------
    trips_df: pandas DataFrame
        parsed and processed xml.files

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object
    """

    mode_df = trips_df[['Trip_ID', 'Distance_m', 'realizedTripMode']]
    mode_df['distance_group'] = pd.cut(mode_df.Distance_m,
                                       [0, 1000, 2500, 5000, 7500, 10000, 60000],
                                       right=False)

    mode_df_grouped = mode_df.groupby(by=['realizedTripMode', 'distance_group']).agg('count').reset_index()

    # rename df column to num_people due to grouping
    mode_df_grouped = mode_df_grouped.rename(index=str, columns={'Trip_ID': 'num_trips'})

    mode_df_dub_grouped = mode_df_grouped.groupby(by='distance_group').agg('sum')
    mode_df_dub_grouped = mode_df_dub_grouped.rename(index=str, columns={'Distance_m': 'total_trips_by_dist'})

    mode_df_grouped['total_trips_by_dist'] = np.zeros(mode_df_grouped.shape[0])
    for d in mode_df_grouped['distance_group'].unique():
        mode_df_grouped.loc[mode_df_grouped['distance_group'] == d, 'total_trips_by_dist'] = mode_df_dub_grouped.loc[
            str(d), 'total_trips_by_dist']
    mode_df_grouped['% Total Trips by Trip Distance'] = mode_df_grouped['num_trips'] / mode_df_grouped[
        'total_trips_by_dist']
    trip_distance_labels = {x[0]: str(x[0]) + ', n = ' + str(int(x[1][1])) for x in mode_df_dub_grouped.iterrows()}
    mode_df_grouped['trip_labels'] = [trip_distance_labels[str(y[1][1])] for y in mode_df_grouped.iterrows()]
    mode_df_grouped = mode_df_grouped.rename(index=str, columns={'distance_group': 'Trip Distance (meters)'})
    # plot
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.barplot(data=mode_df_grouped, x="Trip Distance (meters)", y="% Total Trips by Trip Distance",
                hue="realizedTripMode", ax=ax)
    ax.legend(title="Trip Mode Choice", bbox_to_anchor=(1.0, 1.01))
    ax.set_title("Output - Mode choice by trip distance - {}".format(name_run))
    return ax


def plot_mode_choice_by_trip_distance_stacked(trips_df, name_run):
    """Plotting the Overall Mode choice By Trip Distance output

    Parameters
    ----------
    trips_df: pandas DataFrame
        parsed and processed xml.files

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object
    """

    mode_df = trips_df[['Trip_ID', 'Distance_m', 'realizedTripMode']]
    mode_df.loc[:,'Distance_miles'] = mode_df.loc[:,'Distance_m'] * 0.000621371
    mode_df.loc[:,'Trip Distance (miles)'] = pd.cut(mode_df.Distance_miles,[0, .5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 7.5, 10, 40],right=False)

    mode_df_grouped = mode_df.groupby(by=['realizedTripMode', 'Trip Distance (miles)']).agg('count').reset_index()

    # rename df column to num_people due to grouping
    mode_df_grouped = mode_df_grouped.rename(index=str, columns={'Trip_ID': 'num_trips'})

    for_plot = mode_df_grouped[['realizedTripMode', 'Trip Distance (miles)', 'num_trips']]
    for_plot = for_plot.rename(columns={'realizedTripMode': 'Trip Mode'})
    for_plot = for_plot.pivot(index='Trip Distance (miles)', columns='Trip Mode', values='num_trips')

    # plot

    for_plot.plot.bar(stacked=True, figsize=(10, 6))
    plt.ylabel('Number of Trips')


def plot_num_trips_by_trip_distance(trips_df, name_run):
    """Plotting the Overall Mode choice By Trip Distance output

    Parameters
    ----------
    trips_df: pandas DataFrame
        parsed and processed xml.files

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object
    """

    mode_df = trips_df[['Trip_ID', 'Distance_m', 'realizedTripMode']]
    mode_df['distance_group'] = pd.cut(mode_df.Distance_m,
                                       [0, 1000, 2500, 5000, 7500, 10000, 60000],
                                       right=False)

    mode_df_grouped = mode_df.groupby(by=['realizedTripMode', 'distance_group']).agg('count').reset_index()

    # rename df column to num_people due to grouping
    mode_df_grouped = mode_df_grouped.rename(index=str, columns={'Trip_ID': 'num_trips'})

    mode_df_dub_grouped = mode_df_grouped.groupby(by='distance_group').agg('sum')
    mode_df_dub_grouped = mode_df_dub_grouped.rename(index=str, columns={'Distance_m': 'total_trips_by_dist'})

    mode_df_grouped['total_trips_by_dist'] = np.zeros(mode_df_grouped.shape[0])
    for d in mode_df_grouped['distance_group'].unique():
        mode_df_grouped.loc[mode_df_grouped['distance_group'] == d, 'total_trips_by_dist'] = mode_df_dub_grouped.loc[
            str(d), 'total_trips_by_dist']

    mode_df_grouped = mode_df_grouped.rename(index=str, columns={"distance_group": "Trip Distance (meters)",
                                                                 "total_trips_by_dist": "Number of Trips"})

    # plot
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.barplot(data=mode_df_grouped, x="Trip Distance (meters)", y="Number of Trips", ax=ax)
    # ax.legend(title="Trip Mode Choice", bbox_to_anchor=(1.0, 1.01))
    ax.set_title("Output - Number of Trips by Trip Distance - {}".format(name_run))
    return ax


def plot_average_speed_by_tod_per_mode(trips_df, name_run):
    """Plotting the average speed by time of day per trip mode output

    Parameters
    ----------
    trips_df: pandas DataFrame
        parsed and processed xml.files

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object
    """
    trips_df['average speed (meters/sec)'] = trips_df['Distance_m'] / trips_df['Duration_sec']
    trips_df['Average Speed (miles/hour)'] = 2.23694 * trips_df['average speed (meters/sec)']
    trips_df['Start_time_hour'] = trips_df['Start_time'] / 3600
    # trips_df['Start time (hour)'] =round(trips_df['Start_time_hour'],0)
    trips_new = trips_df.loc[trips_df['Duration_sec'] > 0,]
    trips_new.loc[:,'time_interval'] = pd.cut(trips_new['Start_time_hour'],
                                        [6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26],
                                        right=False)
    trips_new = trips_new.rename(index=str, columns={"time_interval": "Start time interval (hour)"})

    # plot
    fig, ax = plt.subplots(figsize=(12, 6))
    # sns.lineplot(data=trips_grouped_tod, x="Start time (hour)", y="average speed (miles/hour)", hue="realizedTripMode", ax=ax)
    sns.barplot(data=trips_new, x="Start time interval (hour)", y="Average Speed (miles/hour)", hue="realizedTripMode",
                ax=ax)
    ax.legend(title="Trip Mode", bbox_to_anchor=(1.0, 1.01))
    ax.set_title("Average Travel Speed by Time of Day per Mode - {}".format(name_run))
    return ax

def plot_num_trips_by_tod_per_mode(trips_df, name_run):
    """Plotting the number of trips by binned time of day per trip mode output

    Parameters
    ----------
    trips_df: pandas DataFrame
        parsed and processed xml.files

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object
    """
    trips_df['average speed (meters/sec)'] = trips_df['Distance_m'] / trips_df['Duration_sec']
    trips_df['Average Speed (miles/hour)'] = 2.23694 * trips_df['average speed (meters/sec)']
    trips_df['Start_time_hour'] = trips_df['Start_time'] / 3600
    # trips_df['Start time (hour)'] =round(trips_df['Start_time_hour'],0)
    trips_new = trips_df.loc[trips_df['Duration_sec'] > 0,]
    trips_new['time_interval'] = pd.cut(trips_new['Start_time_hour'],
                                        [6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26],
                                        right=False)
    trips_new = trips_new.rename(index=str, columns={"time_interval": "Start time interval (hour)"})
    trips_grouped = trips_new.groupby(by=["realizedTripMode", "Start time interval (hour)"]).agg('count').reset_index()
    trips_grouped = trips_grouped.rename(index=str, columns={"Trip_ID": "Number of Trips"})
    # plot
    fig, ax = plt.subplots(figsize=(12, 6))
    # sns.lineplot(data=trips_grouped_tod, x="Start time (hour)", y="average speed (miles/hour)", hue="realizedTripMode", ax=ax)
    sns.barplot(data=trips_grouped, x="Start time interval (hour)", y="Number of Trips", hue="realizedTripMode", ax=ax)
    ax.legend(title="Trip Mode", bbox_to_anchor=(1.0, 1.01))
    ax.set_title("Number of Trips by Time of Day per Mode - {}".format(name_run))
    return ax

def plot_average_travel_expenditure_per_trip_per_mode_over_day(trips_df, name_run):
    """Plot the Average Travel Expenditure Per Trip and By MOde Over THe Day output

    Parameters
    ----------
    trips_df: pandas DataFrame
        parsed and processed xml.files (output of event_parser.py)

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object
    """
    this_trips_df = trips_df.copy()
    this_trips_df.loc[:, 'trip_cost'] = np.zeros(this_trips_df.shape[0])

    this_trips_df.loc[this_trips_df['realizedTripMode'] == 'car', 'trip_cost'] = \
        this_trips_df.loc[this_trips_df['realizedTripMode'] == 'car', :].FuelCost.values

    this_trips_df.loc[(this_trips_df['realizedTripMode'] == 'walk_transit') |
                      (this_trips_df['realizedTripMode'] == 'drive_transit') |
                      (this_trips_df['realizedTripMode'] == 'OnDemand_ride'), 'trip_cost'] = \
        this_trips_df.loc[(this_trips_df['realizedTripMode'] == 'walk_transit') |
                          (this_trips_df['realizedTripMode'] == 'drive_transit') |
                          (this_trips_df['realizedTripMode'] == 'OnDemand_ride'),:].Fare.values - \
        this_trips_df.loc[(this_trips_df[ 'realizedTripMode'] == 'walk_transit') |
                          (this_trips_df['realizedTripMode'] == 'drive_transit') |
                          (this_trips_df['realizedTripMode'] == 'OnDemand_ride'),:].Incentive.values

    this_trips_df.loc[this_trips_df['realizedTripMode'] == 'drive_transit', 'trip_cost'] = \
        this_trips_df.loc[this_trips_df['realizedTripMode'] == 'drive_transit', :].trip_cost.values \
        + this_trips_df.loc[this_trips_df['realizedTripMode'] == 'drive_transit',:].FuelCost.values


    this_trips_df.loc[this_trips_df['trip_cost']<0,:] = 0
    #trips_df.loc[:, "trip_cost"] = trips_df.FuelCost.values + trips_df.Fare.values
    this_trips_df.loc[:, "hour_of_day"] = np.floor(this_trips_df.Start_time/3600)
    grouped_data = this_trips_df.groupby(by=["realizedTripMode", "hour_of_day"]).agg("mean")["trip_cost"].reset_index()
    grouped_data = grouped_data[grouped_data['realizedTripMode']!= 0]

    fig, ax = plt.subplots(figsize=(18, 8))
    sns.barplot(data=grouped_data, x="hour_of_day", y="trip_cost", hue="realizedTripMode", ax=ax, palette="Set2")
    ax.set_xlabel("Hour of the day")
    ax.set_ylabel("Average Cost [$]")
    ax.legend(loc="upper left", title="Mode")
    ax.set_title("Output - Average Travel Expenditure per Trip and by mode over the day - {}".format(name_run))
    return ax


def plot_incentives_distributed_by_mode(trips_df, name_run):
    """Plot the total incentives distributed by time of day per mode

    Parameters
    ----------
    trips_df: pandas DataFrame
        parsed and processed xml.files (output of event_parser.py)

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object
    """
    this_trips_df = trips_df.copy()
    this_trips_df.loc[:, 'trip_cost'] = np.zeros(this_trips_df.shape[0])
    this_trips_df.loc[this_trips_df['realizedTripMode'] == 'car', 'trip_cost'] = this_trips_df.loc[this_trips_df[ 'realizedTripMode'] == 'car',:].FuelCost.values
    this_trips_df.loc[(this_trips_df['realizedTripMode'] == 'walk_transit') | ( this_trips_df['realizedTripMode'] == 'drive_transit') | (this_trips_df['realizedTripMode'] == 'OnDemand_ride'), 'trip_cost'] = this_trips_df.loc[(this_trips_df['realizedTripMode'] == 'walk_transit') | ( this_trips_df['realizedTripMode'] == 'drive_transit') | (this_trips_df['realizedTripMode'] == 'OnDemand_ride'),:].Fare.values - \
                                                                                                                                                                                                               this_trips_df.loc[(this_trips_df['realizedTripMode'] == 'walk_transit') | ( this_trips_df['realizedTripMode'] == 'drive_transit') | (this_trips_df['realizedTripMode'] == 'OnDemand_ride'), :].Incentive.values
    this_trips_df.loc[this_trips_df['realizedTripMode'] == 'drive_transit', 'trip_cost'] = this_trips_df.loc[this_trips_df['realizedTripMode'] == 'drive_transit',:].trip_cost.values + \
                                                                                           this_trips_df.loc[this_trips_df['realizedTripMode'] == 'drive_transit', :].FuelCost.values
    this_trips_df.loc[:, 'Incentives_distributed'] = this_trips_df.Incentive.values
    this_trips_df.loc[this_trips_df['trip_cost'] < 0, 'Incentives_distributed'] = this_trips_df.loc[ this_trips_df['trip_cost'] < 0,:].Incentives_distributed.values - this_trips_df.loc[
                                                                                                                     this_trips_df['trip_cost'] < 0,:].trip_cost.values
    this_trips_df = this_trips_df.rename(columns={'Incentives_distributed': "Incentives distributed"})
    this_trips_df.loc[:, "hour_of_day"] = np.floor(trips_df.Start_time / 3600)
    grouped_data = this_trips_df.groupby(by=["realizedTripMode", "hour_of_day"]).agg("sum")[
        "Incentives distributed"].reset_index()

    # print(grouped_data)
    fig, ax = plt.subplots(figsize=(18, 8))
    sns.barplot(data=grouped_data, x="hour_of_day", y="Incentives distributed", hue="realizedTripMode", ax=ax,
                palette="Set2")
    ax.set_xlabel("Hour of the day")
    ax.set_ylabel("Total Incentives Distributed [$]")
    ax.legend(loc="upper left", title="Mode")
    ax.set_title("Output - Total Incentives Distributed by Time of Day per Mode - {}".format(name_run))
    return ax

def plot_average_bus_crowding_by_bus_route_by_period_of_day(path_df, trip_to_route, seating_capacities, transit_scale_factor, name_run):
    """Plot the Average hours of bus crowding output

    Parameters
    ----------
    path_df: pandas DataFrame
        parsed and processed xml.files

    trip_to_route: dictionary
        Correspondance between trip_ids and route_ids

    seating_capacities: dictionary
        Correspondance between each bus type and its seating capacity

    transit_scale_factor: float
        Downsizing factor defined in the config file (=0.1 for Sioux Faux)

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object
        """
    bus_slice_df = path_df.loc[path_df["mode"] == "bus"][["vehicle", "numPassengers", "departureTime",
                                                          "arrivalTime", "vehicleType"]]
    bus_slice_df.loc[:, "route_id"] = bus_slice_df.vehicle.apply(lambda x: trip_to_route[x.split(":")[1].split('-')[0]])
    bus_slice_df.loc[:, "serviceTime"] = (bus_slice_df.arrivalTime - bus_slice_df.departureTime) / 3600
    bus_slice_df.loc[:, "seatingCapacity"] = bus_slice_df.vehicleType.apply(
        lambda x: transit_scale_factor * seating_capacities[x])
    bus_slice_df.loc[:, "passengerOverflow"] = bus_slice_df.numPassengers > bus_slice_df.seatingCapacity
    # AM peak = 7am-10am, PM Peak = 5pm-8pm, Early Morning, Midday, Late Evening = in between
    bus_slice_df.loc[:, "servicePeriod"] = pd.cut(bus_slice_df.departureTime, [0, 25200, 36000, 61200, 72000, 86400],
                                                  labels=["Early Morning", "AM Peak", "Midday", "PM Peak",
                                                          "Late Evening"])

    fig, ax = plt.subplots(figsize=(10, 6))
    grouped_data = \
        bus_slice_df[bus_slice_df.passengerOverflow == True].groupby(["route_id", "servicePeriod"]).agg("sum")[
            "serviceTime"].fillna(0).reset_index()
    sns.barplot(data=grouped_data, x="route_id", y="serviceTime", hue="servicePeriod", ax=ax)
    ax.set_xlabel("Bus Route")
    ax.set_ylabel("Hours of bus crowding")
    ax.legend(loc=(1.02, 0.71), title="Service Period")
    ax.grid(True, which="both")
    ax.set_title("Output - Average Hours of bus crowding by bus route and period of day - {}".format(name_run))
    return ax


def process_travel_time(travel_time_data_path):
    """Processing and reorganizing the data in a dataframe ready for plotting

    Parameters
    ----------
    travel_time_data_path:  PosixPath
        Absolute path of the `{ITER_NUMBER}.averageTravelTimes.csv` input file (located in the
        <output directory>/ITERS/it.<ITER_NUMBER>/ directory of the simulation)

    Returns
    -------
    travel_time: pandas DataFrame
        Average travel_time by mode data that is ready for plotting.

        """
    travel_time = pd.read_csv(travel_time_data_path)
    travel_time = travel_time.set_index("TravelTimeMode\Hour")
    travel_time.rename({"ride_hail": "on_demand ride"}, inplace=True)
    travel_time["mean"] = travel_time.mean(axis=1)
    travel_time["mode"] = travel_time.index
    travel_time = travel_time.drop(labels="others", axis=0)
    travel_time = travel_time.loc[:, ["mode", "mean"]]
    return travel_time


def plot_travel_time_by_mode(travel_time_data_path, name_run):
    """Plotting the Average Travel Time by Mode output

    Parameters
    ----------
    see process_travel_time()

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object
    """
    travel_time = process_travel_time(travel_time_data_path)

    fig, ax = plt.subplots()

    fig.set_size_inches(7, 5)
    sns.barplot(x="mode", y="mean", data=travel_time, palette="Set2")
    plt.xlabel("Mode")
    plt.ylabel("Travel time [min]")
    plt.title("Output - Average travel time per trip and by mode - {}".format(name_run))

    return ax


def plot_parallel_travel_time_bau_submission(travel_time_data_bau_path, travel_time_data_path):
    """Plotting the Average Trip Travel Time by Mode output

        Parameters
        ----------
        travel_time_data_bau_path: pathlib.Path object

        travel_time_data_path: pathlib.Path object


        Returns
        -------
        ax: matplotlib axes object
        """

    travel_time_bau = process_travel_time(travel_time_data_bau_path)
    travel_time_bau.loc[:,"Scenario"] = ["bau"]*len(travel_time_bau)
    travel_time_submission = process_travel_time(travel_time_data_path)
    travel_time_submission.loc[:,"Scenario"] = ["your submission"]*len(travel_time_submission)
    travel_time_both = pd.concat([travel_time_bau, travel_time_submission])
    travel_time_both.reset_index(drop=True, inplace=True)

    # Plot
    fig, ax = plt.subplots()
    fig.set_size_inches(7, 5)
    sns.barplot(x="mode", y="mean", data=travel_time_both, hue="Scenario")

    ax.set_xlabel("Mode")
    ax.set_ylabel("Travel time [min]")
    ax.set_title("Output - Average travel time per trip and by mode")
    ax.legend(bbox_to_anchor=(1, 1))


def process_travel_time_over_the_day(travel_time_data_path):
    """Processing and reorganizing the data in a dataframe ready for plotting

    Parameters
    ----------
    travel_time_data_path:  PosixPath
        Absolute path of the `{ITER_NUMBER}.averageTravelTimes.csv` input file (located in the
        <output directory>/ITERS/it.<ITER_NUMBER>/ directory of the simulation)

    Returns
    -------
    travel_time: pandas DataFrame
        Average travel_time by mode and over the day data that is ready for plotting.

        """

    travel_time = pd.read_csv(travel_time_data_path)
    travel_time = travel_time.set_index("TravelTimeMode\Hour")
    travel_time.rename({"ride_hail": "on_demand ride"}, inplace=True)
    travel_time = travel_time.drop(labels="others", axis=0)
    travel_time.reset_index(inplace=True)

    melted_travel_time = pd.melt(travel_time, id_vars="TravelTimeMode\Hour")
    melted_travel_time.columns = ["mode", "hours", "travel time"]
    melted_travel_time = melted_travel_time.sort_values(by="hours")

    melted_travel_time["hours"] = pd.to_numeric(melted_travel_time["hours"])

    return melted_travel_time


def plot_travel_time_over_the_day(travel_time_data_path, name_run):
    """Plotting the Average Travel Time by Mode and by Hour of the Day output

    Parameters
    ----------
    see process_travel_time_over_the_day()

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object
    """
    melted_travel_time = process_travel_time_over_the_day(travel_time_data_path)

    fig, ax = plt.subplots()

    fig.set_size_inches(20, 8.27)
    sns.barplot(ax=ax, x="hours", y="travel time", hue="mode", data=melted_travel_time.sort_values(by="hours"),
                palette="Set2")
    plt.legend(loc="upper left", title="Mode")
    plt.xlabel("Hours")
    plt.ylabel("Travel time [min]")
    plt.xlim((0, 30))
    plt.ylim((0, 150))
    plt.yticks(np.arange(0, 151, 10), np.arange(0, 151, 10), fontsize=11)
    plt.xticks(np.arange(0, 31, 1), np.arange(0, 31, 1), fontsize=11)

    plt.title("Output - Average travel time per passenger-trip over the day - {}".format(name_run))

    return ax


def plot_cost_benefits(traversal_path_df, legs_df, operational_costs, trip_to_route, name_run):
    """Plotting the Costs and Benefits by bus route output

    Parameters
    ----------
    traversal_path_df: pandas DataFrame
        parsed and processed <num_iterations>.events.csv.gz' file

    legs_df: pandas DataFrame
        merge of parsed and processed xml.files

    operational_costs: dictionary
        Operational costs for each bus vehicle type as defined under "operational_costs" in the
        availableVehicleTypes.csv in the`reference-data` folder of the Starter Kit

    trip_to_route: dictionary
        Correspondance between trip_ids and route_ids

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object
        """
    bus_slice_df = traversal_path_df.loc[traversal_path_df["mode"] == "bus"][["vehicle", "numPassengers", "departureTime",
                                                          "arrivalTime", "FuelCost", "vehicleType"]]
    bus_slice_df.loc[:, "route_id"] = bus_slice_df.vehicle.apply(lambda x: trip_to_route[x.split(":")[-1].split('-')[0]])
    bus_slice_df.loc[:, "operational_costs_per_bus"] = bus_slice_df.vehicleType.apply(
        lambda x: operational_costs[x])
    bus_slice_df.loc[:, "serviceTime"] = (bus_slice_df.arrivalTime - bus_slice_df.departureTime) / 3600
    bus_slice_df.loc[:, "OperationalCosts"] = bus_slice_df.operational_costs_per_bus * bus_slice_df.serviceTime

    bus_fare_df = legs_df.loc[legs_df["Mode"] == "bus"][["Veh", "Fare"]]
    bus_fare_df.loc[:, "route_id"] = bus_fare_df.Veh.apply(
        lambda x: trip_to_route[x.split(":")[-1].split('-')[0].split('-')[0]])
    merged_df = pd.merge(bus_slice_df, bus_fare_df, on=["route_id"])

    grouped_data = merged_df.groupby(by="route_id").agg("sum")[["OperationalCosts", "FuelCost", "Fare"]]

    fig, ax = plt.subplots(figsize=(8, 6))
    grouped_data.plot.bar(stacked=True, ax=ax)
    plt.title("Output - Costs and Benefits of Mass Transit Level of Service Intervention by bus route - {}".format(name_run))
    plt.xlabel("Bus route")
    plt.ylabel("Amount [$]")
    ax.legend(title="Costs and Benefits")
    return ax


# def prepare_raw_scores(raw_scores_data):
#     # raw_scores_data = path of the submissionsScores.csv file
#     scores = pd.read_csv(raw_scores_data)
#     scores = scores.loc[:,["Component Name","Raw Score"]]
#
#     # Drop the `subission score` row
#     scores = scores.drop(index = 10, axis = 0)
#     scores["Component Name"] = scores["Component Name"].astype('category').cat.reorder_categories([
#            'Accessibility: Number of secondary locations accessible within 15 minutes',
#            'Accessibility: Number of work locations accessible within 15 minutes',
#            'Congestion: average vehicle delay per passenger trip',
#            'Congestion: total vehicle miles traveled',
#            'Level of service: average bus crowding experienced',
#            'Level of service: average on-demand ride wait times',
#            'Level of service: average trip expenditure - secondary',
#            'Level of service: average trip expenditure - work',
#            'Mass transit level of service intervention: costs and benefits',
#            'Sustainability: Total PM 2.5 Emissions'])
#
#     scores = scores.sort_values(by="Component Name")
#     scores.iloc[:2, 1] = scores.iloc[:2, 1].apply(np.reciprocal)
#     scores["Subscores"] = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
#     return scores


def process_weighted_scores_to_plot(scores_data):
    """ Put the data (weighted scores) of `submissionScores.csv` in the right format to be plotted.

    Parameters
    ----------
    scores_data: pandas DataFrame
        data from submissionScores.csv file

    Returns
    -------
    scores: pandas DataFrame
        weighted scores of the submission

    """
    scores = scores_data
    scores = scores.loc[:,["Component Name","Weighted Score"]]
    scores.set_index("Component Name", inplace = True)
    #Drop the `submission score` row
    # scores.drop('Level of service: average on-demand ride wait times', axis = 0, inplace=True)
    scores.reset_index( inplace = True)

    scores["Component Name"] = scores["Component Name"].astype('category').cat.reorder_categories([
        'Accessibility: Number of secondary locations accessible within 15 minutes',
        'Accessibility: Number of work locations accessible within 15 minutes',
        'Congestion: average vehicle delay per passenger trip',
        'Congestion: total vehicle miles traveled',
        'Level of service: average bus crowding experienced',
        'Level of service: average trip expenditure - secondary',
        'Level of service: average trip expenditure - work',
        'Level of service: costs and benefits',
        'Sustainability: Total PM 2.5 Emissions',
        'Submission Score'])

    scores = scores.sort_values(by="Component Name")
    #     scores.iloc[:2, 1] = scores.iloc[:2, 1].apply(np.reciprocal)
    #     scores["Subscores"] = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
    return scores


def plot_weighted_scores(scores_data, name_run):
    """Plot the weighted subscores and the submission score in a bar graph

    Parameters
    ----------
    scores_data: pandas DataFrame
        data from submissionScores.csv file

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object

    """
    scores = process_weighted_scores_to_plot(scores_data)
    fig, ax = plt.subplots(figsize=(7, 5))
    palette = ["steelblue"] * (len(scores)-1) + ["navy"]
    sns.barplot(data=scores, x="Weighted Score", y="Component Name", palette=palette)
    #color="steelblue"
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left")
    ax.set_xlabel("Weighted Score")
    ax.set_ylabel("Score component")
    ax.set_title("Weighted Subscores and Submission score - {}".format(name_run))
    return ax


def plot_vmt_per_mode(paths_traversals_df, legs_df, name_run):
    """Plot the total daily VMT by Mode output

    Parameters
    ----------
    paths_traversals_df: pandas Dataframe
        Gathers info on all traversal paths done by agents: output of the event_parser.py

    legs_df: pandas Dataframe
        Gathers info on each single leg constituing trips of agents: output of the event_parser.py

    Returns
    -------
    ax: matplotlib axes object
    """

    # gathering the data
    vmt_walk = round(
        paths_traversals_df[paths_traversals_df["mode"] == "walk"]["length"].apply(lambda x: x * 0.000621371).sum(), 0)
    vmt_bus = round(
        paths_traversals_df[paths_traversals_df["mode"] == "bus"]["length"].apply(lambda x: x * 0.000621371).sum(), 0)
    vmt_on_demand = round(
        legs_df[legs_df["Mode"] == "OnDemand_ride"]["Distance_m"].apply(lambda x: x * 0.000621371).sum(), 0)
    vmt_car = round(legs_df[legs_df["Mode"] == "car"]["Distance_m"].apply(lambda x: x * 0.000621371).sum(), 0)
    vmt = pd.DataFrame({"bus": [vmt_bus], "car": [vmt_car], "on_demand_ride": [vmt_on_demand], "walk":[vmt_walk]})

    # plotting
    fig, ax = plt.subplots()
    fig.set_size_inches(7, 5)
    sns.barplot(data=vmt)

    plt.xlabel("Mode")
    plt.ylabel("Vehicle miles traveled")
    plt.title("Output - Daily vehicle miles traveled per mode - {}".format(name_run))

    return ax


def process_bus_vmt_by_ridership_number_data(paths_traversals_df):
    """Plot the bus vehicle miles traveled by ridership (number of passengers in the bus) by hour of the day

    paths_traversals_df: pandas Dataframe
        Gathers info on all traversal paths done by agents: output of the event_parser.py

    Returns
    -------
    vmt_bus_ridership: pandas DataFrame
        List the vehicle miles traveled for each hour of the day - ridership number (#pax) combination
    """
    vmt_bus_ridership = paths_traversals_df[paths_traversals_df["mode"] == "bus"][
        ["numPassengers", "length", "departureTime", "arrivalTime"]]
    # Split the travels by hour of the day
    vmt_bus_ridership.loc[:, "Hour"] = pd.cut(vmt_bus_ridership["departureTime"], [i * 3600 for i in np.arange(25)],
                                              labels=["{0}".format(hour) for hour in np.arange(24)])

    # Group by hours of the day and number of passengers in the bus
    vmt_bus_ridership = vmt_bus_ridership.groupby(by=["Hour", "numPassengers"]).sum()
    vmt_bus_ridership.reset_index(inplace=True)
    vmt_bus_ridership.set_index("numPassengers", inplace=True)
    vmt_bus_ridership.replace(np.nan, 0, inplace=True)
    vmt_bus_ridership["Hour"] = vmt_bus_ridership["Hour"].astype("int")
    vmt_bus_ridership = vmt_bus_ridership.pivot(columns="Hour", values="length")
    return vmt_bus_ridership


def plot_bus_vmt_by_ridership_number_by_hour_of_the_day(paths_traversals_df, name_run):
    """Plot the bus vehicle miles traveled by ridership (number of passengers in the bus) by hour of the day

    paths_traversals_df: pandas Dataframe
        Gathers info on all traversal paths done by agents: output of the event_parser.py

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object
    """
    vmt_bus_ridership = process_bus_vmt_by_ridership_number_data(paths_traversals_df)

    # Plot
    fig, ax = plt.subplots()
    fig.set_size_inches(20, 8.27)
    vmt_bus_ridership.T.plot(kind="bar", stacked=True, ax=ax)

    ax.set_title("Output - Bus Vehicle Miles Traveled by ridership by time of day - {}".format(name_run))
    ax.set_xlabel("Hours")
    ax.set_ylabel("Vehicle Miles Traveled")
    ax.legend(loc="upper right", title="Number of passengers in the bus")
    plt.show()


def process_bus_vmt_by_ridership_state_data(paths_traversals_df, transit_scale_factor,seating_capacities,capacity,buses_list):
    """Plot the bus vehicle miles traveled by ridership state (empty, low/mediium ridership, crowded, full) by hour of the day

    paths_traversals_df: pandas Dataframe
        Gathers info on all traversal paths done by agents: output of the event_parser.py

    Returns
    -------
    vmt_bus_ridership: pandas DataFrame
        List the vehicle miles traveled for each hour of the day - ridership state combination
    """
    vmt_bus_ridership = paths_traversals_df[paths_traversals_df["mode"] == "bus"][
        ["numPassengers", "length", "departureTime", "arrivalTime", "vehicleType"]]

    # Calculate the capacity of each bus
    vmt_bus_ridership.loc[:, "seatingCapacity"] = vmt_bus_ridership["vehicleType"].apply(
        lambda x: transit_scale_factor * seating_capacities[x])
    vmt_bus_ridership.loc[:, "capacity"] = vmt_bus_ridership["vehicleType"].apply(
        lambda x: transit_scale_factor * capacity[x])

    # Split the travels by crowding state
    print()
    crowding_state_all_buses = pd.DataFrame(columns=vmt_bus_ridership.columns.tolist() + ["crowdingState"])
    for bus in buses_list:
        crowding_state = vmt_bus_ridership[vmt_bus_ridership["vehicleType"] == bus]
        crowding_state.loc[:, "crowdingState"] = pd.cut(crowding_state["numPassengers"],
                                                        [0, 1, transit_scale_factor * seating_capacities[bus] / 2,
                                                         transit_scale_factor * seating_capacities[bus],
                                                         transit_scale_factor * capacity[bus],
                                                         math.ceil(transit_scale_factor * capacity[bus]) + 1],
                                                        labels=["empty (0 passengers)",
                                                                "low ridership (< 50% seating capacity)",
                                                                "medium ridership(< seating capacity)",
                                                                "crowded (> seating capacity)",
                                                                "full (at capacity)"], right=False)

        crowding_state_all_buses = pd.concat([crowding_state_all_buses, crowding_state])

    crowding_state_all_buses
    # Split the travels by hour of the day
    crowding_state_all_buses.loc[:, "Hour"] = pd.cut(crowding_state_all_buses["departureTime"],
                                                     [i * 3600 for i in np.arange(25)],
                                                     labels=["{0}".format(hour) for hour in np.arange(24)],
                                                     duplicates="raise")

    # Group by hours of the day and number of passengers in the bus
    vmt_bus_ridership = crowding_state_all_buses.groupby(by=["Hour", "crowdingState"]).sum()
    vmt_bus_ridership.reset_index(inplace=True)
    vmt_bus_ridership["crowdingState"] = vmt_bus_ridership["crowdingState"].astype('category').cat.reorder_categories(
        ["empty (0 passengers)", "low ridership (< 50% seating capacity)",
         "medium ridership(< seating capacity)", "crowded (> seating capacity)", "full (at capacity)"])
    vmt_bus_ridership.set_index("crowdingState", inplace=True)
    vmt_bus_ridership.replace(np.nan, 0, inplace=True)
    vmt_bus_ridership["Hour"] = vmt_bus_ridership["Hour"].astype("int")
    vmt_bus_ridership = vmt_bus_ridership.pivot(columns="Hour", values="length")

    return vmt_bus_ridership


def plot_bus_vmt_by_ridership_state_by_hour_of_the_day(paths_traversals_df, transit_scale_factor,seating_capacities,
                                                       capacity,buses_list, name_run):
    """Plot the bus vehicle miles traveled by ridership (number of passengers in the bus) by hour of the day

    paths_traversals_df: pandas Dataframe
        Gathers info on all traversal paths done by agents: output of the event_parser.py

    name_run: str
        Name of the run , e.g. "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object
    """
    vmt_bus_ridership = process_bus_vmt_by_ridership_state_data(paths_traversals_df, transit_scale_factor,
                                                                seating_capacities,capacity,buses_list)

    # Plot
    fig, ax = plt.subplots()
    fig.set_size_inches(20, 8.27)
    vmt_bus_ridership.T.plot(kind="bar", stacked=True, ax=ax)

    ax.set_title("Output - Bus Vehicle Miles Traveled by occupancy state by time of day - {}".format(name_run))
    ax.set_xlabel("Hours")
    ax.set_ylabel("Vehicle Miles Traveled")
    ax.legend(loc="upper right", title="Occupancy state of the bus")
    plt.show()


def get_vmt_dataframe(paths_traversals_df, legs_df):
    vmt_walk = round(
        paths_traversals_df[paths_traversals_df["mode"] == "walk"]["length"].apply(lambda x: x * 0.000621371).sum(), 0)
    vmt_bus = round(
        paths_traversals_df[paths_traversals_df["mode"] == "bus"]["length"].apply(lambda x: x * 0.000621371).sum(), 0)

    vmt_on_demand = round(
        paths_traversals_df[paths_traversals_df["vehicle"].str.contains("rideHailVehicle")]["length"].apply(lambda x: x * 0.000621371).sum(), 0)
    vmt_car = round(legs_df[legs_df["Mode"] == "car"]["Distance_m"].apply(lambda x: x * 0.000621371).sum(), 0)
    vmt = pd.DataFrame({"bus": [vmt_bus], "car": [vmt_car], "on_demand_ride": [vmt_on_demand], "walk" : [vmt_walk]})
    return vmt


def plot_parallel_vmt_bau_submission(paths_traversals_df_bau, paths_traversals_df, legs_df_bau, legs_df):
    # Process the data
    vmt_bau = get_vmt_dataframe(paths_traversals_df_bau, legs_df_bau)
    vmt_submission = get_vmt_dataframe(paths_traversals_df, legs_df)
    vmt_both = pd.concat([vmt_bau, vmt_submission])
    vmt_both.loc[:, "Scenario"] = ["bau", "your submission"]
    vmt_both = pd.melt(vmt_both, id_vars=["Scenario"], value_vars=["bus", "car", "on_demand_ride", "walk"])

    # Plot
    fig, ax = plt.subplots()
    fig.set_size_inches(7, 5)
    sns.barplot(x="variable", y="value", data=vmt_both, hue="Scenario")

    ax.set_xlabel("Mode")
    ax.set_ylabel("Miles traveled")
    ax.set_title("Output - Daily miles traveled per mode")

    return ax


def process_vmt_on_demand_data(paths_traversals_df):
    """Process the path_traversals_df data to get Vehicle Miles Traveled by On-demand ride vehicles on Fetch Mode (on route to pick up a passenger)
    by hour of the day.

    Parameters
    ----------
    paths_traversals_df: pandas DataFrame
        Gather info on all traversal paths done by agents: output of the event_parser.py

    Returns
    -------
    ax: matplotlib axes object

    """
    vmt_on_demand = paths_traversals_df[paths_traversals_df["vehicle"].str.contains("rideHailVehicle")]
    vmt_on_demand = vmt_on_demand[["numPassengers", "departureTime", "length"]]
    vmt_on_demand.loc[:, "Hour"] = pd.cut(vmt_on_demand["departureTime"],
                                          [hour for hour in np.arange(0, 25 * 3600, 3600)],
                                          labels=["{hour}" for hour in np.arange(24)],
                                          right=False)
    vmt_on_demand.loc[:, "drivingState"] = pd.cut(vmt_on_demand["numPassengers"], [0, 1, 2], labels=["fetch", "fare"],
                                                  right=False)

    vmt_on_demand = vmt_on_demand.groupby(by=["Hour", "drivingState"]).sum()
    vmt_on_demand.reset_index(inplace=True)
    vmt_on_demand.set_index("drivingState", inplace=True)
    vmt_on_demand.replace(np.nan, 0, inplace=True)
    vmt_on_demand["Hour"] = vmt_on_demand["Hour"].astype("int")
    vmt_on_demand = vmt_on_demand.pivot(columns="Hour", values="length")

    #     vmt_on_demand_fetch = vmt_on_demand[vmt_on_demand["numPassengers"]==0]
    #     vmt_on_demand_fare = vmt_on_demand[vmt_on_demand["numPassengers"]==1]

    #     vmt_on_demand_fare = vmt_on_demand_fare.groupby(by="Hour").sum().reset_index()
    #     vmt_on_demand_fetch = vmt_on_demand_fetch.groupby(by="Hour").sum().reset_index()

    return vmt_on_demand


def plot_vmt_on_demand(paths_traversals_df, name_run):
    """Plot the Vehicle Miles Traveled by On-demand ride vehicles on Fetch Mode (on route to pick up a passenger)

    Parameters
    ----------
    paths_traversals_df: pandas DataFrame
        Gather info on all traversal paths done by agents: output of the event_parser.py

    name_run: str
        Name of the run: "BAU", "Run 1", "Submission"...

    Returns
    -------
    ax: matplotlib axes object

    """
    # Import DataFrame
    vmt_on_demand = process_vmt_on_demand_data(paths_traversals_df)
    #   vmt_on_demand_fetch, vmt_on_demand_fare = process_vmt_on_demand_data(paths_traversals_df)

    # Plot
    fig, ax = plt.subplots()
    fig.set_size_inches(20, 8.27)
    vmt_on_demand.T.plot(kind="bar", stacked=True, ax=ax)
    #     fig, ax = plt.subplots(1,2)
    #     sns.barplot(x="Hour", y = "length", data = vmt_on_demand_fetch, ax = ax[0], color = "steelblue")
    #     sns.barplot(x="Hour", y = "length", data = vmt_on_demand_fare, ax = ax[1], color = "black")

    #     for i in [0,1]:
    #         fig.set_size_inches(20,5)
    #         ax[i].set_xlabel("Hours")
    #         ax[i].set_ylabel("Vehicle Miles Traveled")
    #         ax[i].set_ylim(0,800000)
    ax.set_xlabel("Hours")
    ax.set_ylabel("Vehicle Miles per Hour")
    ax.legend(title="Driving state")
    ax.set_title("Output - Vehicle Miles Traveled by On-demand ride vehicles by driving state - {}".format(name_run))
    return ax


def get_emissions_dataframe(paths_traversals_df, legs_df):
    vmt = paths_traversals_df.loc[:, ["vehicle", "mode", "length", "departureTime"]]

    # emissions for each mode
    emissions_walk = round(
        vmt[vmt["mode"] == "walk"]["length"].apply(lambda x: x * 0.000621371 * 0).sum(), 0)
    emissions_bus = round(
        vmt[vmt["mode"] == "bus"]["length"].apply(lambda x: x * 0.000621371 * 0.259366648).sum(), 0)

    emissions_on_demand = round(
        vmt[vmt["vehicle"].str.contains("rideHailVehicle")]["length"].apply(
            lambda x: x * 0.000621371 * 0.001716086).sum(), 0)

    # Dealing with cars
    emissions_car = round(
        legs_df[legs_df["Mode"] == "car"]["Distance_m"].apply(lambda x: x * 0.000621371 * 0.001716086).sum(), 0)

    emissions = pd.DataFrame({"bus": [emissions_bus], "car": [emissions_car], "on_demand_ride": [emissions_on_demand],
                              "walk": [emissions_walk]})
    return emissions


def plot_daily_emissions_per_mode(paths_traversals_df_bau, paths_traversals_df, legs_df_bau, legs_df):
    emissions_bau = get_emissions_dataframe(paths_traversals_df_bau, legs_df_bau)
    emissions_submission = get_emissions_dataframe(paths_traversals_df, legs_df)

    emissions_both = pd.concat([emissions_bau, emissions_submission])
    emissions_both.loc[:, "Scenario"] = ["bau", "your submission"]
    emissions_both = pd.melt(emissions_both, id_vars=["Scenario"], value_vars=["bus", "car", "on_demand_ride", "walk"])

    # Plot
    fig, ax = plt.subplots()
    fig.set_size_inches(7, 5)
    sns.barplot(x="variable", y="value", data=emissions_both, hue="Scenario")

    ax.set_xlabel("Mode")
    ax.set_ylabel("Emissions [g]")
    ax.set_title("Output - Daily PM2.5 emissions per mode")
    return


class TravelTimeAccessibilityAnalysis(object):
    """Class encapsulating accessibility analysis based on BEAM linkstats.csv, physical network,
    and population file.

    Attributes
    ----------
    self.node_df: pd.DataFrame
        Network nodes representing the output of `make_node_df` function.


    """


    def __init__(self,
                 ref: ReferenceData,
                 linkstats_file: str,
                 utm_zone: str,
                 max_time: int):
        self.network_file = ref.path_network_file
        self.linkstats_file = linkstats_file
        self.population_file = ref.path_population_file
        self.utm_zone = utm_zone
        self.max_time = max_time
        self.poi_dict = self._make_poi_dict()
        self.node_df = self._make_node_df()

    def _convert_crs(self, c):
        return utm.to_latlon(c[0], c[1], int(re.match("\d*", self.utm_zone)[0]), self.utm_zone[self.utm_zone.rfind("[N|S]")])

    def _create_pandana_net(self, edges):
        """Creates a pandana network object for accessibility analysis.


        Parameters
        ----------

        edges: pd.DataFrame
            Network edges representing the output of `make_traveltime_dfs` function.

        """
        import pandana as pdna
        return pdna.Network(self.node_df.x, self.node_df.y, edges['from'], edges['to'], edges[['traveltime']])

    def _make_node_df(self):
        """Parses the physical network representation from XML and produces a dataframe of node locations

       The coordinate reference system (CRS) of the resultant coordinates must be geographic (i.e., epsg:4326).
       """

        matsimnet = open_xml(str(self.network_file)).getroot()
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


    def make_pandana_nets(self, poi_types, timeranges):
        """Creates pandana network objects for BISTRO accessibility analysis and plotting.


        Parameters
        ----------

        poi_types: list[str]
        Names of the pois that we're interested in measuring accessiblity for
        timeranges: dict[str,tuple[int]]
        Start and end times of named accessibility analysis time ranges (e.g., 'morning peak', 'evening peak')

        """

        nets = {}
        for label, timerange in timeranges.items():
            edges = self._make_traveltime_df(timerange)
            net = self._create_pandana_net(edges)
            for poi_type in poi_types:
                net.precompute(self.max_time)
                poi_locs = np.array(self.poi_dict[poi_type])
                x, y = poi_locs[:, 1], poi_locs[:, 0]
                net.set_pois(poi_type, self.max_time, 10, x, y)
                nets[label] = net
        return nets

    def _make_traveltime_df(self, timerange):
        """Compute required traveltime dataframes per time of day.

        Given the link travel times for an iteration representing a full day,
        create dataframes that clean and split out the average hourly travel times
        start and end hours defining the morning and evening peak flows over the network.

        Parameters
        ----------
        timerange: tuple[int]
            timerange for which to filter linkstats.csv.gz

        Returns
        -------
        tuple[pd.DataFrame]:
            dataframe representing link travel times over the road network

        """
        link_df = pd.read_csv(self.linkstats_file, compression='gzip')
        link_df = link_df[link_df.stat == 'AVG']
        link_df.drop(link_df.hour[link_df.hour == '0.0 - 30.0'].index, inplace=True)
        link_df.hour = link_df.hour.astype(float).astype(int)
        traveltime_link_df = link_df[link_df.hour.map(lambda x: x in timerange)].groupby('link').mean()[
            ['from', 'to', 'traveltime']]
        return traveltime_link_df

    def _make_poi_dict(self):
        # helper function to produce the POI dictionary from the population file
        population_xml = open_xml(str(self.population_file)).getroot()
        persons = population_xml.findall('person')
        poi_dict = defaultdict(list)
        for person in persons:
            for activity in person[1]:
                actType = activity.get('type').lower()
                coords = self._convert_crs([float(activity.get('x')), float(activity.get('y'))])
                poi_dict[actType].append(coords)
        return poi_dict


# def plot_accessibility_analysis(name_run, res_scenario, utm_zone, poi_types,
#                                 time_ranges, max_time, linkstats_file):
#     import geopandas as gpd
#
#     gdfs = {}
#     gdfs[name_run] = {}
#     ttaa = TravelTimeAccessibilityAnalysis(res_scenario.reference_data, linkstats_file, utm_zone, max_time)
#     nets = ttaa.make_pandana_nets(poi_types, time_ranges)
#     aggs = {}
#     for label_poi, poi_data in ttaa.poi_dict.items():
#         if label_poi not in poi_types:
#             continue
#         poi_data = np.array(poi_data)
#         x, y = poi_data[:, 1], poi_data[:, 0]
#         total_poi_avg = 0.0
#         for label_timerange, net in nets.items():
#             node_ids = net.get_node_ids(x, y)
#             net.set(node_ids)
#             a = net.aggregate(max_time, type="sum", decay="linear")
#             total_poi_avg += a
#         aggs[label_poi] = total_poi_avg / 2
#
#         gdf = gpd.GeoDataFrame(ttaa.node_df, geometry=[Point(row.x, row.y) for _, row in ttaa.node_df.iterrows()])
#
#         gdf["15min_{}".format(label_poi)] = aggs[label_poi]
#         gdf = gdf[gdf["15min_{}".format(label_poi)] > 0]
#
#         fig, ax = plt.subplots()
#         fig.set_size_inches(10, 10)
#         ax.grid(False)
#         ax.set_facecolor('k')
#         gdf.plot(markersize=5, column="15min_{}".format(label_poi), ax=ax, legend=True, vmin=0, vmax=2000,
#                  cmap='viridis')
#         gdfs[name_run] = gdf
#         ax.xaxis.set_ticks_position('none')
#         ax.yaxis.set_ticks_position('none')
#         ax.xaxis.set_ticklabels([])
#         ax.yaxis.set_ticklabels([])
#         ax.set_title(
#             "Output - Accessibility of {} locations within 15 minutes (from each node) - {}".format(label_poi,
#                                                                                                     name_run))
#         ax.axis('equal')
#
#     return gdfs
#
#
# def plot_diff(name_run, res_scenario, utm_zone, poi_types, time_ranges, max_time, linkstats_file_bau, linkstats_file, poi_diff_label):
#
#     # Collecting info from BAU
#     gdfs_bau = plot_accessibility_analysis("BAU", res_scenario, utm_zone, poi_types,
#                                 time_ranges, max_time, linkstats_file_bau)
#     gdfs_bau["BAU"]['work_diff'] = (gdfs_bau["BAU"]['15min_work'] / gdfs_bau['BAU']['15min_work']) - 1
#     gdfs_bau["BAU"]['secondary_diff'] = (gdfs_bau["BAU"]['15min_secondary'] / gdfs_bau['BAU']['15min_secondary']) - 1
#
#     # Collecting info from Submission
#     gdfs = plot_accessibility_analysis(name_run, res_scenario, utm_zone, poi_types,
#                                 time_ranges, max_time, linkstats_file)
#     gdfs[name_run]['work_diff']  = (gdfs[name_run]['15min_work'] / gdfs_bau['BAU']['15min_work']) - 1
#     gdfs[name_run]['secondary_diff'] = (gdfs[name_run]['15min_secondary'] / gdfs_bau['BAU']['15min_secondary']) - 1
#
#
#     fig, ax = plt.subplots()
#     fig.set_size_inches(10, 10)
#     ax.grid(False)
#     ax.set_facecolor('k')
#     ax.axis('equal')
#     legend = fig.legend()
#     legend.set_visible(True)
#     ax.xaxis.set_ticks_position('none')
#     ax.yaxis.set_ticks_position('none')
#     ax.xaxis.set_ticklabels([])
#     ax.yaxis.set_ticklabels([])
#     gdfs[name_run].plot(markersize=5, column="{}_dif".format(poi_diff_label), ax=ax, legend=True, vmin=-0.5,
#                            vmax=0.5, cmap='cool')
#     ax.set_title(
#         "Output - Difference in Accessibility of {} locations from BAU within 15 minutes (from each node) - {}".format(
#             poi_diff_label,
#             name_run))
#     #
#     # [plot_diff(i) for i in ["work", "secondary"]]

def plot_accessibility_analysis(sample_name, res_scenario, utm_zone, poi_types,
                                time_ranges, max_time):
    import geopandas as gpd
    import pandana as pdna

    linkstats_files = [res_scenario.reference_data.linkstats_file_bau, res_scenario.linkstats_file]
    gdfs = {}
    for name_run, linkstats_file in zip(['BAU', sample_name], linkstats_files):
        gdfs[name_run] = {}
        ttaa = TravelTimeAccessibilityAnalysis(res_scenario.reference_data, linkstats_file, utm_zone, max_time)
        nets = ttaa.make_pandana_nets(poi_types, time_ranges)
        aggs = {}
        for label_poi, poi_data in ttaa.poi_dict.items():
            if label_poi not in poi_types:
                continue
            poi_data = np.array(poi_data)
            x, y = poi_data[:, 1], poi_data[:, 0]
            total_poi_avg = 0.0
            for label_timerange, net in nets.items():
                node_ids = net.get_node_ids(x, y)
                net.set(node_ids)
                a = net.aggregate(max_time, type="sum", decay="linear")
                total_poi_avg += a
            aggs[label_poi] = total_poi_avg/2

            gdf = gpd.GeoDataFrame(ttaa.node_df, geometry=[Point(row.x, row.y) for _, row in ttaa.node_df.iterrows()])

            gdf["15min_{}".format(label_poi)] = aggs[label_poi]
            gdf = gdf[gdf["15min_{}".format(label_poi)] > 0]

            fig, ax = plt.subplots()
            fig.set_size_inches(10, 10)
            ax.grid(False)
            ax.set_facecolor('k')
            gdf.plot(markersize=5, column="15min_{}".format(label_poi), ax=ax, legend=True, vmin=0, vmax=2000,cmap='viridis')
            gdfs[name_run] = gdf
            ax.xaxis.set_ticks_position('none')
            ax.yaxis.set_ticks_position('none')
            ax.xaxis.set_ticklabels([])
            ax.yaxis.set_ticklabels([])
            ax.set_title(
                "Output - Accessibility of {} locations within 15 minutes (from each node) - {}".format(label_poi,
                                                                                                        name_run))
            ax.axis('equal')

    gdfs[sample_name]['work_diff'] = (gdfs[sample_name]['15min_work'] / gdfs['BAU']['15min_work']) - 1
    gdfs[sample_name]['secondary_diff'] = (gdfs[sample_name]['15min_secondary'] / gdfs['BAU']['15min_secondary']) - 1

    def plot_diff(poi_diff_label):
        fig, ax = plt.subplots()
        fig.set_size_inches(10, 10)
        ax.grid(False)
        ax.set_facecolor('k')
        ax.axis('equal')
        legend = fig.legend()
        legend.set_visible(True)
        ax.xaxis.set_ticks_position('none')
        ax.yaxis.set_ticks_position('none')
        ax.xaxis.set_ticklabels([])
        ax.yaxis.set_ticklabels([])
        gdfs[sample_name].plot(markersize=5, column="{}_diff".format(poi_diff_label), ax=ax, legend=True, vmin=-0.5, vmax=0.5, cmap='cool')
        ax.set_title(
            "Output - Difference in Accessibility of {} locations from BAU within 15 minutes (from each node) - {}".format(poi_diff_label,
                                                                                                    name_run))

    [plot_diff(i) for i in ["work","secondary"]]

    # gdfs['work']['work_bau'] = gdfs['work']['15min_work'] / bau_gdfs['work']['15min_work'] - 1.0
    # gdfs['secondary']['secondary_bau'] = gdfs['secondary']['15min_secondary'] / bau_gdfs['secondary'][
    #     '15min_secondary'] - 1.0



# def plot_raw_scores(raw_scores_data, name_run):
#     """
#
#     Parameters
#     ----------
#     raw_scores_data: pandas DataFrame
#
#     name_run: str
#         Name of the run , e.g. "BAU", "Run 1", "Submission"...
#
#     Returns
#     -------
#
#     """
#     raw_scores = prepare_raw_scores(raw_scores_data)
#     sns.barplot(x="Raw Score", y="Subscores", data=raw_scores, palette=['steelblue', 'steelblue', 'lightsteelblue',
#                                                                         'lightsteelblue', 'lightsteelblue',
#                                                                         'lightsteelblue', 'skyblue', 'skyblue',
#                                                                         'lightblue', 'paleturquoise'])
#     plt.yticks(fontsize=11)
#     plt.xlabel("Raw Score")
#     plt.ylabel("Score component name - {}".format(name_run))
#     plt.title("Raw Subscores", fontweight="bold", pad=12, fontsize=15)

# def plot_standardized_scores(scores_data_path, ):
#     sns.set_context('notebook')
#     sns.set_palette('Set1')
#     fig, ax = plt.subplots()
#     fig.set_size_inches(7, 5)
#
#     sc_fit = StandardScaler().fit(wide_scores.values)
#     sample1 = pd.Series(dict(zip(wide_scores.columns.tolist(), np.squeeze(
#         sc_fit.transform(wide_scores.loc[sample1_key].values.reshape(1, -1))).tolist())))
#     sample2 = pd.Series(dict(zip(wide_scores.columns.tolist(), np.squeeze(
#         sc_fit.transform(wide_scores.loc[sample2_key].values.reshape(1, -1))).tolist())))
#
#     # flip accessibility:
#     # sample1.iloc[0:2]=np.reciprocal(sample1.iloc[0:2])
#
#     std_raw_scores = pd.DataFrame({"Sample 1": sample1, "Sample 2": sample2})
#     # sns.barplot(data=std_raw_scores)
#     std_raw_scores.index.name = "Score Component"
#     std_raw_scores.columns.name = 'Sample'
#     std_raw_scores.index = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']
#     std_raw_scores.plot(kind='barh', ax=ax)
#     # plt.axvline(x=1.0,linewidth=1, color='k', ls='dashed', label = "baseline")
#     plt.xlabel("Standardized Score")
#     ax.set_title('Policy Focus: Agnostic')
#     # plt.xlim(right = 0.7,left=-0.7)
#
#     sns.despine()
#     plt.savefig('img/random_inputs/Policy Agnostic_standardized_scores.png', format='png', dpi=150, bbox_inches="tight")
#     # plt.xlim(xmax = 1.4)


