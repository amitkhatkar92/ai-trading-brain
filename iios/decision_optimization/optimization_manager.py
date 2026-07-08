"""iios/decision_optimization/optimization_manager.py — Request, Result, Manager."""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field

from .optimization_constants import (
    DEFAULT_ALGORITHM_TYPE,
    DEFAULT_OPTIMIZATION_MODE,
    MAX_OPTIMIZATION_HISTORY,
    AlgorithmType,
    OptimizationMode,
    OptimizationStatus,
)
from .optimization_exceptions import (
    InsufficientCandidatesError,
    OptimizationNotFoundError,
)
from .optimization_context import Candidate
from .objectives.objective import Objective
from .objectives.objective_result import ObjectiveResult, build_objective_result
from .constraints.constraint_checker import OptimizationConstraint
from .constraints.constraint_report import ConstraintReport
from .constraints.constraint_optimizer import ConstraintOptimizer
from .constraints.constraint_solver import ConstraintSolver
from .algorithms.optimization_algorithm import OptimizationSolution
from .algorithms.algorithm_executor import AlgorithmExecutor
from .algorithms.algorithm_selector import AlgorithmSelector
from .simulation.simulation_engine import SimulationEngine
from .simulation.sensitivity_analyzer import SensitivityAnalyzer
from .simulation.robustness_evaluator import RobustnessEvaluator


@dataclass
class OptimizationRequest:
    request_id:     str  = field(default_factory=lambda: str(uuid.uuid4()))
    candidates:     list[Candidate]             = field(default_factory=list)
    objectives:     list[Objective]             = field(default_factory=list)
    constraints:    list[OptimizationConstraint] = field(default_factory=list)
    algorithm_type: AlgorithmType               = DEFAULT_ALGORITHM_TYPE
    algorithm_id:   str | None                  = None
    mode:           OptimizationMode            = DEFAULT_OPTIMIZATION_MODE
    metadata:       dict                        = field(default_factory=dict)
    created_at:     float                       = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "request_id":     self.request_id,
            "n_candidates":   len(self.candidates),
            "n_objectives":   len(self.objectives),
            "n_constraints":  len(self.constraints),
            "algorithm_type": self.algorithm_type.value,
            "mode":           self.mode.value,
        }


@dataclass
class OptimizationResult:
    result_id:         str  = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:        str  = ""
    candidates:        list[Candidate]           = field(default_factory=list)
    optimal_id:        str | None                = None
    status:            OptimizationStatus        = OptimizationStatus.FEASIBLE
    feasible_ids:      list[str]                 = field(default_factory=list)
    infeasible_ids:    list[str]                 = field(default_factory=list)
    objective_result:  ObjectiveResult | None    = None
    constraint_report: ConstraintReport | None   = None
    solution:          OptimizationSolution | None = None
    succeeded:         bool                      = True
    errors:            list[str]                 = field(default_factory=list)
    warnings:          list[str]                 = field(default_factory=list)
    duration_ms:       float                     = 0.0
    created_at:        float                     = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "result_id":    self.result_id,
            "request_id":   self.request_id,
            "succeeded":    self.succeeded,
            "optimal_id":   self.optimal_id,
            "status":       self.status.value,
            "duration_ms":  self.duration_ms,
            "errors":       self.errors,
        }


class OptimizationManager:
    """
    Core optimization pipeline:
    objective evaluation → constraint checking → algorithm execution → result.
    """

    def __init__(
        self,
        executor:             AlgorithmExecutor    | None = None,
        constraint_optimizer: ConstraintOptimizer  | None = None,
        simulation_engine:    SimulationEngine     | None = None,
        sensitivity_analyzer: SensitivityAnalyzer  | None = None,
        robustness_evaluator: RobustnessEvaluator  | None = None,
    ) -> None:
        self._executor    = executor             or AlgorithmExecutor()
        self._constraints = constraint_optimizer or ConstraintOptimizer()
        self._simulation  = simulation_engine    or SimulationEngine()
        self._sensitivity = sensitivity_analyzer or SensitivityAnalyzer()
        self._robustness  = robustness_evaluator or RobustnessEvaluator()
        self._history:    dict[str, OptimizationResult] = {}
        self._lock        = threading.RLock()

    # ── Core optimize ──────────────────────────────────────────────────────

    def optimize(self, request: OptimizationRequest) -> OptimizationResult:
        start  = time.perf_counter()
        result = OptimizationResult(
            request_id = request.request_id,
            candidates = list(request.candidates),
        )
        try:
            if len(request.candidates) < 1:
                raise InsufficientCandidatesError(len(request.candidates), required=1)

            # 1. Evaluate objectives
            obj_result = build_objective_result(
                request.candidates, request.objectives
            )
            result.objective_result = obj_result

            # 2. Check constraints + produce report
            solver    = ConstraintSolver()
            solve_res = solver.solve(request.candidates, request.constraints)
            from .constraints.constraint_report import build_constraint_report
            c_report  = build_constraint_report(
                request.candidates, request.constraints, solve_res
            )
            result.constraint_report = c_report
            result.feasible_ids      = c_report.feasible_ids
            result.infeasible_ids    = c_report.infeasible_ids

            # 3. Run algorithm
            solution = self._executor.execute(
                candidates     = request.candidates,
                objectives     = request.objectives,
                constraints    = request.constraints,
                algorithm_type = request.algorithm_type,
                algorithm_id   = request.algorithm_id,
            )
            result.solution   = solution
            result.optimal_id = solution.optimal_id
            result.status     = solution.status

        except Exception as exc:  # noqa: BLE001
            result.succeeded = request.mode == OptimizationMode.AUDIT
            result.errors.append(str(exc))
            result.status    = OptimizationStatus.ERROR
            if request.mode == OptimizationMode.STRICT:
                raise

        result.duration_ms = (time.perf_counter() - start) * 1_000.0
        self._store(result)
        return result

    # ── Simulation helpers (thin wrappers) ────────────────────────────────

    def simulate_what_if(
        self,
        request:      OptimizationRequest,
        perturbation: dict,
    ) -> OptimizationSolution:
        alg = AlgorithmSelector().select(
            request.algorithm_type, request.algorithm_id
        )
        return self._simulation.run_what_if(
            request.candidates, request.objectives,
            request.constraints, perturbation, alg,
        )

    def sensitivity_analysis(
        self,
        request:      OptimizationRequest,
        objective_id: str,
        weight_range: tuple[float, float] = (0.0, 1.0),
        steps:        int = 10,
    ) -> dict:
        alg = AlgorithmSelector().select(request.algorithm_type, request.algorithm_id)
        return self._sensitivity.analyze_objective_weight(
            request.candidates, request.objectives,
            request.constraints, objective_id,
            weight_range, steps, alg,
        )

    def robustness(
        self,
        request:     OptimizationRequest,
        noise_level: float = 0.05,
        n_trials:    int   = 50,
    ) -> dict:
        alg = AlgorithmSelector().select(request.algorithm_type, request.algorithm_id)
        return self._robustness.evaluate(
            request.candidates, request.objectives,
            request.constraints, alg, noise_level, n_trials,
        )

    # ── History ────────────────────────────────────────────────────────────

    def get(self, result_id: str) -> OptimizationResult:
        with self._lock:
            if result_id not in self._history:
                raise OptimizationNotFoundError(result_id)
            return self._history[result_id]

    def recent(self, n: int = 10) -> list[OptimizationResult]:
        with self._lock:
            items = sorted(
                self._history.values(), key=lambda r: r.created_at, reverse=True
            )
            return items[:n]

    def statistics(self) -> dict:
        with self._lock:
            total   = len(self._history)
            success = sum(1 for r in self._history.values() if r.succeeded)
            return {"total": total, "success": success, "failure": total - success}

    def stats(self) -> dict:
        return self.statistics()

    # ── Private ────────────────────────────────────────────────────────────

    def _store(self, result: OptimizationResult) -> None:
        with self._lock:
            self._history[result.result_id] = result
            if len(self._history) > MAX_OPTIMIZATION_HISTORY:
                oldest = sorted(
                    self._history, key=lambda k: self._history[k].created_at
                )
                for k in oldest[:len(self._history) - MAX_OPTIMIZATION_HISTORY]:
                    del self._history[k]


_manager: OptimizationManager | None = None
_lock    = threading.Lock()


def get_optimization_manager() -> OptimizationManager:
    global _manager
    if _manager is None:
        with _lock:
            if _manager is None:
                _manager = OptimizationManager()
    return _manager


def reset_optimization_manager() -> None:
    global _manager
    with _lock:
        _manager = None
