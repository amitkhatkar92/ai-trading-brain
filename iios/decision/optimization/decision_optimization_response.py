"""
decision_optimization_response.py — iios.decision.optimization
================================================================
DecisionOptimizationSummary — aggregated run summary.
OptimizationReport          — full traceability report.
DecisionOptimizationResponse — public output of the engine.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from .constants import VERSION
from .decision_ranking_engine import DecisionRanking
from .decision_solution import DecisionSolution


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DecisionOptimizationSummary:
    """
    High-level summary of one optimization run.

    Parameters
    ----------
    summary_id :           Unique identifier.
    request_id :           Originating request ID.
    decision_id :          Decision optimized.
    selected_candidate_id: ID of the chosen candidate (None on failure).
    is_feasible :          Whether the selection satisfies all hard constraints.
    final_score :          Confidence-adjusted score of the selection.
    candidates_evaluated : Total candidates evaluated.
    feasible_count :       Candidates satisfying hard constraints.
    infeasible_count :     Candidates violating hard constraints.
    optimization_strategy: Name of the applied strategy.
    optimization_time_s :  Total wall-clock time.
    objectives_applied :   Number of objectives used.
    constraints_applied :  Number of constraints checked.
    constraint_violations: Total hard-constraint violations across all candidates.
    rationale :            Human-readable explanation.
    solution :             The full :class:`DecisionSolution` (None on failure).
    evaluated_at :         Timestamp.
    framework_version :    Framework version.
    """

    summary_id:            str
    request_id:            str
    decision_id:           str
    selected_candidate_id: Optional[str]
    is_feasible:           bool
    final_score:           float
    candidates_evaluated:  int
    feasible_count:        int
    infeasible_count:      int
    optimization_strategy: str
    optimization_time_s:   float
    objectives_applied:    int
    constraints_applied:   int
    constraint_violations: int
    rationale:             str
    solution:              Optional[DecisionSolution]
    evaluated_at:          datetime
    framework_version:     str = VERSION

    @property
    def is_success(self) -> bool:
        return self.solution is not None

    def to_dict(self) -> dict:
        return {
            "summary_id":            self.summary_id,
            "request_id":            self.request_id,
            "decision_id":           self.decision_id,
            "selected_candidate_id": self.selected_candidate_id,
            "is_feasible":           self.is_feasible,
            "final_score":           self.final_score,
            "candidates_evaluated":  self.candidates_evaluated,
            "feasible_count":        self.feasible_count,
            "infeasible_count":      self.infeasible_count,
            "optimization_strategy": self.optimization_strategy,
            "optimization_time_s":   self.optimization_time_s,
            "objectives_applied":    self.objectives_applied,
            "constraints_applied":   self.constraints_applied,
            "constraint_violations": self.constraint_violations,
            "rationale":             self.rationale,
            "is_success":            self.is_success,
            "framework_version":     self.framework_version,
        }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OptimizationReport:
    """
    Full traceability report for one optimization run.

    Parameters
    ----------
    report_id :              Unique identifier.
    request_id :             Originating request ID.
    decision_id :            Decision optimized.
    candidates_evaluated :   Total candidates evaluated.
    feasible_count :         Feasible candidates.
    infeasible_count :       Infeasible candidates.
    constraint_violations :  Hard-constraint violations across all candidates.
    optimization_strategy :  Name of the applied strategy.
    selected_candidate_id :  Chosen candidate ID (None on failure).
    final_score :            Score of the selection.
    rankings :               Full candidate ranking.
    objective_scores :       Per-objective scores for the selected candidate.
    generated_at :           Timestamp.
    framework_version :      Framework version.
    """

    report_id:              str
    request_id:             str
    decision_id:            str
    candidates_evaluated:   int
    feasible_count:         int
    infeasible_count:       int
    constraint_violations:  int
    optimization_strategy:  str
    selected_candidate_id:  Optional[str]
    final_score:            float
    rankings:               Tuple[DecisionRanking, ...]
    objective_scores:       Dict[str, float]
    generated_at:           datetime
    framework_version:      str = VERSION

    def to_dict(self) -> dict:
        return {
            "report_id":             self.report_id,
            "request_id":            self.request_id,
            "decision_id":           self.decision_id,
            "candidates_evaluated":  self.candidates_evaluated,
            "feasible_count":        self.feasible_count,
            "infeasible_count":      self.infeasible_count,
            "constraint_violations": self.constraint_violations,
            "optimization_strategy": self.optimization_strategy,
            "selected_candidate_id": self.selected_candidate_id,
            "final_score":           self.final_score,
            "rankings":              [
                {"rank": r.rank, "candidate_id": r.candidate_id,
                 "score": r.final_score, "is_feasible": r.is_feasible}
                for r in self.rankings
            ],
            "objective_scores":      self.objective_scores,
            "generated_at":          self.generated_at.isoformat(),
            "framework_version":     self.framework_version,
        }


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DecisionOptimizationResponse:
    """
    Public output of :class:`DecisionOptimizationEngine.optimize`.

    Use :meth:`success` and :meth:`failure` to construct instances.
    """

    response_id:         str
    request_id:          str
    decision_id:         str
    solution:            Optional[DecisionSolution]
    summary:             Optional[DecisionOptimizationSummary]
    optimization_report: Optional[OptimizationReport]
    error:               Optional[str]
    evaluation_time_s:   float
    responded_at:        datetime
    framework_version:   str = VERSION

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_success(self) -> bool:
        return self.error is None and self.solution is not None

    @property
    def is_optimal(self) -> bool:
        return self.solution is not None and self.solution.is_optimal

    @property
    def is_feasible(self) -> bool:
        return self.solution is not None and self.solution.is_feasible

    # ------------------------------------------------------------------
    # Classmethods
    # ------------------------------------------------------------------

    @classmethod
    def success(
        cls,
        request_id:          str,
        decision_id:         str,
        solution:            DecisionSolution,
        summary:             DecisionOptimizationSummary,
        optimization_report: OptimizationReport,
        *,
        evaluation_time_s:   float         = 0.0,
        response_id:         Optional[str] = None,
    ) -> "DecisionOptimizationResponse":
        return cls(
            response_id         = response_id or str(uuid.uuid4()),
            request_id          = request_id,
            decision_id         = decision_id,
            solution            = solution,
            summary             = summary,
            optimization_report = optimization_report,
            error               = None,
            evaluation_time_s   = evaluation_time_s,
            responded_at        = datetime.now(timezone.utc),
        )

    @classmethod
    def failure(
        cls,
        request_id:  str,
        decision_id: str,
        error:       str,
        *,
        response_id: Optional[str] = None,
    ) -> "DecisionOptimizationResponse":
        return cls(
            response_id         = response_id or str(uuid.uuid4()),
            request_id          = request_id,
            decision_id         = decision_id,
            solution            = None,
            summary             = None,
            optimization_report = None,
            error               = error,
            evaluation_time_s   = 0.0,
            responded_at        = datetime.now(timezone.utc),
        )

    def to_dict(self) -> dict:
        return {
            "response_id":       self.response_id,
            "request_id":        self.request_id,
            "decision_id":       self.decision_id,
            "is_success":        self.is_success,
            "is_optimal":        self.is_optimal,
            "is_feasible":       self.is_feasible,
            "error":             self.error,
            "evaluation_time_s": self.evaluation_time_s,
            "responded_at":      self.responded_at.isoformat(),
            "framework_version": self.framework_version,
        }
