# BISTRO SCENARIOS OPTIMIZATION

This repo contains scrits used to run experiements on pre-defined scenarios with BISTRO and to analyse the results.

Currently, the repo contains two plug-and-play scenarios: 

* A cordon-style pricing policy that charges users a fixed amount each time they cross a predefined boundary (As currently in use in Oslo)

* A mileage based toll policy that charges drivers a per-mile amount when they drive within a defined area.

## Installing BISTRO and setting up the optimizer 

This section gives step by step instructions on how to install BISTRO, Mongodb and the hyperopt package on a clean Ubuntu distro. In order to run a BISTRO optimization at correct speeds, we recommend using at least an AWS m5a.8xlarge instance, or equivalent. This should allow for a simulation rate of about 6 Samples/hour.

1. Clone BISTRO from [Github](https://github.com/bistro-its-berkeley/BISTRO). This contains BISTRO's files and the Sioux Faux scenario.

2. Install python3 if not present, and python3-pip (`sudo apt update` and `sudo apt install python3-pip`)

3. Install hyperopt (without superuser!) : `pip3 install hyperopt`. Depending on your installation, you might need to add `~/.local/bin` to your path variable with the following command: `PATH=$PATH:absolute_path_of you_local_bin_folder`.

4. Install mongodb by following [this](https://docs.mongodb.com/manual/tutorial/install-mongodb-on-ubuntu/) tutorial.

5. Install the required python dependencies: `pip3 install docker untangle xmltodict pandas shapely pymongo`

6. Install docker: `sudo apt install docker.io`, create a docker group `sudo groupadd docker` and add yourself to it: `sudo usermod -aG docker ${USER}`. You might need to log out of your session and log back in.

The last step is to configure the number of iterations of BEAM:

7. Edit `BISTRO/fixed-data/sioux-faux/sioux_faux-15k.conf` and change the following line: `beam.agentsim.lastIteration = 100` to 30. 



## Running experiments

All pre-configured experiments are located in the optimization folder:

* Per-mile experiments can be found in `optimization/per_mile`
* Cordon-tolls experiments can be found in `optimization/cordon`

With BISTRO installed and configured, refer to each experiment's folder to get step by step instructions on how to run it. For all experiments, there are three generic steps:

1. Use the settings file to set the experiment parameters
2. Run (as super user) the file that corresponds to the desired scenario
3. Launch as many hyperopt workers as the system can run. These will run individual simulations and produce Samples.



## Analysing experiment results

Use Dashboard or my code?
