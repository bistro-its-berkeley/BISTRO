# PER-MILE OPTIMIZATION SCENARIO

## Description

Drivers are charged a fixed amount per mile when they drive within a certain area. This area has a circular shape. The search space for the exeriment contains four variables:

* center_x : x coordinate of the circle's center
* center_y : y coordinate of the circle's center
* radius : circle's radius
* price : price per mile (in $) when driving within the area.

## Optimization

This scenario has two different optimization files:

* Random search: Randomly selects points from the search space and runs the simulation with those input parameters.

* Bayesian optimization: Uses Tree Parzen Estimators to select points that have a better chance of optimizating user-defined key performance indicators.

### Running a random search

TBA


### Running baysesian optimization

#### Defining an optimization metric

*What are we optimizing?* BEAM automatically produces 9 KPIs (key performance indicators) that the user can mix to reach their performance objective. The different KPIs are:

* `averageVehicleDelayPerPassengerTrip` stores the average delay experienced by people used motorized vehicles.
* `VMT` (vehicle miles traveled) counts the total number of miles traveled using motorized vehicles
* `averageTravelCostBurden_Work` counts the average amount of money spent on work related trips. This includes gas, tolls, and the perceived  value of time of the individual.
* `averageTravelCostBurden_Secondary` counts the average amount of money spent on non-work related trips. This also includes gas, tolls, and perceived value of time.
* `busCrowding` records the average crowding of buses and public transportation.
* `costBenefitAnalysis` indicates the average benefit of the city for each dollar invested.
* `sustainability_GHG` records the total amount of Greenhouse gaz emitted in 24 hours.
* `sustainability_PM` records the total amount of particles emitted in 24 hours.
* `TollRevenue` counts the total amount of tolls collected in the day.

Before running any optimization, the user should define what their priority is and define a weighted sum of KPIs that reflects this priority. This can be done by editing the `optimization_kpi.py` file in this folder. 

__/!\\__ Since KPIs have very different ranges, the optimizer standadizes them. To do so, it uses a `standardizationParameters.csv` file that contains the average value of the KPI and its standard deviation, both computed over a random collection of samples of this scenario, acquired using random search. This file comes pre-computed with the experiment and can be found in the settings file, but you can run your own random search or edit it manually it you desire.

#### Running the optimization

Once this is done, the user should edit the `settings.yaml` file. It contains an overview of the optimization hyperparameters. 

Once these steps are covered, the optimization can start. The hyperopt library that we use allows for a flexible number of samples to be evaluated at the same time unsing individual 'workers'. For each of these workers, you will need a new terminal window. We recommend using `screen` to manage them, especially if operating on a remote computer.

1. Start the docker and mongodb services by typing `sudo service mongod start` and `sudo service docker start`.

2. Launch the optimization master with `sudo python3 bayesian_optimization_per_mile`

3. For each worker, follow these steps:
	- Open a new terminal window
	- Navigate to the output folder of your experiment (/!\\ see common problems)
	- Run `hyperopt-mongo-worker --mongo=localhost:27017/wh_db_circle --poll-interval=0.1`. The worker will automatically connect to the master and evaluate a new sample

__Voilà__, your experiment is running. It will run until it has evaluated the number of samples defined in the settings file. If you want to stop it prematurely, you can simply enter `CTRL + C` in the master terminal. The workers will finish running their experiments and stop on their own. You can also stop the workers manually, but you will get incomplete output folders.

To generate graphs of the experiment's output, see the analysis folder.

### Common problems

* Disk memory: Optimization samples are very memory heavy (About 1.6 GBs for a 30 iterations sample). This is due to BISTRO saving a lot of intermediate information. For most purposes, this information is not needed and can be safely discarded. In the output folder of each sample, there is an `ITERS` directory. The contents of this directory can be deleted and will considerably the space taken by one iteration (to about 50MB)

* Workers have access permission problems: this can happen on some systems, we're working on fixing that bug. Starting your *hyperopt-mongo-worker* in another folder should solver the problem.
