import sys
import os
import subprocess
from os import path
# To user: insert your absolute path to access the utilities folder in the Uber-Starter-Kit-Repo
sys.path.append(r"/Users/vgolfi/Documents/GitHub/Uber-Prize-Starter-Kit/utilities")
import competition_executor
from competition_executor import AbstractCompetitionExecutor, Results, _get_submission_timestamp_from_log


class GradleExecutor(AbstractCompetitionExecutor):
    """Utility to run instances of the simulation with Gradle.

    """
    def __init__(self, scenario_name, sample_size, num_iterations, input_root=path.join(os.getcwd(), "submission-inputs"),
                 output_root=path.join(os.getcwd(), "output")):
        super().__init__(input_root, output_root)
        self.scenario_name = scenario_name
        self.sample_size = sample_size
        self.num_iterations = num_iterations
        self.input_root = input_root
        self.output_root = output_root
        self.simulation_logs = None

    def run_simulation(self):
        """Launches an Uber Prize competition simulation using Gradle on a specified set of inputs.

        """
        try:
            self.simulation_logs = os.popen(
                "./gradlew run --args='--iters {0} --sample-size {1} --scenario {2}' --stacktrace".format(
                    self.num_iterations, self.sample_size, self.scenario_name)).read()
        except subprocess.CalledProcessError as e:
            raise RuntimeError("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))

        except Exception as e:
            print(str(e))

        return _get_submission_timestamp_from_log(self.simulation_logs)

    def output_simulation_logs(self):
        """Prints a specified simulation log or writes to file if filename is provided.

       Returns
       -------
       str
           Log output as bytestring

        """
        return self.simulation_logs

    def format_out_dir(self, output_root, timestamp):
        """Automatically creates the path to the output directory of the simulation.

        Parameters
        ----------
        output_root:  str
            Root directory of the simulation
        timestamp: str
            Date and time at which the output directory was created

        Returns
        -------
        : str
            path of the output directory
        """

        return path.join(output_root, self.scenario_name,
                         "{}-{}__{}".format(self.scenario_name, self.sample_size, timestamp))

    def get_submission_scores_and_stats(self, timestamp):
        """Returns two of the simulation outputs (as pandas DataFrames) for a specific simulation timestamp:
        the scores and the statistics.

        Parameters
        ----------
        timestamp: str
            date and time at which the output directory was created


        Returns
        -------
        Tuple(DataFrame,DataFrame)
            [0] summary of the raw and weighted sub-scores as well as the final score of the
            submission, and;
            [1] summary of the output stats of the submission. (see "Understanding the outputs
            and the scoring function" page of the Starter Kit for the full list of stats)
        """

        output_directory = self.format_out_dir(self.output_root, timestamp)
        results = Results(output_directory)

        stats = results.summary_stats
        scores = results.scores

        return stats, scores


if __name__ == '__main__':
    ex = GradleExecutor("sioux_faux", "1k", 1)

    # Running the simulation
    timestamp = ex.run_simulation()
    print(type(timestamp))

    # Get the logs
    print(ex.output_simulation_logs())

    # Get the output directory path
    output_directory = ex.format_out_dir(ex.output_root, timestamp)
    print("The stats and scores results were stored in the following output folder:{0}".format(output_directory))

    # Get the stats and sores
    stats, scores = ex.get_submission_scores_and_stats(timestamp)
