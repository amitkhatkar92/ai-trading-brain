"""
decision_optimization_manager.py — iios.decision.optimization
==============================================================
Orchestrates the complete optimization workflow.

Workflow
--------
1. Load objectives from the registry (filtered by request).
2. Load constraints from the registry (filtered by request).
3. Resolve the optimization strategy from the strategy registry.
4. Emit CANDIDATES_LOADED, OBJECTIVES_LOADED, CONSTRAINTS_LOADED events.
5. Call :class:`DecisionOptimizer.optimize` → :class:`DecisionSolution`.
6. Build :class:`DecisionOptimizationSummary` and :class:`OptimizationReport`.
7. Return (summary, report).

Zero-candidate behaviour
------------------------
When *request.candidates* is empty the manager returns a failure summary
without invoking the optimizer.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from iios.common.logging.logging_manager import get_logger

from .constants import ACTOR_MANAGER
from .decision_constraint import ConstraintEvaluationResult, DecisionConstraint
from .decision_objective  import DecisionObjective
from .decision_optimizer  import DecisionOptimizer
from .decision_optimization_registry import DecisionOptimizationRegistry
from .decision_optimization_request  import DecisionOptimizationRequest
from .decision_optimization_response import (
    DecisionOptimizationSummary,
    OptimizationReport,
)
from .decision_solution   import DecisionSolution
from .decision_strategy_registry import DecisionStrategyRegistry
from .exceptions import NoCandidatesError, NoFeasibleSolutionError, StrategyNotFoundError

_log = get_logger(__name__)


class DecisionOptimizationManager:
    """
    Orchestrates the full optimization workflow from request to summary.

    Parameters
    ----------
    registry :          Stores objectives and constraints.
    strategy_registry : Stores optimization strategies.
    optimizer :         Executes the core algorithm.
    """

    def __init__(
        self,
        registry:          DecisionOptimizationRegistry,
        strategy_registry: DecisionStrategyRegistry,
        optimizer:         DecisionOptimizer,
    ) -> None:
        self._registry          = registry
        self._strategy_registry = strategy_registry
        self._optimizer         = optimizer

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def optimize(
        self,
        request: DecisionOptimizationRequest,
    ) -> Tuple[DecisionOptimizationSummary, OptimizationReport]:
        """
        Execute the optimization workflow and return
        ``(DecisionOptimizationSummary, OptimizationReport)``.
        """
        t_start = time.time()

        request_id  = request.request_id
        decision_id = request.context.decision_id
        candidates  = list(request.candidates)

        # --- 1. Handle empty candidates ---
        if not candidates:
            return self._zero_candidate_result(request, t_start)

        # --- 2. Load configuration ---
        objectives  = self._registry.get_objectives(request.objective_ids)
        constraints = self._registry.get_constraints(request.constraint_ids)

        try:
            strategy = self._strategy_registry.get(request.strategy_id)
        except StrategyNotFoundError:
            _log.warning(
                f"DecisionOptimizationManager: strategy {request.strategy_id!r} "
                f"not found; using default"
            )
            strategy = self._strategy_registry.get_default()

        # --- 3. Optimize ---
        try:
            solution: Optional[DecisionSolution] = self._optimizer.optimize(
                request_id  = request_id,
                decision_id = decision_id,
                candidates  = candidates,
                objectives  = objectives,
                constraints = constraints,
                strategy    = strategy,
                context     = request.context,
            )
        except (NoCandidatesError, NoFeasibleSolutionError) as exc:
            _log.warning(
                f"DecisionOptimizationManager: optimization failed: {exc}"
            )
            return self._failed_result(request, str(exc), t_start)
        except Exception as exc:
            _log.warning(
                f"DecisionOptimizationManager: unexpected error: {exc}"
            )
            return self._failed_result(request, str(exc), t_start)

        elapsed = time.time() - t_start

        # --- 4. Count feasibility ---
        feasible_count   = sum(1 for r in solution.rankings if r.is_feasible)
        infeasible_count = len(solution.rankings) - feasible_count
        violations       = sum(
            len(r.is_feasible and 0 or [])
            for r in solution.rankings
        )
        # Simpler: count hard violations from solution
        hard_violations = len([v for v in solution.constraint_violations
                                if True])  # all in violations are hard since soft won't block

        summary = DecisionOptimizationSummary(
            summary_id            = str(uuid.uuid4()),
            request_id            = request_id,
            decision_id           = decision_id,
            selected_candidate_id = solution.selected_candidate.candidate_id,
            is_feasible           = solution.is_feasible,
            final_score           = solution.final_score,
            candidates_evaluated  = len(candidates),
            feasible_count        = feasible_count,
            infeasible_count      = infeasible_count,
            optimization_strategy = strategy.name,
            optimization_time_s   = elapsed,
            objectives_applied    = len(objectives),
            constraints_applied   = len(constraints),
            constraint_violations = len(solution.constraint_violations),
            rationale             = solution.rationale,
            solution              = solution,
            evaluated_at          = datetime.now(timezone.utc),
        )

        report = OptimizationReport(
            report_id             = str(uuid.uuid4()),
            request_id            = request_id,
            decision_id           = decision_id,
            candidates_evaluated  = len(candidates),
            feasible_count        = feasible_count,
            infeasible_count      = infeasible_count,
            constraint_violations = len(solution.constraint_violations),
            optimization_strategy = strategy.name,
            selected_candidate_id = solution.selected_candidate.candidate_id,
            final_score           = solution.final_score,
            rankings              = solution.rankings,
            objective_scores      = solution.objective_scores,
            generated_at          = datetime.now(timezone.utc),
        )

        return summary, report

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _zero_candidate_result(
        self,
        request: DecisionOptimizationRequest,
        t_start: float,
    ) -> Tuple[DecisionOptimizationSummary, OptimizationReport]:
        elapsed = time.time() - t_start
        summary = self._empty_summary(
            request, elapsed, "No candidates provided for optimization"
        )
        report  = self._empty_report(request)
        return summary, report

    def _failed_result(
        self,
        request: DecisionOptimizationRequest,
        reason:  str,
        t_start: float,
    ) -> Tuple[DecisionOptimizationSummary, OptimizationReport]:
        elapsed = time.time() - t_start
        summary = self._empty_summary(request, elapsed, reason)
        report  = self._empty_report(request)
        return summary, report

    def _empty_summary(
        self,
        request:  DecisionOptimizationRequest,
        elapsed:  float,
        rationale: str,
    ) -> DecisionOptimizationSummary:
        strat = self._strategy_registry.find(request.strategy_id)
        name  = strat.name if strat else request.strategy_id
        return DecisionOptimizationSummary(
            summary_id            = str(uuid.uuid4()),
            request_id            = request.request_id,
            decision_id           = request.context.decision_id,
            selected_candidate_id = None,
            is_feasible           = False,
            final_score           = 0.0,
            candidates_evaluated  = len(request.candidates),
            feasible_count        = 0,
            infeasible_count      = len(request.candidates),
            optimization_strategy = name,
            optimization_time_s   = elapsed,
            objectives_applied    = 0,
            constraints_applied   = 0,
            constraint_violations = 0,
            rationale             = rationale,
            solution              = None,
            evaluated_at          = datetime.now(timezone.utc),
        )

    def _empty_report(
        self,
        request: DecisionOptimizationRequest,
    ) -> OptimizationReport:
        strat = self._strategy_registry.find(request.strategy_id)
        name  = strat.name if strat else request.strategy_id
        return OptimizationReport(
            report_id             = str(uuid.uuid4()),
            request_id            = request.request_id,
            decision_id           = request.context.decision_id,
            candidates_evaluated  = len(request.candidates),
            feasible_count        = 0,
            infeasible_count      = len(request.candidates),
            constraint_violations = 0,
            optimization_strategy = name,
            selected_candidate_id = None,
            final_score           = 0.0,
            rankings              = (),
            objective_scores      = {},
            generated_at          = datetime.now(timezone.utc),
        )
