"""iios/investment/portfolio/optimization/optimization_score.py

Optimization governance score and history.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.optimization.optimization_quality import OptimizationQualityReport
from iios.investment.portfolio.optimization.optimization_types import OptimizationQualityGrade


@dataclass(frozen=True)
class OptimizationScore:
    """Governance score for one OptimizationPlan."""

    score_id:             str                       = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:         str                       = ""
    plan_id:              str                       = ""
    overall:              float                     = 0.0
    grade:                OptimizationQualityGrade  = OptimizationQualityGrade.F
    is_acceptable:        bool                      = False
    gate_passed:          bool                      = False

    objective_achievement:  float = 0.0
    constraint_compliance:  float = 0.0
    convergence_quality:    float = 0.0
    diversification_quality:float = 0.0
    stability_score:        float = 0.0

    delta_overall:        Optional[float]           = None   # vs previous score

    scored_at:            float                     = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score_id":              self.score_id,
            "portfolio_id":          self.portfolio_id,
            "plan_id":               self.plan_id,
            "overall":               round(self.overall, 4),
            "grade":                 self.grade.value,
            "is_acceptable":         self.is_acceptable,
            "gate_passed":           self.gate_passed,
            "objective_achievement": round(self.objective_achievement, 4),
            "constraint_compliance": round(self.constraint_compliance, 4),
            "convergence_quality":   round(self.convergence_quality, 4),
            "diversification_quality":round(self.diversification_quality, 4),
            "stability_score":       round(self.stability_score, 4),
            "delta_overall":         round(self.delta_overall, 4) if self.delta_overall is not None else None,
            "scored_at":             self.scored_at,
        }


class OptimizationScoreCalculator:
    """Converts OptimizationQualityReport → OptimizationScore."""

    def __init__(self, governance_gate: float = 0.55) -> None:
        self._gate = governance_gate

    def calculate(
        self,
        quality_report:  OptimizationQualityReport,
        previous_score:  Optional[OptimizationScore] = None,
    ) -> OptimizationScore:
        overall = quality_report.overall_score
        delta   = (overall - previous_score.overall) if previous_score else None
        return OptimizationScore(
            portfolio_id           = quality_report.portfolio_id,
            plan_id                = quality_report.plan_id,
            overall                = overall,
            grade                  = quality_report.grade,
            is_acceptable          = quality_report.is_acceptable,
            gate_passed            = overall >= self._gate,
            objective_achievement  = quality_report.objective_achievement,
            constraint_compliance  = quality_report.constraint_compliance,
            convergence_quality    = quality_report.convergence_quality,
            diversification_quality= quality_report.diversification_quality,
            stability_score        = quality_report.stability_score,
            delta_overall          = delta,
        )


class OptimizationScoreHistory:
    """Thread-safe bounded history of OptimizationScore for one portfolio."""

    def __init__(self, portfolio_id: str, max_size: int = 100) -> None:
        self._portfolio_id = portfolio_id
        self._max_size     = max(1, max_size)
        self._scores: List[OptimizationScore] = []
        self._lock    = threading.Lock()

    def record(self, score: OptimizationScore) -> None:
        with self._lock:
            self._scores.append(score)
            if len(self._scores) > self._max_size:
                self._scores.pop(0)

    def latest(self) -> Optional[OptimizationScore]:
        with self._lock:
            return self._scores[-1] if self._scores else None

    def best(self) -> Optional[OptimizationScore]:
        with self._lock:
            if not self._scores:
                return None
            return max(self._scores, key=lambda s: s.overall)

    def recent(self, n: int = 10) -> Tuple[OptimizationScore, ...]:
        with self._lock:
            return tuple(self._scores[-n:])

    def count(self) -> int:
        with self._lock:
            return len(self._scores)

    def trend(self) -> Optional[float]:
        with self._lock:
            if len(self._scores) < 2:
                return None
            return self._scores[-1].overall - self._scores[0].overall

    def reset(self) -> None:
        with self._lock:
            self._scores.clear()
