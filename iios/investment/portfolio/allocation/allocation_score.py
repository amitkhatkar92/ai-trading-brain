"""iios/investment/portfolio/allocation/allocation_score.py

Allocation score models and history.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.allocation.allocation_quality import AllocationQualityReport
from iios.investment.portfolio.allocation.allocation_types import AllocationQualityGrade


@dataclass(frozen=True)
class AllocationScore:
    """Single-plan allocation quality score with trend support."""

    score_id:             str                    = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:         str                    = ""
    plan_id:              str                    = ""
    overall:              float                  = 0.0   # 0.0 – 1.0
    grade:                AllocationQualityGrade = AllocationQualityGrade.F
    is_acceptable:        bool                   = False
    gate_passed:          bool                   = False

    # Dimension breakdown
    capital_utilisation:  float                  = 0.0
    constraint_compliance:float                  = 0.0
    cash_adequacy:        float                  = 0.0
    exposure_compliance:  float                  = 0.0
    consistency:          float                  = 0.0

    # Trend
    delta_overall:        Optional[float]        = None   # vs previous score

    scored_at:            float                  = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score_id":             self.score_id,
            "portfolio_id":         self.portfolio_id,
            "plan_id":              self.plan_id,
            "overall":              round(self.overall, 4),
            "grade":                self.grade.value,
            "is_acceptable":        self.is_acceptable,
            "gate_passed":          self.gate_passed,
            "capital_utilisation":  round(self.capital_utilisation, 4),
            "constraint_compliance":round(self.constraint_compliance, 4),
            "cash_adequacy":        round(self.cash_adequacy, 4),
            "exposure_compliance":  round(self.exposure_compliance, 4),
            "consistency":          round(self.consistency, 4),
            "delta_overall":        round(self.delta_overall, 4) if self.delta_overall is not None else None,
            "scored_at":            self.scored_at,
        }


class AllocationScoreCalculator:
    """Converts AllocationQualityReport → AllocationScore."""

    def __init__(self, governance_gate: float = 0.55) -> None:
        self._gate = governance_gate

    def calculate(
        self,
        quality_report:  AllocationQualityReport,
        previous_score:  Optional[AllocationScore] = None,
    ) -> AllocationScore:
        overall   = quality_report.overall_score
        delta     = (overall - previous_score.overall) if previous_score else None
        return AllocationScore(
            portfolio_id          = quality_report.portfolio_id,
            plan_id               = quality_report.plan_id,
            overall               = overall,
            grade                 = quality_report.grade,
            is_acceptable         = quality_report.is_acceptable,
            gate_passed           = overall >= self._gate,
            capital_utilisation   = quality_report.capital_utilisation_score,
            constraint_compliance = quality_report.constraint_compliance_score,
            cash_adequacy         = quality_report.cash_adequacy_score,
            exposure_compliance   = quality_report.exposure_compliance_score,
            consistency           = quality_report.consistency_score,
            delta_overall         = delta,
        )


class AllocationScoreHistory:
    """Thread-safe bounded history of AllocationScore objects for one portfolio."""

    __slots__ = ("_portfolio_id", "_max_size", "_scores", "_lock")

    def __init__(self, portfolio_id: str, max_size: int = 100) -> None:
        self._portfolio_id = portfolio_id
        self._max_size     = max(1, max_size)
        self._scores: List[AllocationScore] = []
        self._lock    = threading.Lock()

    def record(self, score: AllocationScore) -> None:
        with self._lock:
            self._scores.append(score)
            if len(self._scores) > self._max_size:
                self._scores.pop(0)

    def latest(self) -> Optional[AllocationScore]:
        with self._lock:
            return self._scores[-1] if self._scores else None

    def best(self) -> Optional[AllocationScore]:
        with self._lock:
            if not self._scores:
                return None
            return max(self._scores, key=lambda s: s.overall)

    def recent(self, n: int = 10) -> Tuple[AllocationScore, ...]:
        with self._lock:
            return tuple(self._scores[-n:])

    def count(self) -> int:
        with self._lock:
            return len(self._scores)

    def trend(self) -> Optional[float]:
        """Returns (latest - oldest) overall score, or None if < 2 entries."""
        with self._lock:
            if len(self._scores) < 2:
                return None
            return self._scores[-1].overall - self._scores[0].overall

    def reset(self) -> None:
        with self._lock:
            self._scores.clear()
