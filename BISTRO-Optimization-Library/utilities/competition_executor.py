import docker
import multiprocessing
import pandas as pd
import sys
import time
from abc import ABC, abstractmethod
from functools import wraps
from os import path

# TODO: Change to map or parameter
SCENARIO_NAME = 'sioux_faux'

SAMPLE_SIZES = ['15k', '1k']

MODE_CHOICE_CSV = "modeChoice.csv"

SUMMARY_STATS_CSV = "summaryStats.csv"

SUBMISSION_SCORES_FILE = "submissionScores.csv"

SUBMISSION_SCORES_DIR = "competition"

SCORES_PATH = ("competition", "submissionScores.csv")

IMAGE_REPOSITORY = "beammodel/beam-competition"

# TODO: Make parametric
IMAGE_TAG = "0.0.1-SNAPSHOT"

IMAGE_NAME = "{}:{}".format(IMAGE_REPOSITORY, IMAGE_TAG)


def lazy_property(fn):
    """Decorator that makes a property lazy-evaluated.
    """
    attr_name = '_lazy_' + fn.__name__

    @property
    @wraps(fn)
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)

    return _lazy_property


class Results:
    """Allow to read the results from a simulation based on its output folder.

    """

    def __init__(self,
                 output_root):
        self.output_directory = output_root

    @lazy_property
    def scores(self):
        """ Extracts the submission scores from the simulation outputs and creates a pandas DataFrame from it.

              Parses the submissionScores.csv output file containing the raw and weighted subscores, as well as the general
              score of the simulation run. Stores the result in a pandas DataFrame

              Returns
              -------
              scores: pandas DataFrame
                      Summary of the raw and weighted subscores, as well as the general score of
                      the simulation run.
              """
        output_path = path.join(self.output_directory, SUBMISSION_SCORES_DIR, SUBMISSION_SCORES_FILE)
        return pd.read_csv(output_path, index_col="Component Name")

    @lazy_property
    def summary_stats(self):
        """ Extracts the submission statistics from the simulation outputs and creates a pandas DataFrame from it.

        Reads the summaryStats.csv output file containing many of the raw output statistics of the simulation
        (see "Understanding the outputs and the scoring function" page of the Starter Kit).

        Returns
        -------
        summary_stats: pandas DataFrame
            Summary of the output stats of the submission


        """

        summary_file = path.join(self.output_directory, SUMMARY_STATS_CSV)
        summary_stats = pd.read_csv(summary_file)
        return summary_stats

    @lazy_property
    def mode_choice(self):
        """ Extracts the mode choice of agents from the simulation outputs and creates a pandas DataFrame from it.

        Reads the modeChoice.csv output file containing the distribution of agents among available transportation modes.

        Returns
        -------
        mode_choice: pandas DataFrame
            Summary of the number of users per transportaion mode.
        """
        mode_choice_file = path.join(self.output_directory, MODE_CHOICE_CSV)
        mode_choice = pd.read_csv(mode_choice_file)
        return mode_choice


class Submission(object):
    """Points to the simulation as the submission is executing and thus permits the querying of the simulation state
    as it executes within the container.

    Additionally this class summarizes the submission results of a specific simulation run.

    Parameters
    ----------
        submission_id : str
            Identifier of the simulation instance (will become the container name)
        scenario_name : str
            Which of the available scenarios will be run in the container (i.e "sioux_faux")
        input_directory : str
            Location of the input files for the simulation
        output_root :str:
            Location of the output directory for the simulation
        sample_size : str:
            Available samples size (scenario dependent, see documentation, i.e 1k)
        num_iterations: float:
            Number of iterations to run BEAM simulation engine

    """

    def __init__(self,
                 submission_id,
                 scenario_name,
                 input_directory,
                 output_root,
                 sample_size,
                 num_iterations,
                 container):
        # Delay initialization in order to get timestamp
        time.sleep(10)
        log = container.logs()
        self._submission_id = submission_id
        self._timestamp = _get_submission_timestamp_from_log(log.decode('utf-8'))
        self.num_iterations = num_iterations
        self.sample_size = sample_size
        self.scenario_name = scenario_name
        self.input_directory = input_directory
        self._container = container

        self.output_directory = self._format_output_directory(output_root)

        self.results = Results(self.output_directory)

    @lazy_property
    def id(self):
        return self._container.short_id

    @lazy_property
    def name(self):
        return self._container.name

    def logs(self):
        return self._container.logs()

    def stop(self):
        self._container.stop()

    def remove(self):
        self._container.remove()

    def status(self):
        self._container.update()
        return self._container.status

    def reload(self):
        self._container.reload()

    def _format_output_directory(self, output_root):
        """Automatically creates the path to the output directory of the simulation.

        Parameters
        ----------
        output_root: str
            root directory of the simulation

        Returns
        -------
        :str
            path of the output directory

        """
        return path.join(output_root, self.scenario_name,
                         "{}-{}__{}".format(self.scenario_name, self.sample_size, self._timestamp))

    def score(self):
        """ Extracts the submission scores from the simulation outputs and creates a pandas DataFrame from it.

        Parses the submissionScores.txt output file containing the raw and weighted subscores,
        as well as the general score of the simulation run. Stores the result in a pandas DataFrame

        Returns
        -------
        all_scores : pd.DataFrame
            summary of the raw and weighted subscores, as well as the total score of the simulation run.

        """
        return self.results.scores

    def summary_stats(self):
        """ Extracts the submission statistics from the simulation outputs and creates a pandas DataFrame from it.

        Reads the summaryStats.csv output file containing many of the raw output statistics of the simulation
        (see "Understanding the outputs and the scoring function" page of the Starter Kit).

        Returns
        -------
         DataFrame:
            Summary of the output stats of the submission

        """

        return self.results.summary_stats

    def is_complete(self):
        """ Checks if the submission is complete.

        Returns
        -------
        bool
            True if the simulation is complete, False otherwise.

        """

        path_submission_scores = path.join(self.output_directory, SUBMISSION_SCORES_DIR, SUBMISSION_SCORES_FILE)
        return path.exists(path_submission_scores)

    def __str__(self):
        return "Submission_id: {}\n\t Scenario name: {}\n\t # iters: {}\n\t sample size: {}".format(self._submission_id,
                                                                                                    self.scenario_name,
                                                                                                    self.num_iterations,
                                                                                                    self.sample_size)


def verify_submission_id(func):
    """Checks that the container id exists in the CompetitionContainerExecutor object."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        self, submission_id = args
        if submission_id not in self.containers:
            raise ValueError("Container not executed using this interface.")
        else:
            return func(*args, **kwargs)

    return wrapper


def _get_submission_timestamp_from_log(log):
    """Parses the logs (as a str) of a container to find the precise time at which the output directory was
    created.

    """

    lines = log.split('\n')
    for line in lines:
        if 'Beam output directory is' in line:
            words = line.split(' ')
            output_dir = words[-1]
            timestamp = output_dir.split('/')[-1].split('__')[-1]
            return timestamp
    else:
        raise ValueError("No timestamp found for submission. Error running submission!")


class AbstractCompetitionExecutor(ABC):
    """ Factors the common methods used by subclasses running instances of the simulation with different
    executors (e.g. Docker, Gradle...)

    """

    def __init__(self, input_root=None,
                 output_root=None):
        super().__init__()
        self.input_root = input_root
        self.output_root = output_root

    def save_inputs(self, input_dictionary, submission_input_root=None):
        """ Save the contestant's inputs into csv files that can be read by the simulation.

         The dictionary should be structured as follows:
        - "VehicleFleetMix": Bus fleet mix DataFrame
        - "ModeSubsidies": Subsidies DataFrame
        - "RoadPricing": Road Pricing DataFrame
        - "FrequencyAdjustment": Frequency Adjustment DataFrame
        - "MassTransitFares": Mass Transit (buses) Fares DataFrame

        The content of the different DataFrames can be understood by refering to the `Uber-Prize-Starter-Kit` repository
        documentation (`docs/Which-inputs-should-I-optimize.ms`)

        Parameters
        ----------
        input_dictionary : dictionary
            maps data_name (key) to DataFrame (value)

        """
        input_root = self.input_root

        list_inputs = ["VehicleFleetMix", "ModeSubsidies", "FrequencyAdjustment", "MassTransitFares"]

        if input_root is None:
            if submission_input_root is not None:
                input_root = submission_input_root
            else:
                raise ValueError(
                    "No input location specified. One must be provided by default on object"
                    " instantiation or supplied to this method as an argument")

        for input_name, input_dataframe in input_dictionary.items():
            if input_name not in list_inputs:
                raise KeyError("{0} is not a valid key for `input_dictionary`.".format(input_name))

            input_dataframe.to_csv(path.join(input_root, input_name + ".csv"), index=False)

    @abstractmethod
    def get_submission_scores_and_stats(self, *args, **kwargs):
        pass

    @abstractmethod
    def output_simulation_logs(self, *args, **kwargs):
        pass

    @abstractmethod
    def run_simulation(self, *args, **kwargs):
        pass


class CompetitionContainerExecutor(AbstractCompetitionExecutor):
    """Utility to run (potentially many) instances of the simulation.

    Pointers to docker-py container objects executed by this utility are cached on the field
    self.containers under the name specified in the self.run(...) method. Convenience methods on this class can be
    used to simplify interaction with one or many of these containers.

    Parameters
    ----------
    input_root : str
        a permanent input file directory, i.e., /submission-inputs
        (if you expect not to feed this in manually; see run method below).
    output_root : str
        a permanent output file directory (it's a good idea to set this,
        else you will need to do so for every container you create)

    """

    def __init__(self, input_root=None,
                 output_root=None):
        super().__init__(input_root, output_root)
        self.client = docker.from_env()
        self.containers = self.find_existing_simulation_containers()

    def find_existing_simulation_containers(self):
        all_containers = self.client.containers.list(all=True)
        if all_containers is not None:
            return {c.name: c for c in self.client.containers.list(all=True) if c.image.tag('beammodel/beam_competition:0.0.1-SNAPSHOT')}
        else:
            return {}


    def list_running_simulations(self):
        """Queries the run status for executed containers cached on this object in turn
        (updating their statuses as appropriate).

        Returns:
            a list of running containers

        """
        running = []
        for name, container in self.containers.items():
            container.reload()
            if container.status == 'running':
                running.append(name)
        return running

    @verify_submission_id
    def find_last_completed_simulation_path(self, submission_id):
        lines = self.output_simulation_logs(submission_id).decode("utf-8").split("\n")

        for line in lines:
            if "Beam output directory is" in line:
                words = line.split(' ')
                output_dir = words[-1]
                timestamp = output_dir.split('/')[-1].split('__')[-1]
                # assumes simulation params stay the same
                simulation_output_root = path.join(self.output_root, SCENARIO_NAME,
                                                   "{}-{}__{}".format(SCENARIO_NAME, SAMPLE_SIZES[0], timestamp))
                score_path = path.join(simulation_output_root, "competition", "submissionScores.csv")
                if score_path is not None and path.exists(path):
                    return score_path
                else:
                    # don't keep going... there is nothing else to find here.
                    break

        return "Simulation run not completed!"

    @verify_submission_id
    def get_submission_scores_and_stats(self, submission_id):
        """ Returns two of the simulation outputs (as pandas DataFrames) for a specific submission ID:
        the scores and the statistics.


        Parameters
        ----------
        submission_id : str
            The unique identifier for the submission

        Returns
        -------
        Tuple(DataFrame,DataFrame)
            [0] Summary of the raw and weighted sub-scores as well as the final score of the
            submission, and;
            [1] summary of the output stats of the submission. (see "Understanding the outputs
            and the scoring function" page of the Starter Kit for the full list of stats)

        Raises
        ------
        ValueError
            The scores do not exist yet i.e the simulation is still running.

        """

        submission = self.containers[submission_id]

        if submission.is_complete():
            scores = submission.results.scores
            stats = submission.results.summary_stats

            return scores, stats
        else:
            raise NameError("Simulation {0} is still running.".format(submission_id))

    def stop_all_simulations(self, remove=True):
        """Stops all simulations. By default, containers are removed (both from this object and the docker daemon).

        `Remove=True` frees the names that were used to execute containers previously, so it's generally a good
        idea to remove if you plan to reuse names.

        Parameters
        ----------
        remove : bool, optional
            Whether to remove the containers cached on this object.

        """
        if len(self.containers.values()) == 0:
            print("WARNING: No simulations currently running!")
        for container in self.containers.values():
            print("Stopping simulation:\n {}".format(container))
            container.stop()
            print("Done.")
            if remove:
                container.remove()
        self.containers.clear()

    def pull(self, stream=True, decode=True):
        """Pulls the appropriate image for the competition round.

        Instantiates the low-level client to do this task.
        The tag is defined by the round of the competition and the version, which is
        fixed (w/r/t this API). Uses docker.py low-level API.

        Parameters
        ----------
        stream : bool
            Stream the output as a generator. Make sure to consume the generator,
            otherwise pull might get cancelled.
        decode: bool
             Decode the JSON data from the server into dicts. Only applies with stream=True

        Returns
        -------
            generator or str
                Output of API call
        """
        # TODO[saf] Will be dependent on round/version. Will need to parametrize once naming scheme decided.
        # TODO[saf] Add method to check if newer image is available and give user option if desired to
        #           download.
        apiclient = docker.APIClient()
        for line in apiclient.pull(repository=IMAGE_REPOSITORY, tag=IMAGE_TAG, stream=True, decode=True):
            print(json.dumps(line, indent=4))
        return self.client.images.pull(repository=IMAGE_REPOSITORY, tag=IMAGE_TAG,
                                       stream=stream, decode=decode)

    @verify_submission_id
    def output_simulation_logs(self, sim_name, filename=None):
        """Prints a specified simulation log or writes to file if filename is provided.


        Parameters
        ----------
        sim_name : str
            Name of the the requested simulation
        filename : str, optional
            A path to which to save the logfile

        Returns
        -------
        str
            Log output as bytestring

        """

        logs = self.containers[sim_name].logs().decode('utf-8')
        if filename is None:
            print(logs)
        else:
            with open(filename, 'w') as f:
                f.write(logs)
        return logs

    @verify_submission_id
    def check_if_submission_complete(self, sim_name):
        """ Checks if a given submission is complete.

        Parameters
        ----------
        sim_name : str
            identifier of the simulation instance

        Returns
        -------
        bool :
            True if the given simulation is complete, False otherwise


        """
        return self.containers[sim_name].is_complete()

    def run_simulation(self,
                       submission_id,
                       submission_output_root=None,
                       submission_input_root=None,
                       scenario_name=SCENARIO_NAME,
                       sample_size=SAMPLE_SIZES[0],
                       num_iterations=1,
                       num_cpus=multiprocessing.cpu_count() - 1,
                       mem_limit="4g"):
        """Creates a new container running an Uber Prize competition simulation on a specified set of inputs.

        Containers are run in a background process (detached mode), so several containers can be run in parallel
        (though this is a loose and uncoordinated parallelism and is very experimental! Future updates are
        planned to scale execution out over compute nodes).

        This utility adds the container to the list of containers managed by this object.

        Parameters
        ----------
        submission_id : str
            Identifier of the simulation instance (will become the container name)
        submission_output_root : str
            The (absolute) path to locate simulation outputs
        submission_input_root : str
            The (absolute) path where simulation inputs are located
        scenario_name : str
            Name of the current scenario (e.g., "sioux_faux")
        sample_size : str
             The available sample size (scenario dependent, see documentation).
        num_iterations : int
            Number of iterations for which to run the BEAM simulation engine.
        num_cpus : float
            Number of cpus to allocate to container (multiprocessing.cpu_count()-1 by default).
            (not currently used).
        mem_limit : int
            Adds a maximum memory constraint to execution. Concretely, sets the Java parameter -Xmx{}.

        Raises
        ------
        ValueError
            If the output location or input location are nowhere specified (either here on object instantiation).

        """
        output_root = self.output_root
        input_root = self.input_root

        if output_root is None:
            if submission_output_root is not None:
                output_root = submission_output_root
            else:
                raise ValueError(
                    "No output location specified. One must be provided by default "
                    "on object instantiation or supplied to this method as an argument.")

        if input_root is None:
            if submission_input_root is not None:
                input_root = submission_input_root
            else:
                raise ValueError(
                    "No input location specified. One must be provided by default "
                    "on object instantiation or supplied to this method as an argument.")

        container = self.client.containers.run(IMAGE_NAME,
                                               cpu_count=num_cpus,

                                               name=submission_id,
                                               command=r"--scenario {0} --sample-size {1} --iters {2}".format(
                                                   scenario_name, sample_size, num_iterations),
                                               detach=True,
                                               volumes=
                                               {output_root: {"bind": "/output", "mode": "rw"},
                                                input_root: {"bind": "/submission-inputs",
                                                             "mode": "ro"}})

        self.containers[submission_id] = Submission(submission_id,
                                                    scenario_name,
                                                    input_root,
                                                    output_root,
                                                    sample_size,
                                                    num_iterations,
                                                    container)


if __name__ == '__main__':
    # Example to demonstrate/test usage. Not a production script. For more detailed explanations, read the API-tutorial
    # Jupyter Notebook in the Starter-Kit repository.

    # Ensure docker is running before using this module!

    CONTAINER_ID = 'uber1'

    # Must use absolute paths here
    ex = CompetitionContainerExecutor(input_root=sys.argv[1],
                                      output_root=sys.argv[2])

    print("Running Container")

    try:
        uber = ex.client.containers.get(CONTAINER_ID)
        uber.stop()
        uber.remove()
        print("Found container from previous run, removing and creating new sim container...")
    except docker.errors.NotFound:
        print("Creating new simulation container...")

    ex.run_simulation(CONTAINER_ID, num_iterations=1, num_cpus=2, sample_size='15k')

    # Let it roll for a bit (hopefully at least one or two iterations!)
    if len(sys.argv) < 4:
        print("Running simulation for 40 seconds...")
        time.sleep(40)
    else:
        run_time = int(sys.argv[3])
        print("Running simulation for {} seconds...".format(str(run_time)))
        time.sleep(int(run_time))

    ex.output_simulation_logs(CONTAINER_ID)

    # Good idea to call this at the end of any run to clean up containers (particularly if you want to reuse names)!
    ex.stop_all_simulations()
