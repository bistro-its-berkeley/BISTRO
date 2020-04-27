# HyperBand OPTIMIZATION (Based on per-mile)

## What is HyperBand 

HyperBand is a bandit-based approach algorithm that runs policies for a limited amount of time and uses intermediate results to decide whether or not to pursue the evaluation further, thereby reducing the amount of resources spent on ultimately bad candidate policies. contains four variables:
HyperBand can be used to accelerate the optimization process due to our observations in the experiments with TPE that the result can only improve signifanctly with first few iterations.
For more information about HyperBand, see:
Li, Lisha, et al. "Hyperband: A novel bandit-based approach to hyperparameter optimization." The Journal of Machine Learning Research 18.1 (2017): 6765-6816.
Falkner, Stefan, Aaron Klein, and Frank Hutter. "Combining hyperband and bayesian optimization." Proceedings of the 31st Conference on Neural Information Processing Systems (NIPS), Bayesian Optimization Workshop. 2017.

## Running HyperBand
Running HyperBand is similar to running Bayesian optimization(TPE) with per-mile. For HyperBand, there are several special parameters to tune.
* `portion` defines the portion of trials to discard after every iteration. This parameter is written in bayesian_optimization_hyperband.py
* `budget_update` defines the way that budget for one iteration will update. The default way of updating the budget is new_budget = old_budget * budget_update. This parameter is written both in bayesian_optimization_hyperband.py and optimizer_hyperband.py

## Possible Improvements
1. Warm Start Mode in Beam. The current design of Beam is that the first iteration is much slower than other iterations. As HyperBand need to restart Beam several times, the current HyperBand is slower than we expect. If Warm Start Mode in Beam can work, this is a great improvement for running HyperBand.
2. Parameter passing in current HyperOpt library. As the parameters in 'fmin()' function in HyperOpt library is hard coded, the current implementation keeps track of and passes the parameters by creating, reading and modifying a file. And these operations happens in every iteration for every trials and could slow down the HyperBand.

#Warm Start of Beam
With Warm Start, you can loaded the results from the earlier Beam run and used them to start a new BEAM run

## How to use warm start
Related documentation can be found in https://beam.readthedocs.io/en/latest/inputs.html?highlight=warm-start#configuration-file
To modify the specification for Warm Start in Beam, you can simply change two lines of code in the configuration file BISTRO/fixed-data/sioux-faux/sioux_faux-15k.conf. 
 1 beam.warmStart.enabled = true
 2 beam.warmStart.path = "/bau/warm-start/sioux_faux-15k__warm-start.zip"(You may need to change a little bit to make sure the correct route is used within your file structure)

## Current challenge with warm start
Our current challenge with Warm Start is that,  beam/src/main/scala/beam/sim/BeamWarmStart.scala has specified that if Warm Start is not enabled, there should be the exception that "BeamWarmStart cannot be initialized since warmstart is disabled". 
If Warm Start is enabled and the path for zip file is wrong, there should be exception "Travel times failed to warm start, stats not found at path".
If Warm Start is enabled and the path for the zip file is correct, Warm Start should be working and should output the corresponding log information "Read travel times from...". 
Therefore, if the design of Warm Start is correct with Sioux-faux, there should always be log information about warm start whether Warm Start is enabled or not, or whether Warm Start is enabled correctly or not. But in the current version of Beam we are using, there is no log information about Warm Start.

## Some advice on reading the code of Beam about warm start
The most important file about the logic of warm start in Beam is beam/src/main/scala/beam/sim/BeamWarmStart.scala(https://github.com/LBNL-UCB-STI/beam/blob/d40faa44c5e2aaaede7eee6a80f1afb806329a67/src/main/scala/beam/sim/BeamWarmStart.scala). This scala file mainly deal with two tasks:
1. Reading the specification about Warm Start in the configuration file and evaluate whether the specifications are effective. If not effective, throw corresponding exceptions. This part is in the class "class BeamWarmStart private (beamConfig: BeamConfig, maxHour: Int) extends LazyLogging".
2. Reading the results from previous Beam run and start a new run. This part is in "object BeamWarmStart extends LazyLogging".
 
 