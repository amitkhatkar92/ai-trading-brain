"""iios/investment/portfolio/diversification/diversification_score.py

Governance score derived from a DiversificationQualityReport.
Includes bounded per-portfolio score history.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.diversification.diversification_quality import (
    DiversificationQualityReport,
)
from iios.investment.portfolio.diversification.diversification_types import (
    DEFAULT_QUALITY_GATE,
    DiversificationGrade,
)


@dataclass(frozen=True)
class DiversificationScore:
    """Governance-gated diversification score."""

    score_id:     str                 = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id: str                 = ""
    analysis_id:  str                 = ""
    overall:      float               = 0.0
    grade:        DiversificationGrade= DiversificationGrade.F
    is_acceptable:bool                = False
    gate_passed:  bool                = False
    gate:         float               = DEFAULT_QUALITY_GATE
    # Dimension sub-scores
    position:     float               = 0.0
    sector:       float               = 0.0
    correlation:  float               = 0.0
    concentration:float               = 0.0
    resilience:   float               = 0.0
    delta_overall:Optional[float]     = None   # vs previous score
    scored_at:    float               = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score_id":     self.score_id,
            "portfolio_id": self.portfolio_id,
            "analysis_id":  self.analysis_id,
            "overall":      round(self.overall, 4),
            "grade":        self.grade.value,
            "is_acceptable":self.is_acceptable,
            "gate_passed":  self.gate_passed,
            "gate":         self.gate,
            "position":     round(self.position, 4),
            "sector":       round(self.sector, 4),
            "correlation":  round(self.correlation, 4),
            "concentration":round(self.concentration, 4),
            "resilience":   round(self.resilience, 4),
            "delta_overall":round(self.delta_overall, 4) if self.delta_overall is not None else None,
            "scored_at":    self.scored_at,
        }


class DiversificationScoreCalculator:
    """Computes a DiversificationScore from a quality report."""

    def __init__(self, governance_gate: float = DEFAULT_QUALITY_GATE) -> None:
        self._gate = governance_gate

    def calculate(
        self,
        quality_report:  DiversificationQualityReport,
        previous_score:  Optional[DiversificationScore] = None,
    ) -> DiversificationScore:
        overall = quality_report.overall_score
        delta   = (overall - previous_score.overall) if previous_score else None
        return DiversificationScore(
            portfolio_id  = quality_report.portfolio_id,
            analysis_id   = quality_report.analysis_id,
            overall       = overall,
            grade         = quality_report.grade,
            is_acceptable = quality_report.is_acceptable,
            gate_passed   = overall >= self._gate,
            gate          = self._gate,
            position      = quality_report.position_score,
            sector        = quality_report.sector_score,
            correlation   = quality_report.correlation_score,
            concentration = quality_report.concentration_score,
            resilience    = quality_report.resilience_score,
            delta_overall = round(delta, 4) if delta is not None else None,
        )


class DiversificationScoreHistory:
    """Thread-safe, bounded per-portfolio score history."""

    def __init__(self, portfolio_id: str, max_size: int = 100) -> None:
        self._portfolio_id = portfolio_id
        self._max  = max(1, max_size)
        self._scores: List[DiversificationScore] = []
        self._lock = threading.Lock()

    def record(self, score: DiversificationScore) -> None:
        with self._lock:
            self._scores.append(score)
            if len(self._scores) > self._max:
                self._scores.pop(0)

    def latest(self) -> Optional[DiversificationScore]:
        with self._lock:
            return self._scores[-1] if self._scores else None

    def best(self) -> Optional[DiversificationScore]:
        with self._lock:
            return max(self._scores, key=lambda s: s.overall) if self._scores else None

    def recent(self, n: int = 10) -> List[DiversificationScore]:
        with self._lock:
            return list(self._scores[-n:])

    def count(self) -> int:
        with self._lock:
            return len(self._scores)

    def trend(self) -> str:
        """Return 'improving' | 'stable' | 'deteriorating' | 'insufficient_data'."""
        with self._lock:
            scores = list(self._scores)
        if len(scores) < 3:
            return "insufficient_data"
        recent_avg = sum(s.overall for s in scores[-3:]) / 3
        prior_avg  = sum(s.overall for s in scores[-6:-3]) / max(len(scores[-6:-3]), 1)
        delta = recent_avg - prior_avg
        if delta > 0.03:
            return "improving"
        if delta < -0.03:
            return "deteriorating"
        return "stable"

    def reset(self) -> None:
        with self._lock:
            self._scores.clear()
