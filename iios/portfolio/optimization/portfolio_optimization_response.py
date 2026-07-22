"""
portfolio_optimization_response.py — iios.portfolio.optimization
=================================================================
Immutable optimization response returned by the engine.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .constants import VERSION
from .portfolio_solution import PortfolioOptimizationSummary, PortfolioSolution


@dataclass(frozen=True)
class PortfolioOptimizationResponse:
    """
    Immutable response returned to the caller after optimization.

    Fields
    ------
    response_id :       Unique identifier.
    request_id :        Matching request identifier.
    portfolio_id :      Portfolio that was optimized.
    optimization_id :   Optimization run identifier.
    selected_solution : The selected optimal solution (None if failure).
    all_solutions :     All ranked solutions.
    summary :           Compact optimization run summary.
    is_error :          True when the optimization run failed.
    error_message :     Non-empty only when is_error is True.
    elapsed_s :         Total elapsed seconds.
    created_at :        Wall-clock response timestamp.
    framework_version : Framework version string.
    """
    response_id:        str
    request_id:         str
    portfolio_id:       str
    optimization_id:    str
    selected_solution:  Optional[PortfolioSolution]
    all_solutions:      tuple   # Tuple[PortfolioSolution, ...]
    summary:            PortfolioOptimizationSummary
    is_error:           bool
    error_message:      str
    elapsed_s:          float
    created_at:         float
    framework_version:  str

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_success(self) -> bool:
        return not self.is_error and self.selected_solution is not None

    @property
    def is_failure(self) -> bool:
        return self.is_error

    @property
    def has_solution(self) -> bool:
        return self.selected_solution is not None

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def create_success(
        cls,
        request_id:        str,
        portfolio_id:      str,
        optimization_id:   str,
        selected_solution: Optional[PortfolioSolution],
        all_solutions:     List[PortfolioSolution],
        summary:           PortfolioOptimizationSummary,
        elapsed_s:         float = 0.0,
    ) -> "PortfolioOptimizationResponse":
        return cls(
            response_id        = str(uuid.uuid4()),
            request_id         = request_id,
            portfolio_id       = portfolio_id,
            optimization_id    = optimization_id,
            selected_solution  = selected_solution,
            all_solutions      = tuple(all_solutions),
            summary            = summary,
            is_error           = False,
            error_message      = "",
            elapsed_s          = elapsed_s,
            created_at         = time.time(),
            framework_version  = VERSION,
        )

    @classmethod
    def create_failure(
        cls,
        request_id:      str,
        portfolio_id:    str,
        optimization_id: str,
        error_message:   str,
        elapsed_s:       float = 0.0,
        *,
        summary:         Optional[PortfolioOptimizationSummary] = None,
    ) -> "PortfolioOptimizationResponse":
        _summary = summary or PortfolioOptimizationSummary(
            optimization_id        = optimization_id,
            portfolio_id           = portfolio_id,
            strategy_name          = "",
            total_candidates       = 0,
            feasible_candidates    = 0,
            infeasible_candidates  = 0,
            selected_candidate_id  = "",
            selected_solution_id   = "",
            best_score             = 0.0,
            avg_score              = 0.0,
            objectives_evaluated   = 0,
            constraints_evaluated  = 0,
            constraints_violated   = 0,
            elapsed_s              = elapsed_s,
            evaluated_at           = time.time(),
        )
        return cls(
            response_id        = str(uuid.uuid4()),
            request_id         = request_id,
            portfolio_id       = portfolio_id,
            optimization_id    = optimization_id,
            selected_solution  = None,
            all_solutions      = (),
            summary            = _summary,
            is_error           = True,
            error_message      = error_message,
            elapsed_s          = elapsed_s,
            created_at         = time.time(),
            framework_version  = VERSION,
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":       self.response_id,
            "request_id":        self.request_id,
            "portfolio_id":      self.portfolio_id,
            "optimization_id":   self.optimization_id,
            "is_success":        self.is_success,
            "is_failure":        self.is_failure,
            "has_solution":      self.has_solution,
            "total_solutions":   len(self.all_solutions),
            "selected_solution": (
                self.selected_solution.to_dict()
                if self.selected_solution
                else None
            ),
            "summary":           self.summary.to_dict(),
            "error_message":     self.error_message,
            "elapsed_s":         self.elapsed_s,
            "created_at":        self.created_at,
            "framework_version": self.framework_version,
        }
