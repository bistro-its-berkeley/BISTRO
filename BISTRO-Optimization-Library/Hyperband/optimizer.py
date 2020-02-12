import logging
import os
import shutil
import sys
import uuid
from timeit import default_timer as timer

import pandas as pd

sys.path.append(os.path.abspath("../../"))
# print(sys.path)
#import convert_to_input
from hyperopt import STATUS_OK

DOCKER_IMAGE = "beammodel/beam-competition:0.0.3-SNAPSHOT"
CMD_TEMPLATE = "--scenario {0} --sample-size {1} --iters {2}"
SCENARIO_NAME = "sioux_faux"
SCORES_PATH = ("competition", "submissionScores.csv")
DIR_DELIM = "-"

logger = logging.getLogger(__name__)

#currently polynomial
budget_update=2

def abspath2(path):
    path = os.path.abspath(os.path.expanduser(path))
    return path


def only_subdir(path):
    subdir, = os.listdir(path)  # Validates only returned element
    path = os.path.join(path, subdir)
    return path


def read_scores(output_dir):
    """Read scores from output directory as .csv file.
    """
    output_dir = only_subdir(only_subdir(output_dir))
    print("subdir")
    print(output_dir)
    df = pd.read_csv(os.path.join(output_dir, *SCORES_PATH), index_col="Component Name")
    scores = df["Weighted Score"]
    return scores


def objective(params):
    """Objective function for Calling the Simulator"""

    # Keep track of evals

    start = timer()

    input_suffix = uuid.uuid4()

    input_dir = "/home/ubuntu/BeamCompetitions/submission-inputs/"+str(input_suffix)
    if not os.path.isdir('/home/ubuntu/BeamCompetitions/submission-inputs/'):
        os.system("sudo rm -f /home/ubuntu/BeamCompetitions/submission-inputs/")
    if not os.path.exists('/home/ubuntu/BeamCompetitions/submission-inputs/'):
        os.system('sudo mkdir /home/ubuntu/BeamCompetitions/submission-inputs/')
    if not os.path.exists(input_dir):
        os.system(f'sudo mkdir {input_dir}')
        os.system('sudo chmod -R 777 /home/ubuntu/BeamCompetitions/submission-inputs/')

    budget=pd.read_csv("/home/ubuntu/BeamCompetitions/budget.csv")
    if(len(budget)==0): n_sim_iters=1   
    else:
        #n_sim_iters=budget[len(budget)-1,0]*budget_update
        n_sim_iters=budget.loc[len(budget)-1,'iter']*budget_update
    
    n_sim_iters=int(n_sim_iters)


    # Run simulator, return a score
    sample_size = "15k" #TODO
    # n_sim_iters = 1
    docker_cmd = CMD_TEMPLATE.format(SCENARIO_NAME, sample_size, n_sim_iters)

    output_suffix = uuid.uuid4()  
    output_dir="/home/ubuntu/BeamCompetitions/output/"+str(output_suffix)
    #if not os.path.isdir('/home/ubuntu/BeamCompetitions/output/'):
    #    os.system("rm -f /home/ubuntu/BeamCompetitions/output/")
    if not os.path.exists('/home/ubuntu/BeamCompetitions/output/'):
        os.system('mkdir /home/ubuntu/BeamCompetitions/output/')
    if not os.path.exists(output_dir):
        os.system(f'sudo mkdir {output_dir}')
        os.system('sudo chmod -R 777 /home/ubuntu/BeamCompetitions/output/')
    print("outputdir")
    print(output_dir)
    print(os.path.exists(output_dir))


    cmd = f"sudo docker run -it -v {output_dir}:/output:rw -v /home/ubuntu/BeamCompetitions/submission-inputs:/submission-inputs:ro {DOCKER_IMAGE} {docker_cmd}"
    print("commandline")
    print(cmd)
    logger.info("!!! execute simulator cmd: %s" % cmd)
    os.system(cmd)

    scores = read_scores(output_dir)
    score = scores["Submission Score"]
    score = float(score)

    output_dir = only_subdir(only_subdir(output_dir))
    shutil.copy(os.path.join(output_dir, *SCORES_PATH), input_dir)

    paths = (input_dir, output_dir)

    loss = score

    run_time = timer() - start


    #TODO DONE update budget.csv
    #budget.loc[len(budget)]=n_sim_iters
    #budget.to_csv("/home/ubuntu/BeamCompetitions/budget.csv")

    # Dictionary with information for evaluation
    return {'loss': loss, 'params': params, 'train_time': run_time, 'status': STATUS_OK, 'paths': paths,'iter':n_sim_iters}
