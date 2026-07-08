"""iios/decision_optimization/simulation/robustness_evaluator.py"""
from __future__ import annotations

import copy
import random

from ..optimization_context import Candidate
from ..objectives.objective import Objective
from ..constraints.constraint_checker import OptimizationConstraint
from ..algorithms.optimization_algorithm import GreedyOptimizer, OptimizationAlgorithm
from ..optimization_constants import DEFAULT_SIMULATION_TRIALS


class RobustnessEvaluator:
    """
    Measures how stable the optimal solution is when candidate
    evaluation_scores are perturbed by Gaussian noise.
    """

    def evaluate(
        self,
        candidates:  list[Candidate],
        objectives:  list[Objective],
        constraints: list[OptimizationConstraint],
        algorithm:   OptimizationAlgorithm | None = None,
        noise_level: float = 0.05,
        n_trials:    int   = DEFAULT_SIMULATION_TRIALS,
        seed:        int | None = None,
    ) -> dict:
        alg = algorithm or GreedyOptimizer()
        rng = random.Random(seed)

        # Baseline
        baseline      = alg.optimize(candidates, objectives, constraints)
        baseline_id   = baseline.optimal_id

        wins:          dict[str, int] = {}
        trial_results: list[str]      = []

        for _ in range(n_trials):
            noisy = self._add_noise(candidates, noise_level, rng)
            sol   = alg.optimize(noisy, objectives, constraints)
            winner = sol.optimal_id or ""
            wins[winner]   = wins.get(winner, 0) + 1
            trial_results.append(winner)

        stability = wins.get(baseline_id or "", 0) / max(n_trials, 1)
        return {
            "baseline_optimal": baseline_id,
            "stability":        stability,      # 0..1 — fraction of trials matching baseline
            "win_counts":       wins,
            "n_trials":         n_trials,
            "noise_level":      noise_level,
        }

    @staticmethod
    def _add_noise(
        candidates: list[Candidate], noise_level: float, rng: random.Random
    ) -> list[Candidate]:
        noisy: list[Candidate] = []
        for cand in candidates:
            c              = copy.copy(cand)
            c.evaluation_score = cand.evaluation_score + rng.gauss(0, noise_level)
            noisy.append(c)
        return noisy
