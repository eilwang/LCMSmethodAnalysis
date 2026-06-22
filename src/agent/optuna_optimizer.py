"""
Optuna-based Bayesian optimizer for LCMS method parameters.
"""

import optuna
from typing import Callable, Dict, Any

class LCMSOptimizer:
    def __init__(self, objective_func: Callable[[Dict[str, Any]], float], param_space: Dict[str, Any]):
        self.objective_func = objective_func
        self.param_space = param_space
        self.study = optuna.create_study(direction="maximize")

    def suggest(self, n_trials: int = 10):
        def objective(trial):
            params = {k: trial.suggest_float(k, *v) for k, v in self.param_space.items()}
            return self.objective_func(params)
        self.study.optimize(objective, n_trials=n_trials)
        return self.study.best_params, self.study.best_value
