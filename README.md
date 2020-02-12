# BISTRO
The Berkeley Integrated System for Transportation Optimization is being developed as an an open source collaborative transportation planning decision support system to assist stakeholders in addressing the increasingly complex complex problems arising in transportation systems worldwide. BISTRO uses an agent-based simulation and optimization approach to anticipate and develop adaptive strategies fo potential technological disruptions and growth scenarios. 

BISTRO uses the [BEAM](https://beam.readthedocs.io/en/latest/index.html) (the Behavior, Energy, Autonomy, and Mobility) framework for agent-based simulation to enable the optimization of transportation system interventions based on the emergent behavior of a synthetic population of individual travelers that exhibit sensitivity to cost and time factors of the transportation system. 

[Read more about BISTRO.](https://bistro.its.berkeley.edu)


## Introduction


*Software Requirements*:

Run via Docker (Recommand):
- [Docker](https://www.docker.com).

You can find the instructions to install Docker for Mac [here](https://docs.docker.com/docker-for-mac/install/#install-and-run-docker-for-mac) and for Windows [here](https://docs.docker.com/docker-for-windows/install/). See [www.get.docker.com](http://get.docker.com) for an automated Linux installation. 

Thus, the code is OS-agnostic.

Note that some of the provided utility scripts require a python installation with the [docker-py](https://docker-py.readthedocs.io/en/stable/) package installed as well as some other [requirements](/requirements.txt). Please run `pip install docker` prior to running the scripts.

Run via IntelliJ:
- [IntelliJ](https://www.jetbrains.com/idea/).

**Note:** the most recent IDE does not support current BISTRO, you can download version 2019.1

You can find the instructions to install IntelliJ [here](https://www.jetbrains.com/idea/download).

*Hardware Requirements and Performance Considerations*:

There are no strict hardware requirements; however, performance will increase substantially with more CPUs (as well as, to some extent, more memory). At a bare minimum, we recommend 8GB RAM and 4 CPUs. Initial observations for the sioux faux 15k sample on the minimum hardware clock in at ~49s/iteration. 
We recommend use of computers or Amazon EC2 instances with at least 8 CPUs and at least 32 GB of RAM. As for sf light(urbansim), with accessibility on, we don't recommend run it locally. We recommend Amazon EC2 instances with 48 CPUs, 192 GB of RAM and at least 30 GB of storage to get the best performance.



## Running the Simulation

This repository is organized according to the following directories:
* `/src`: source code,
* `/fixed-data`: fixed input data, and
* `/submission-inputs`: example submissions.

## Requirements

For execution:
- [Docker](https://www.docker.com) (Recommend)
- [IntelliJ](https://www.jetbrains.com/idea/)

Additional requirements for development:
- Java 8
- Scala 2.12

## Functionality and Design

For every change in the set of inputs provided by contestants, executing beam.competition.RunCompetition completes
the following three steps in sequence:

1. Validation of inputs, fail-fast error-reporting, and cost computation
2. Submission evaluation using the simulator
3. Scoring of submissions, organization of diagnostic outputs, and (tbd) communication with vendor API

Each `Input` entity has an associated `InputDataHelper[T<:Input]` responsible for parsing data in the corresponding `${pwd}submission-inputs/${input-type}.csv`
file and performing associated validation-related tasks.
** Note: This version of code and docker image don't support FrequentAdjustment.csv**

Scoring functions are either "Simple" or "Compound". In the case of a `Simple` score, they are read a single field from the `summaryStatsFile.csv` from the
business as usual (BAU) folder for the associated scenario (provided with this library or available by request) as well as the `summaryStatsFile.csv` from the
submission outputs, taking the weighted (according to the corresponding field in `${pwd}/fixed-data/ difference between BAU and the submission values. "Compound" scores add some number of component statistics together before taking the weighted difference. The sum of all scoring components is then taken as the final score.

## [Docker](https://www.docker.com/) Container Management and Execution

The wrapper around `BISTRO` has a Docker image on [Docker Hub](https://hub.docker.com/) with tag `beammodel/beam-competition:0.0.3-SNAPSHOT` (sioux faux specific), `beammodel/beam-competition:0.0.4.1-SNAPSHOT` (no accessibility enabled) and `beammodel/beam-competition:0.0.4.2-SNAPSHOT` (accessibility enabled).

This section details how administrators can manage and execute this image via the Docker toolkit.

### Build and Deploying

Updating the BISTRO image requires collaborator access to the `beammodel` DockerHub repository. Please contact sid.feygin@berkeley.edu to inquire about getting credentials.

To re-create the `BISTRO` image from the latest version of `BISTRO`, use the
[`gradle-docker-plugin`](https://github.com/bmuschko/gradle-docker-plugin) as follows:

    > gradle dockerBuildImage

To push the image please define your DockerHub credentials first and add
`DOCKER_USER` and `DOCKER_PASSWORD` to your env. From a `bash`
session in the root folder, `/` of this repository, run 

    > export DOCKER_USER=<Your DockerHub username>
    > export DOCKER_PASSWORD=<Your DockerHub password>

and then run

    > gradle dockerPushImage

to push the image to DockerHub.

**Note to Windows users**: you may need to expose the Docker daemon to tcp://localhost:2735 without TLS ( Settings>General and check the appropriate box ), see spotify/docker-maven-plugin#351.

### Running a Simulation Locally

Once built and pushed, the container is ready to be executed.

**Notes to Windows users** 
- You will need to execute the following from PowerShell.
- If you get a file not found exception, then you may need to add a shared folder
  1. `docker-machine stop`
  2. `VBoxManage sharedfolder add default --name /BISTRO --hostpath <absolute_path_to>\BISTRO --automount`
     - Or add from the VirtualBox UI from the VM's Settings
     - `--readonly` can be added if desired
  3. `docker-machine start`
  4. Now instead of using the absolute path you can use `/BISTRO` as the starting point in the below `-v` argument

To run a container based on the image containing the BISTRO framework, users need to specify the submission folder and output folder and then run the following command (subsititute <x> as appropriate, keeping in mind that there are sample submission inputs in the root of this repo i.e., `/submission-inputs`). For example, you may run

`docker run -v <absolute_path_to_submission_inputs>:/submission-inputs:ro -v /home/ubuntu/BISTRO/fixed-data:/fixed-data:rw -v <path_to_output_root>:/output:rw beammodel/beam-competition:0.0.4.2-SNAPSHOT --config fixed-data/sf_light/urbansim-25k.conf`

to execute the sf light scenario with accessibility KPI enabled based on urbansim-25k.conf file. You can change your basic inputs such as number of iterations through conf files. 

You may also run `docker run -v <absolute_path_to_submission_inputs>:/submission-inputs:ro -v <path_to_output_root>:/output:rw beammodel/beam-competition:0.0.1-SNAPSHOT --scenario siouxfaux --sample-size 15k --iters 10`

to execute the 15k Sioux Faux scenario for 10 iterations. `sample-size` can be `1k` if you need to debug a smaller, simpler dataset.


_Note_: To those unfamiliar with the `docker run` command, `-v` binds a local volume (the `.../submission-input` directory, say) to a volume inside the container, which is what follows the `:` (e.g., `/submission-input`). The `ro` or `rw` flags indicate if the directory is to be bound as read-only or write-only, respectively.

If desired, users may pass Java Virtual Machine (JVM) attributes and add JAVA_OPTS `env` arguments to the `docker run` command. For example,
`docker run -it --memory=4g --cpus=2 -v <absolute_path_to_submission_inputs>:/submission-inputs:ro -v <path_to_output_root>/output:/output:rw -e JAVA_OPTS='"-Xmx4g" "-Xms2g"' beammodel/beam-competition:0.0.1-SNAPSHOT --scenario siouxfaux --sample-size 15k --iters 10`

sets the memory used by docker instance to 4 GB and uses 2 cpus. BISTRO, in fact, uses _ncpu_-1 for each run, where _ncpu_ is the number of CPUs available on the host machine (virtual or otherwise). While this is sensible for a single run on
one machine, it is not very useful for multiple runs (one CPU is left to run background processes in order to avoid freezing the system).

### Shell Script (Linux/Mac only) for Sioux Faux scenario

For convenience, the `docker run` command is wrapped by a bash script, `competition.sh`.

To run the script, users may enter, for example, `./competition.sh -m 4g -c 2 -s sioux_faux -sz 15k -n 10 -i <absolute_path_to_submission-inputs>`, where

* `-m` is the memory limit
* `-c` is the number of CPUs
* `-s` is the scenario name
* `-sz` is the sample size
* `-n` is the number of BEAM iterations
* `-i` is the input folder path

_Reminder_: Substitute `<path_to_submission-inputs>` as appropriate.

An example run with existing data can be run like so:

```bash
./competition.sh -m 4g -c 2 -s sioux_faux -sz 1k -n 1 -i ../submission-inputs/
```

*Note:* When you run the simulation again via the competition script, you will have to delete the container created via the previous `./competition.sh` run. You can do so with `sudo docker rm <container id>`, after looking up the <container id> via `sudo docker ps | grep beam-competition`

## Running with IntelliJ

### GIT-LFS Configuration
The installation process for git-lfs client(v2.3.4, latest installer has some issue with node-git-lfs) is very simple. For detailed documentation please consult github guide for Mac, windows and Linux.

To verify successful installation, run following command:

```$ git lfs install```
to confirm that you have installed the correct version of client run the following command:

```$ git lfs env```
will print out the installed version, and please make sure it is git-lfs/2.3.4.

To update the text pointers with the actual contents of files, run the following command (if it requests credentials, use any username and leave the password empty):

```$ git lfs pull```

### Installing git lfs on windows :

With Git LFS windows installation, it is common to have the wrong version of git-lfs installed, because in these latest git client version on windows, git lfs comes packaged with the git client.

When installing the git client one needs to uncheck git lfs installation. If mistakenly you installed git lfs with the git client, the following steps are needed to correct it (uninstalling git lfs and installing the required version does not work…):

* Uninstall git
* Install the git client (uncheck lfs installation)
* Install git lfs version 2.3.4 separately

Another alternative to above is to get the old git-lfs.exe from the release archives and replace the executable found in

*[INSTALL PATH]\mingw6\bin* and *[INSTALL PATH]\cmd*, where the default installation path usually is *C:\Program Files\Git*

###Installing BISTRO   
Clone the beam repository:

```git clone git@github.com:<xxx>/BISTRO.git```

Change directories into that repository:

```cd BISTRO```

Fetch the remote branches and tags: 

```git fetch```

###Running on IntelliJ IDE

####Importing BISTRO project into IDE
Once the IDE is successfully installed, proceed with the below steps to import BISTRO into the IDE.
1. **Open the IDE and agree to the privacy policy and continue**
    1. (Optional) IDEA walks you through some default configurations set up here . In case you want to skip these steps , choose “Skip and install defaults” and go to step 2
        1. Select a UI theme of choice and go to Next: Default Plugins
        2. Select only the required plugins (gradle , java are mandatory) and disable the others and go to Next:Feature plugins
        3. Install scala and click “Start using Intellij IDEA”
   
2. In the welcome menu , select “Import Project” and provide the location of the locally cloned BISTRO project
3. Inside the import project screen, select “Import project from external model” and choose “Gradle” from the available and click Next
4. Click Finish.


The project should now be successfully imported into the IDE and a build should be initiated automatically. If no build is triggered automatically , you can manually trigger one by going to Build > Build Project.
  
  **Installing scala plugin**
  
  If optional configuration in step 1 of above section was skipped , scala plugin will not be added automatically . To manually enable scala plugin go to File > Settings > Plugins. Search for scala plugin and click Install.
  
  **Setting up scala SDK**
  
  Since BEAM is built with java/scala . A scala sdk module needs to be configured to run BEAM. Check the below steps on how to add a scala module to IDEA * Go to File > Project Settings > Global Libraries * Click + and select Scala SDK * Select the required scala SDK from the list , if no SDK found click Create. * Click “Browse” and select the scala home path or click “Download” (choose 2.12.x version)
  
  **Running BISTRO from IDE**
  
  BEAM requires some arguments to be specified during run-time like the scenario configuration. These configuration settings can be added as a run configuration inside the IDE.
  
  Steps to add a new configuration :
  
  - Go to Run > Edit Configurations
  - Click + and from the templates list and select “Application”
  - Fill in the following values
    - Main Class : beam.competition.run.RunCompetition
    - VM options : -Xmx8g
    - Program Arguments : –config test/input/beamville/beam.conf (this runs beaamville scenario, changes the folder path to run a different scenario)
    - Working Directory : /home/BISTRO
    - use submodule of path : competitions.main
  - Click Ok to save the configuration.
  
  To add a configuration for a different scenario , follow the above steps and change the folder path to point to the required scenario in program arguments



## Contributing

We always welcome bug reports and enhancement requests from both competitors as well as developers on the BISTRO team and elsewhere. Guidelines and suggestions on how to contribute code to this repository may be found in [./github/CONTRIBUTING.md](./github/CONTRIBUTING.md].

