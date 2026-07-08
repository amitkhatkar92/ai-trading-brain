"""iios/decision_optimization/algorithms/optimization_algorithm.py — Algorithm ABC + built-ins."""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..optimization_constants import AlgorithmType, ObjectiveType, OptimizationStatus
from ..optimization_context import Candidate
from ..objectives.objective import Objective
from ..constraints.constraint_checker import OptimizationConstraint


@dataclass
class OptimizationSolution:
    optimal_id:      str | None  = None
    ranked_ids:      list[str]   = field(default_factory=list)
    scores:          dict[str, float] = field(default_factory=dict)
    feasible_ids:    list[str]   = field(default_factory=list)
    infeasible_ids:  list[str]   = field(default_factory=list)
    pareto_frontier: list[str]   = field(default_factory=list)
    status:          OptimizationStatus = OptimizationStatus.FEASIBLE
    algorithm_id:    str  = ""
    metadata:        dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "optimal_id":      self.optimal_id,
            "ranked_ids":      self.ranked_ids,
            "feasible_count":  len(self.feasible_ids),
            "status":          self.status.value,
            "algorithm_id":    self.algorithm_id,
        }


class OptimizationAlgorithm(ABC):
    @property
    @abstractmethod
    def algorithm_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def algorithm_type(self) -> AlgorithmType:
        return AlgorithmType.GREEDY

    @property
    def supports_multi_objective(self) -> bool:
        return False

    @abstractmethod
    def optimize(
        self,
        candidates:  list[Candidate],
        objectives:  list[Objective],
        constraints: list[OptimizationConstraint],
        **kwargs,
    ) -> OptimizationSolution: ...

    def to_dict(self) -> dict:
        return {
            "algorithm_id":   self.algorithm_id,
            "name":           self.name,
            "algorithm_type": self.algorithm_type.value,
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_feasible(c: Candidate, constraints: list[OptimizationConstraint]) -> bool:
    for con in constraints:
        if not con.is_hard:
            continue
        try:
            if not con.check(c).satisfied:
                return False
        except Exception:  # noqa: BLE001
            return False
    return True


def _aggregate_objectives(c: Candidate, objectives: list[Objective]) -> float:
    if not objectives:
        return c.evaluation_score
    total_w = sum(o.weight for o in objectives) or 1.0
    return sum(o.effective_score(c) * o.weight for o in objectives) / total_w


def _partition(
    candidates: list[Candidate],
    constraints: list[OptimizationConstraint],
) -> tuple[list[Candidate], list[Candidate]]:
    feasible:   list[Candidate] = []
    infeasible: list[Candidate] = []
    for c in candidates:
        (feasible if _is_feasible(c, constraints) else infeasible).append(c)
    return feasible, infeasible


def _empty_solution(candidates: list[Candidate]) -> OptimizationSolution:
    return OptimizationSolution(
        status         = OptimizationStatus.EMPTY,
        infeasible_ids = [c.candidate_id for c in candidates],
    )


def _infeasible_solution(candidates: list[Candidate]) -> OptimizationSolution:
    return OptimizationSolution(
        status         = OptimizationStatus.INFEASIBLE,
        infeasible_ids = [c.candidate_id for c in candidates],
    )


# ── GreedyOptimizer ───────────────────────────────────────────────────────────

class GreedyOptimizer(OptimizationAlgorithm):
    """Select the feasible candidate with the highest weighted objective score."""

    @property
    def algorithm_id(self) -> str: return "greedy"

    @property
    def name(self) -> str: return "Greedy Optimizer"

    def optimize(
        self,
        candidates:  list[Candidate],
        objectives:  list[Objective],
        constraints: list[OptimizationConstraint],
        **kwargs,
    ) -> OptimizationSolution:
        if not candidates:
            return _empty_solution(candidates)

        feasible, infeasible = _partition(candidates, constraints)
        if not feasible:
            return _infeasible_solution(candidates)

        scored  = {c.candidate_id: _aggregate_objectives(c, objectives) for c in feasible}
        ranked  = sorted(scored, key=scored.__getitem__, reverse=True)

        return OptimizationSolution(
            optimal_id    = ranked[0],
            ranked_ids    = ranked,
            scores        = scored,
            feasible_ids  = [c.candidate_id for c in feasible],
            infeasible_ids= [c.candidate_id for c in infeasible],
            status        = OptimizationStatus.OPTIMAL,
            algorithm_id  = self.algorithm_id,
        )


# ── WeightedSumOptimizer ──────────────────────────────────────────────────────

class WeightedSumOptimizer(OptimizationAlgorithm):
    """Normalise objective scores across candidates, then maximise weighted sum."""

    @property
    def algorithm_id(self) -> str: return "weighted_sum"

    @property
    def name(self) -> str: return "Weighted Sum Optimizer"

    def optimize(
        self,
        candidates:  list[Candidate],
        objectives:  list[Objective],
        constraints: list[OptimizationConstraint],
        **kwargs,
    ) -> OptimizationSolution:
        if not candidates:
            return _empty_solution(candidates)

        feasible, infeasible = _partition(candidates, constraints)
        if not feasible:
            return _infeasible_solution(candidates)

        if not objectives:
            # Fall back to evaluation_score
            scored = {c.candidate_id: c.evaluation_score for c in feasible}
        else:
            raw: dict[str, dict[str, float]] = {
                c.candidate_id: {o.objective_id: o.effective_score(c) for o in objectives}
                for c in feasible
            }
            # Normalise per objective
            norm: dict[str, dict[str, float]] = {}
            for cid in raw:
                norm[cid] = {}
            for obj in objectives:
                oid     = obj.objective_id
                vals    = [raw[cid][oid] for cid in raw]
                mn, mx  = min(vals), max(vals)
                rng     = mx - mn
                for cid in raw:
                    norm[cid][oid] = (raw[cid][oid] - mn) / rng if rng else 1.0

            total_w = sum(o.weight for o in objectives) or 1.0
            scored  = {
                cid: sum(norm[cid][o.objective_id] * o.weight for o in objectives) / total_w
                for cid in norm
            }

        ranked = sorted(scored, key=scored.__getitem__, reverse=True)
        return OptimizationSolution(
            optimal_id     = ranked[0],
            ranked_ids     = ranked,
            scores         = scored,
            feasible_ids   = [c.candidate_id for c in feasible],
            infeasible_ids = [c.candidate_id for c in infeasible],
            status         = OptimizationStatus.OPTIMAL,
            algorithm_id   = self.algorithm_id,
        )


# ── ConstraintSatisfactionOptimizer ──────────────────────────────────────────

class ConstraintSatisfactionOptimizer(OptimizationAlgorithm):
    """
    First honours all hard constraints.
    If no feasible candidates, selects the candidate with fewest hard violations.
    Then maximises objectives.
    """

    @property
    def algorithm_id(self) -> str: return "constraint"

    @property
    def name(self) -> str: return "Constraint Satisfaction Optimizer"

    def optimize(
        self,
        candidates:  list[Candidate],
        objectives:  list[Objective],
        constraints: list[OptimizationConstraint],
        **kwargs,
    ) -> OptimizationSolution:
        if not candidates:
            return _empty_solution(candidates)

        feasible, infeasible = _partition(candidates, constraints)

        if not feasible:
            # Relax to least-violated
            def _violation_count(c: Candidate) -> int:
                return sum(
                    1 for con in constraints
                    if con.is_hard and not con.check(c).satisfied
                )
            best      = min(candidates, key=_violation_count)
            fallback  = _aggregate_objectives(best, objectives)
            return OptimizationSolution(
                optimal_id     = best.candidate_id,
                ranked_ids     = [best.candidate_id],
                scores         = {best.candidate_id: fallback},
                feasible_ids   = [],
                infeasible_ids = [c.candidate_id for c in candidates],
                status         = OptimizationStatus.INFEASIBLE,
                algorithm_id   = self.algorithm_id,
            )

        scored  = {c.candidate_id: _aggregate_objectives(c, objectives) for c in feasible}
        ranked  = sorted(scored, key=scored.__getitem__, reverse=True)
        return OptimizationSolution(
            optimal_id     = ranked[0],
            ranked_ids     = ranked,
            scores         = scored,
            feasible_ids   = [c.candidate_id for c in feasible],
            infeasible_ids = [c.candidate_id for c in infeasible],
            status         = OptimizationStatus.OPTIMAL,
            algorithm_id   = self.algorithm_id,
        )


# ── MultiObjectiveOptimizer ───────────────────────────────────────────────────

class MultiObjectiveOptimizer(OptimizationAlgorithm):
    """Pareto-optimal selection across all objectives."""

    @property
    def algorithm_id(self) -> str: return "multi_objective"

    @property
    def name(self) -> str: return "Multi-Objective Optimizer"

    @property
    def supports_multi_objective(self) -> bool: return True

    def optimize(
        self,
        candidates:  list[Candidate],
        objectives:  list[Objective],
        constraints: list[OptimizationConstraint],
        **kwargs,
    ) -> OptimizationSolution:
        if not candidates:
            return _empty_solution(candidates)

        feasible, infeasible = _partition(candidates, constraints)
        if not feasible:
            return _infeasible_solution(candidates)

        obj_scores: dict[str, list[float]] = {
            c.candidate_id: [o.effective_score(c) for o in objectives]
            for c in feasible
        }

        pareto   = self._pareto_frontier(feasible, obj_scores)
        composite = {
            c.candidate_id: sum(obj_scores[c.candidate_id]) / max(len(objectives), 1)
            for c in feasible
        }
        ranked   = sorted(composite, key=composite.__getitem__, reverse=True)

        return OptimizationSolution(
            optimal_id      = ranked[0],
            ranked_ids      = ranked,
            scores          = composite,
            feasible_ids    = [c.candidate_id for c in feasible],
            infeasible_ids  = [c.candidate_id for c in infeasible],
            pareto_frontier = pareto,
            status          = OptimizationStatus.OPTIMAL,
            algorithm_id    = self.algorithm_id,
        )

    @staticmethod
    def _pareto_frontier(
        candidates: list[Candidate],
        scores:     dict[str, list[float]],
    ) -> list[str]:
        frontier: list[str] = []
        for cand in candidates:
            dominated = False
            for other in candidates:
                if other.candidate_id == cand.candidate_id:
                    continue
                a  = scores[other.candidate_id]
                b  = scores[cand.candidate_id]
                ok = all(ai >= bi for ai, bi in zip(a, b))
                gt = any(ai >  bi for ai, bi in zip(a, b))
                if ok and gt:
                    dominated = True
                    break
            if not dominated:
                frontier.append(cand.candidate_id)
        return frontier
