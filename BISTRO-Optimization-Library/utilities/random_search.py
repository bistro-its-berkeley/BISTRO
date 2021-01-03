import logging
import os
import tempfile
from pathlib import Path

import docker
import numpy as np
import pandas as pd

import input_sampler as sampler

AGENCY = "sioux_faux_bus_lines"
SCENARIO_NAME = "sioux_faux"
DOCKER_IMAGE = "beammodel/beam-competition:0.0.1-SNAPSHOT"

CMD_TEMPLATE = "--scenario {0} --sample-size {1} --iters {2}"
DIR_DELIM = "-"

FREQ_FILE = "FrequencyAdjustment.csv"
SUB_FILE = "ModeSubsidies.csv"
FLEET_FILE = "VehicleFleetMix.csv"
MASS_TRANSIT_FILE = "MassTransitFares.csv"
SCORES_PATH = ("competition", "submissionScores.csv")

logger = logging.getLogger(__name__)


def abspath2(path):
    path = os.path.abspath(os.path.expanduser(path))
    return path


def only_subdir(path):
    subdir, = os.listdir(path)  # Validates only returned element
    path = os.path.join(path, subdir)
    return path


def docker_exists(container_id, client):
    try:
        client.containers.get(container_id)
    except docker.errors.NotFound:
        return False
    return True


def sample_settings(max_num_records, data_root):
    # TODO pull out data GTFS stuff to make this pure function
    agency_dict = sampler.scenario_agencies(Path(data_root), SCENARIO_NAME)
    sf_gtfs_manager = sampler.AgencyGtfsDataManager(agency_dict[AGENCY])

    samplers = [sampler.sample_frequency_adjustment_input,
                sampler.sample_mode_incentives_input,
                sampler.sample_vehicle_fleet_mix_input,
                sampler.sample_mass_transit_fares_input]

    samples = []
    for input_sampler in samplers:
        num_records = np.random.randint(0, max_num_records)
        samples.append(input_sampler(num_records, sf_gtfs_manager))

    return tuple(samples)


def save_inputs(input_dir, freq_df=None, mode_incentive_df=None, vehicle_fleet_mix_df=None, pt_fare_df=None):
    if freq_df is not None:
        freq_df.to_csv(os.path.join(input_dir, FREQ_FILE), header=True, index=False)
    if mode_incentive_df is not None:
        mode_incentive_df.to_csv(os.path.join(input_dir, SUB_FILE), header=True, index=False)
    if vehicle_fleet_mix_df is not None:
        vehicle_fleet_mix_df.to_csv(os.path.join(input_dir, FLEET_FILE), header=True, index=False)
    if pt_fare_df is None:
        pt_fare_df = pd.read_csv('../submission-inputs/{0}'.format(MASS_TRANSIT_FILE))
    pt_fare_df.to_csv(os.path.join(input_dir, MASS_TRANSIT_FILE), header=True, index=False)



def read_scores(output_dir):
    """Read scores from output directory as .csv file.
    """
    output_dir = only_subdir(only_subdir(output_dir))
    df = pd.read_csv(os.path.join(output_dir, *SCORES_PATH), index_col="Component Name")
    scores = df["Weighted Score"]
    return scores


def search_iteration(docker_cmd, data_root, input_root, output_root):
    max_records = 10

    client = docker.from_env()  # TODO consider if cleanest that this is in main?

    assert os.path.isabs(data_root)
    assert os.path.isabs(input_root)
    assert os.path.isabs(output_root)

    # Make temp dirs, race condition safe too
    input_dir = tempfile.mkdtemp(prefix="input" + DIR_DELIM, dir=input_root)
    output_dir = tempfile.mkdtemp(prefix="output" + DIR_DELIM, dir=output_root)

    # Should be unique name here since folder is unique, also checks only one instance of delim
    _, submission_name = os.path.basename(input_dir).split(DIR_DELIM)
    # Add 'bm_bc_' prefix due to docker's restriction on container names
    submission_name = "bm_bc_{}".format(submission_name)
    # Call random input sampler
    settings = sample_settings(max_records, data_root)
    # Save all inputs
    save_inputs(input_dir, *settings)

    docker_dirs = {input_dir: {"bind": "/submission-inputs", "mode": "ro"},
                   output_dir: {"bind": "/output", "mode": "rw"},
                   "/tmp-data": {"bind": "/tmp-data", "mode": "rw"},
                   "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}}

    assert not docker_exists(submission_name, client)
    logger.info('%s start' % submission_name)
    logs = client.containers.run(DOCKER_IMAGE, command=docker_cmd, auto_remove=True, detach=False,
                                 name=submission_name, volumes=docker_dirs,
                                 stdout=True, stderr=True)
    logger.debug(logs)
    logger.info('%s end' % submission_name)

    scores = read_scores(output_dir)
    score = scores["Submission Score"]
    score = float(score)  # verify simple float to keep simple

    paths = (input_dir, output_dir)
    return paths, score


def random_search(docker_cmd, n_iters, data_root, input_root, output_root):
    best_score = None
    best_setting = None
    for _ in range(n_iters):
        paths, score = search_iteration(docker_cmd, data_root, input_root, output_root)
        # Appears we are maximizing
        if best_score is None or score > best_score:
            best_score = score
            best_setting = paths

        result_str = 'paths: %s\nscore: %f' % (str(paths), score)
        logger.info(result_str)

    return best_setting, best_score


def main():
    logging.basicConfig(level=logging.INFO)

    # TODO explain why this is different than SCENARIO_NAME

    # We can take these from cmd args later:
    sample_size = "1k"
    n_sim_iters = 20
    seed = 123

    n_search_iters = 100
    data_root = abspath2("../reference-data")
    input_root = abspath2("../search-input")
    output_root = abspath2("../search-output")

    os.makedirs(input_root, exist_ok=True)
    os.makedirs(output_root, exist_ok=True)

    # TODO also consider setting pyseed
    np.random.seed(seed)

    # Some prints
    docker_cmd = CMD_TEMPLATE.format(SCENARIO_NAME, sample_size, n_sim_iters)
    (input_dir, output_dir), best_score = random_search(docker_cmd, n_search_iters,
                                                        data_root, input_root, output_root)

    print('Best score: %f' % best_score)
    print('Input: %s' % input_dir)
    print('Output: %s' % output_dir)


if __name__ == "__main__":
    main()
