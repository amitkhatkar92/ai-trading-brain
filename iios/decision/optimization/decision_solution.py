"""
decision_solution.py — iios.decision.optimization
===================================================
DecisionSolution — the selected optimal candidate and its full rationale.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .constants import VERSION
from .decision_candidate import DecisionCandidate
from .decision_ranking_engine import DecisionRanking


@dataclass(frozen=True)
class DecisionSolution:
    """
    The output of a single optimization run: the selected candidate
    together with its scores, ranking, and a human-readable rationale.

    Parameters
    ----------
    solution_id :          Unique identifier.
    request_id :           Originating request ID.
    decision_id :          Decision that was optimized.
    selected_candidate :   The chosen :class:`DecisionCandidate`.
    final_score :          Confidence-adjusted score of the selection.
    rank :                 Position in the ranking (1 = best).
    rankings :             Full candidate ranking for traceability.
    objective_scores :     Per-objective scores of the selected candidate.
    constraint_violations: Names of violated soft constraints.
    optimization_strategy: Name of the strategy used.
    rationale :            Human-readable explanation.
    evaluation_time_s :    Wall-clock time for this optimization.
    generated_at :         Timestamp.
    framework_version :    Framework version.
    is_optimal :           ``True`` when rank == 1 and candidate is feasible.
    is_feasible :          ``True`` when no hard constraints were violated.
    """

    solution_id:            str
    request_id:             str
    decision_id:            str
    selected_candidate:     DecisionCandidate
    final_score:            float
    rank:                   int
    rankings:               Tuple[DecisionRanking, ...]
    objective_scores:       Dict[str, float]
    constraint_violations:  Tuple[str, ...]
    optimization_strategy:  str
    rationale:              str
    evaluation_time_s:      float
    generated_at:           datetime
    is_optimal:             bool
    is_feasible:            bool
    framework_version:      str   = VERSION

    def to_dict(self) -> dict:
        return {
            "solution_id":           self.solution_id,
            "request_id":            self.request_id,
            "decision_id":           self.decision_id,
            "selected_candidate_id": self.selected_candidate.candidate_id,
            "symbol":                self.selected_candidate.symbol,
            "direction":             self.selected_candidate.direction,
            "final_score":           self.final_score,
            "rank":                  self.rank,
            "is_optimal":            self.is_optimal,
            "is_feasible":           self.is_feasible,
            "optimization_strategy": self.optimization_strategy,
            "rationale":             self.rationale,
            "evaluation_time_s":     self.evaluation_time_s,
            "generated_at":          self.generated_at.isoformat(),
            "framework_version":     self.framework_version,
        }
