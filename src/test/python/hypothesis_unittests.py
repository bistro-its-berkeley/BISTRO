import sys
sys.path.append(r"/Users/vgolfi/Documents/GitHub/BeamCompetitions/src/main/python/run")
from gradle_executor import GradleExecutor
from .inputs_unittests import change_vehicle_fleet_mix
import unittest
from competition_executor import Results


def run_simulations_change_in_vehicle_fleet_mix():
    """Runs the simulations for all inputs necessary to test consequences of changes in the vehicle fleet mix.

    Returns
    -------
    list_results : list of objects instantiations from the `Results` class

    """
    # Creates an instantiation o the GradelExecutor class
    gradle_executor = GradleExecutor("sioux_faux", "1k", 1)

    # Gathers the input sets to be compared
    input_sets_list = change_vehicle_fleet_mix()

    # Saves the input sets, runs the corresponding simulations and extracts the paths of the output folders containing
    # the results of all run simulations
    results_directories = gradle_executor.run_pipeline(input_sets_list)

    list_results = [Results(path_output_dir) for path_output_dir in results_directories]
    return list_results


class ChangeVehicleFleetMix(unittest.TestCase):
    """Gathers all hypothesis methods related to change in the bus fleet composition that we want to test.

    Returns
    -------
    "OK" statement if all tests were verified.
    Error message if at least one test failed.

    """

    def __init__(self, *args, **kwargs):
        super(ChangeVehicleFleetMix, self).__init__(*args, **kwargs)
        self.list_results = run_simulations_change_in_vehicle_fleet_mix()

    def test_more_fuel_consumed_by_bigger_buses(self):
        """Ensures that larger buses consume more fuel.

        """

        # Getting fuel consumed from last iteration
        diesel_consumed = [result.summary_stats.loc[len(self.list_results) - 1, "fuelConsumedInMJ_Diesel"] for
                           result in self.list_results]
        self.assertTrue(diesel_consumed[0] > diesel_consumed[1])


if __name__ == '__main__':
    unittest.main()
