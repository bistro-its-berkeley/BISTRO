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