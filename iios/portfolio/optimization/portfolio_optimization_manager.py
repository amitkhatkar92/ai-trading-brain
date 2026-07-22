"""
portfolio_optimization_manager.py — iios.portfolio.optimization
================================================================
Workflow coordinator — runs the full optimization pipeline,
emits events, records statistics and history, and returns a
PortfolioOptimizationResponse.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_STRATEGY_NAME, VERSION
from .exceptions import PortfolioOptimizationValidationError
from .portfolio_candidate import PortfolioCandidate
from .portfolio_candidate_registry import PortfolioCandidateRegistry
from .portfolio_optimization_events import (
    make_allocation_generated,
    make_candidates_loaded,
    make_constraints_loaded,
    make_objectives_loaded,
    make_optimization_completed,
    make_optimization_failed,
    make_optimization_started,
    make_portfolio_selected,
    make_rebalancing_generated,
    make_solution_validated,
)
from .portfolio_optimization_factory import PortfolioOptimizationFactory
from .portfolio_optimization_history import PortfolioOptimizationHistory
from .portfolio_optimization_registry import PortfolioOptimizationRegistry
from .portfolio_optimization_request import PortfolioOptimizationRequest
from .portfolio_optimization_response import PortfolioOptimizationResponse
from .portfolio_optimization_statistics import PortfolioOptimizationStatistics
from .portfolio_optimizer import PortfolioOptimizer
from .portfolio_solution import PortfolioOptimizationSummary
from .portfolio_solution_validator import PortfolioSolutionValidator
from .portfolio_strategy_registry import PortfolioStrategyRegistry

_log = get_logger(__name__)


class PortfolioOptimizationManager:
    """
    Coordinates the full optimization workflow.

    Responsibilities
    ----------------
    - Resolves the optimization strategy from the strategy registry.
    - Resolves candidates from the request (plus fallback to
      the candidate registry).
    - Invokes the PortfolioOptimizer pipeline.
    - Emits all 10 OptimizationEngineEvents.
    - Records metrics in statistics and history.
    - Stores the completed result in the optimization registry.
    - Returns a PortfolioOptimizationResponse.

    This class performs NO policy evaluation and NO trade execution.
    """

    def __init__(
        self,
        optimizer:              PortfolioOptimizer,
        strategy_registry:      PortfolioStrategyRegistry,
        candidate_registry:     PortfolioCandidateRegistry,
        optimization_registry:  PortfolioOptimizationRegistry,
        statistics:             PortfolioOptimizationStatistics,
        history:                PortfolioOptimizationHistory,
    ) -> None:
        self._optimizer             = optimizer
        self._strategy_registry     = strategy_registry
        self._candidate_registry    = candidate_registry
        self._opt_registry          = optimization_registry
        self._stats                 = statistics
        self._history               = history
        self._solution_validator    = PortfolioSolutionValidator()
        self._listeners:            List[Callable] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def optimize_portfolio(
        self, request: PortfolioOptimizationRequest
    ) -> PortfolioOptimizationResponse:
        """
        Run the full optimization pipeline for *request*.

        Returns a PortfolioOptimizationResponse (success or failure).
        Never raises — errors are captured in the response.
        """
        t0 = time.monotonic()
        self._stats.record_request()
        self._history.record_request(request)

        try:
            response = self._run(request, t0)
        except Exception as exc:
            elapsed  = time.monotonic() - t0
            _log.error(f"optimization pipeline raised unexpected exception: {exc}")
            event    = make_optimization_failed(
                request.optimization_id, request.portfolio_id, str(exc)
            )
            self._history.record_event(event)
            self._notify(event)
            self._stats.record_failure()
            response = PortfolioOptimizationResponse.create_failure(
                request_id      = request.request_id,
                portfolio_id    = request.portfolio_id,
                optimization_id = request.optimization_id,
                error_message   = str(exc),
                elapsed_s       = elapsed,
            )

        self._history.record_response(response)
        self._opt_registry.register(response)
        return response

    # ------------------------------------------------------------------
    # Event bus
    # ------------------------------------------------------------------

    def add_listener(self, fn: Callable) -> None:
        if callable(fn) and fn not in self._listeners:
            self._listeners.append(fn)

    def remove_listener(self, fn: Callable) -> None:
        if fn in self._listeners:
            self._listeners.remove(fn)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _run(
        self,
        request: PortfolioOptimizationRequest,
        t0:      float,
    ) -> PortfolioOptimizationResponse:
        oid = request.optimization_id

        # --- candidates ---
        candidates = self._resolve_candidates(request)
        if not candidates:
            raise PortfolioOptimizationValidationError(
                "No candidates available for optimization",
                failed_checks=("candidates_present",),
            )

        # --- OPTIMIZATION_STARTED ---
        ev = make_optimization_started(oid, request.portfolio_id, len(candidates))
        self._history.record_event(ev)
        self._notify(ev)
        self._stats.record_optimization_started(len(candidates))

        # --- CANDIDATES_LOADED ---
        ev = make_candidates_loaded(oid, request.portfolio_id, len(candidates))
        self._history.record_event(ev)
        self._notify(ev)

        # --- strategy ---
        strategy = self._strategy_registry.resolve(request.strategy_name)
        if strategy is None:
            strategy = PortfolioOptimizationFactory.create_default_strategy()

        # --- OBJECTIVES_LOADED ---
        ev = make_objectives_loaded(oid, request.portfolio_id, len(strategy.objectives))
        self._history.record_event(ev)
        self._notify(ev)

        # --- CONSTRAINTS_LOADED ---
        ev = make_constraints_loaded(oid, request.portfolio_id, len(strategy.constraints))
        self._history.record_event(ev)
        self._notify(ev)

        # --- run pipeline ---
        merged_inputs = {**request.inputs}
        solutions, selected = self._optimizer.optimize(
            oid, candidates, strategy, merged_inputs
        )

        # --- allocation / rebalancing events (one per candidate) ---
        for sol in solutions:
            if sol.allocation_plan:
                ev = make_allocation_generated(oid, request.portfolio_id, sol.candidate_id)
                self._history.record_event(ev)
                self._notify(ev)
            if sol.rebalancing_plan:
                ev = make_rebalancing_generated(oid, request.portfolio_id, sol.candidate_id)
                self._history.record_event(ev)
                self._notify(ev)

        # --- PORTFOLIO_SELECTED ---
        selected_cid   = selected.candidate_id if selected else ""
        selected_score = selected.score          if selected else 0.0
        ev = make_portfolio_selected(oid, request.portfolio_id, selected_cid, selected_score)
        self._history.record_event(ev)
        self._notify(ev)

        # --- validate selected solution ---
        validation = None
        if selected is not None:
            validation = self._solution_validator.validate(selected)
        ev = make_solution_validated(
            oid, request.portfolio_id,
            is_valid=validation.is_valid if validation else True,
        )
        self._history.record_event(ev)
        self._notify(ev)

        # --- summary ---
        elapsed_s  = time.monotonic() - t0
        feasible   = [s for s in solutions if s.is_feasible]
        scores     = [s.score for s in solutions]
        best_score = max(scores) if scores else 0.0
        avg_score  = sum(scores) / len(scores) if scores else 0.0
        total_constraints_violated = sum(s.constraints_violated for s in solutions)

        summary = PortfolioOptimizationSummary(
            optimization_id        = oid,
            portfolio_id           = request.portfolio_id,
            strategy_name          = strategy.name,
            total_candidates       = len(candidates),
            feasible_candidates    = len(feasible),
            infeasible_candidates  = len(solutions) - len(feasible),
            selected_candidate_id  = selected_cid,
            selected_solution_id   = selected.solution_id if selected else "",
            best_score             = best_score,
            avg_score              = avg_score,
            objectives_evaluated   = len(strategy.objectives),
            constraints_evaluated  = len(strategy.constraints) * len(candidates),
            constraints_violated   = total_constraints_violated,
            elapsed_s              = elapsed_s,
            evaluated_at           = time.time(),
        )

        # --- OPTIMIZATION_COMPLETED ---
        ev = make_optimization_completed(oid, request.portfolio_id, elapsed_s, selected_cid)
        self._history.record_event(ev)
        self._notify(ev)

        # --- stats ---
        self._stats.record_success(
            solution_count = len(solutions),
            selected       = selected is not None,
        )

        return PortfolioOptimizationResponse.create_success(
            request_id        = request.request_id,
            portfolio_id      = request.portfolio_id,
            optimization_id   = oid,
            selected_solution = selected,
            all_solutions     = solutions,
            summary           = summary,
            elapsed_s         = elapsed_s,
        )

    def _resolve_candidates(
        self,
        request: PortfolioOptimizationRequest,
    ) -> List[PortfolioCandidate]:
        """Merge request candidates with any approved registry candidates."""
        from_request = list(request.candidates)
        from_registry = self._candidate_registry.for_portfolio(request.portfolio_id)
        # Deduplicate by candidate_id; request candidates take precedence
        seen = {c.candidate_id for c in from_request}
        for c in from_registry:
            if c.candidate_id not in seen:
                from_request.append(c)
                seen.add(c.candidate_id)
        return from_request

    def _notify(self, event: Any) -> None:
        for fn in list(self._listeners):
            try:
                fn(event)
            except Exception:
                pass
