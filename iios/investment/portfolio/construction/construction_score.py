"""iios/investment/portfolio/construction/construction_score.py

Single-number construction score derived from a ConstructionQualityReport.

The score is a deterministic composite — it never involves market data or
optimisation.  It is used for construction history comparison, health
dashboards, and governance gates.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from iios.investment.portfolio.construction.construction_types import (
    HealthStatus,
    QualityDimension,
)


# ---------------------------------------------------------------------------
# ConstructionScore
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConstructionScore:
    """
    Derived, single-number score for one construction run.

    Complements ConstructionQualityReport by providing a compact,
    directly comparable score object suitable for sorting, history
    comparison, and governance gate checks.
    """

    score_id:       str          = field(default_factory=lambda: str(uuid.uuid4()))
    blueprint_id:   str          = ""
    portfolio_id:   str          = ""

    # Overall composite [0, 1]
    overall:        float        = 0.0

    # Grade: A ≥ 0.90, B ≥ 0.75, C ≥ 0.60, D ≥ 0.45, F < 0.45
    grade:          str          = "F"

    health_status:  HealthStatus = HealthStatus.UNKNOWN
    is_acceptable:  bool         = False
    gate_passed:    bool         = False   # overall >= governance_gate_threshold

    # Per-dimension
    completeness:           float = 0.0
    consistency:            float = 0.0
    constraint_compliance:  float = 0.0
    rec_alignment:          float = 0.0
    policy_compliance:      float = 0.0
    diversity:              float = 0.0
    readiness:              float = 0.0

    # Delta vs previous score (positive = improvement)
    delta_overall:  Optional[float] = None

    scored_at:      float        = field(default_factory=time.time)

    # ---------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score_id":              self.score_id,
            "blueprint_id":          self.blueprint_id,
            "portfolio_id":          self.portfolio_id,
            "overall":               round(self.overall, 4),
            "grade":                 self.grade,
            "health_status":         self.health_status.value,
            "is_acceptable":         self.is_acceptable,
            "gate_passed":           self.gate_passed,
            "completeness":          round(self.completeness, 4),
            "consistency":           round(self.consistency, 4),
            "constraint_compliance": round(self.constraint_compliance, 4),
            "rec_alignment":         round(self.rec_alignment, 4),
            "policy_compliance":     round(self.policy_compliance, 4),
            "diversity":             round(self.diversity, 4),
            "readiness":             round(self.readiness, 4),
            "delta_overall":         (
                round(self.delta_overall, 4) if self.delta_overall is not None else None
            ),
            "scored_at":             self.scored_at,
        }


# ---------------------------------------------------------------------------
# ScoreCalculator
# ---------------------------------------------------------------------------

class ScoreCalculator:
    """
    Converts a ConstructionQualityReport into a ConstructionScore.

    governance_gate: minimum overall score for gate_passed=True.
    """

    def __init__(self, governance_gate: float = 0.55) -> None:
        self._gate = governance_gate

    def calculate(
        self,
        quality_report: Any,
        previous_score: Optional[ConstructionScore] = None,
    ) -> ConstructionScore:
        overall = getattr(quality_report, "overall_score", 0.0)

        dim_map = {
            d.dimension: d.normalised
            for d in getattr(quality_report, "dimension_scores", [])
        }

        grade = self._grade(overall)
        delta = (
            round(overall - previous_score.overall, 4)
            if previous_score is not None
            else None
        )

        return ConstructionScore(
            blueprint_id          = getattr(quality_report, "blueprint_id", ""),
            portfolio_id          = getattr(quality_report, "portfolio_id", ""),
            overall               = round(overall, 4),
            grade                 = grade,
            health_status         = getattr(quality_report, "health_status", HealthStatus.UNKNOWN),
            is_acceptable         = getattr(quality_report, "is_acceptable", False),
            gate_passed           = overall >= self._gate,
            completeness          = dim_map.get(QualityDimension.COMPLETENESS, 0.0),
            consistency           = dim_map.get(QualityDimension.CONSISTENCY, 0.0),
            constraint_compliance = dim_map.get(QualityDimension.CONSTRAINT_COMPLIANCE, 0.0),
            rec_alignment         = dim_map.get(QualityDimension.RECOMMENDATION_ALIGNMENT, 0.0),
            policy_compliance     = dim_map.get(QualityDimension.POLICY_COMPLIANCE, 0.0),
            diversity             = dim_map.get(QualityDimension.DIVERSITY, 0.0),
            readiness             = dim_map.get(QualityDimension.READINESS, 0.0),
            delta_overall         = delta,
        )

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 0.90:
            return "A"
        if score >= 0.75:
            return "B"
        if score >= 0.60:
            return "C"
        if score >= 0.45:
            return "D"
        return "F"


# ---------------------------------------------------------------------------
# ScoreHistory
# ---------------------------------------------------------------------------

class ScoreHistory:
    """
    Bounded, thread-safe store of ConstructionScores for a portfolio.
    Provides trend and comparison utilities.
    """

    __slots__ = ("_portfolio_id", "_max_size", "_scores", "_lock")

    def __init__(self, portfolio_id: str, max_size: int = 100) -> None:
        import threading
        self._portfolio_id = portfolio_id
        self._max_size     = max(1, max_size)
        self._scores: list = []
        self._lock         = threading.Lock()

    def record(self, score: ConstructionScore) -> None:
        with self._lock:
            self._scores.append(score)
            if len(self._scores) > self._max_size:
                self._scores.pop(0)

    def latest(self) -> Optional[ConstructionScore]:
        with self._lock:
            return self._scores[-1] if self._scores else None

    def all(self) -> Tuple[ConstructionScore, ...]:
        with self._lock:
            return tuple(self._scores)

    def recent(self, n: int = 5) -> Tuple[ConstructionScore, ...]:
        with self._lock:
            return tuple(self._scores[-n:])

    def trend(self) -> Optional[float]:
        """Average delta over the last 5 scores. Positive = improving."""
        recent = self.recent(5)
        deltas = [s.delta_overall for s in recent if s.delta_overall is not None]
        if not deltas:
            return None
        return round(sum(deltas) / len(deltas), 4)

    def best(self) -> Optional[ConstructionScore]:
        with self._lock:
            return max(self._scores, key=lambda s: s.overall) if self._scores else None

    def count(self) -> int:
        with self._lock:
            return len(self._scores)
