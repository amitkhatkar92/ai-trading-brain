"""iios/investment/portfolio/performance/performance_score.py

Composite performance scoring engine.

Weights: sharpe=0.35, alpha=0.25, sortino=0.20, calmar=0.10, info_ratio=0.10
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.performance.performance_types import (
    SCORE_AVERAGE, SCORE_EXCELLENT, SCORE_GOOD, SCORE_BELOW_AVERAGE,
    SHARPE_ACCEPTABLE, SHARPE_EXCELLENT, SHARPE_GOOD,
    ALPHA_EXCELLENT, ALPHA_GOOD,
    PerformanceGrade, PerformanceLevel, PerformanceTrend,
    normalize_alpha, normalize_sharpe,
    performance_score_to_grade, performance_score_to_level,
)

# Dimension weights (sum = 1.0)
_WEIGHTS = {
    "sharpe":    0.35,
    "alpha":     0.25,
    "sortino":   0.20,
    "calmar":    0.10,
    "info_ratio":0.10,
}


@dataclass(frozen=True)
class PerformanceDimensionScore:
    """Score for a single performance dimension."""

    dimension:   str
    raw_value:   float = 0.0
    score:       float = 0.0   # [0, 1]
    weight:      float = 0.0
    contribution:float = 0.0   # score × weight

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension":    self.dimension,
            "raw_value":    round(self.raw_value, 4),
            "score":        round(self.score, 4),
            "contribution": round(self.contribution, 4),
        }


@dataclass(frozen=True)
class PerformanceScore:
    """Composite performance score."""

    result_id:           str  = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:        str  = ""

    overall:             float             = 0.0   # [0, 1]
    sharpe_score:        float             = 0.0
    alpha_score:         float             = 0.0
    sortino_score:       float             = 0.0
    calmar_score:        float             = 0.0
    info_ratio_score:    float             = 0.0

    grade:               PerformanceGrade  = PerformanceGrade.F
    level:               PerformanceLevel  = PerformanceLevel.POOR
    is_acceptable:       bool              = False

    # Change vs previous score
    delta_overall:       float             = 0.0
    trend:               PerformanceTrend  = PerformanceTrend.INSUFFICIENT

    dimensions:          tuple             = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall":          round(self.overall, 4),
            "grade":            self.grade.value,
            "level":            self.level.value,
            "is_acceptable":    self.is_acceptable,
            "delta_overall":    round(self.delta_overall, 4),
            "trend":            self.trend.value,
            "dimensions":       [d.to_dict() for d in self.dimensions],
        }


class PerformanceScoreCalculator:
    """Calculates composite performance score from raw metrics."""

    def __init__(self, quality_gate: float = 0.55) -> None:
        self.quality_gate = quality_gate

    def calculate(
        self,
        sharpe:           float = 0.0,
        alpha:            float = 0.0,
        sortino:          float = 0.0,
        calmar:           float = 0.0,
        information_ratio:float = 0.0,
        portfolio_id:     str   = "",
        previous_score:   Optional[float] = None,
    ) -> PerformanceScore:

        # Normalize each dimension to [0, 1]
        s_score  = normalize_sharpe(sharpe)
        a_score  = normalize_alpha(alpha)
        so_score = normalize_sharpe(sortino)     # same normalization as sharpe
        c_score  = _normalize_calmar(calmar)
        ir_score = _normalize_ir(information_ratio)

        dim_map = {
            "sharpe":    (sharpe,            s_score,  _WEIGHTS["sharpe"]),
            "alpha":     (alpha,             a_score,  _WEIGHTS["alpha"]),
            "sortino":   (sortino,           so_score, _WEIGHTS["sortino"]),
            "calmar":    (calmar,            c_score,  _WEIGHTS["calmar"]),
            "info_ratio":(information_ratio, ir_score, _WEIGHTS["info_ratio"]),
        }

        overall = sum(sc * w for _, sc, w in dim_map.values())
        overall = max(0.0, min(1.0, overall))

        grade = performance_score_to_grade(overall)
        level = performance_score_to_level(overall)

        # Delta vs previous
        delta  = 0.0
        trend  = PerformanceTrend.INSUFFICIENT
        if previous_score is not None:
            delta = overall - previous_score
            if abs(delta) < 0.02:
                trend = PerformanceTrend.STABLE
            elif delta > 0:
                trend = PerformanceTrend.IMPROVING
            else:
                trend = PerformanceTrend.DETERIORATING

        dimensions = tuple(
            PerformanceDimensionScore(
                dimension    = k,
                raw_value    = round(rv, 4),
                score        = round(sc, 4),
                weight       = w,
                contribution = round(sc * w, 4),
            )
            for k, (rv, sc, w) in dim_map.items()
        )

        return PerformanceScore(
            portfolio_id     = portfolio_id,
            overall          = round(overall, 4),
            sharpe_score     = round(s_score, 4),
            alpha_score      = round(a_score, 4),
            sortino_score    = round(so_score, 4),
            calmar_score     = round(c_score, 4),
            info_ratio_score = round(ir_score, 4),
            grade            = grade,
            level            = level,
            is_acceptable    = overall >= self.quality_gate,
            delta_overall    = round(delta, 4),
            trend            = trend,
            dimensions       = dimensions,
        )


class PerformanceScoreHistory:
    """Thread-safe bounded history of scores for a portfolio."""

    def __init__(self, portfolio_id: str, max_size: int = 100) -> None:
        self.portfolio_id = portfolio_id
        self._max  = max_size
        self._lock = threading.RLock()
        self._data: List[PerformanceScore] = []

    def add(self, score: PerformanceScore) -> None:
        with self._lock:
            self._data.append(score)
            if len(self._data) > self._max:
                self._data = self._data[-self._max:]

    def latest(self) -> Optional[PerformanceScore]:
        with self._lock:
            return self._data[-1] if self._data else None

    def recent(self, n: int) -> List[PerformanceScore]:
        with self._lock:
            return list(self._data[-n:])

    def best(self) -> Optional[PerformanceScore]:
        with self._lock:
            if not self._data:
                return None
            return max(self._data, key=lambda s: s.overall)


def _normalize_calmar(calmar: float) -> float:
    """Normalize Calmar ratio to [0, 1]. Good ≥ 1.0, excellent ≥ 2.0."""
    if calmar <= 0:
        return 0.0
    if calmar >= 2.0:
        return 1.0
    return calmar / 2.0


def _normalize_ir(ir: float) -> float:
    """Normalize information ratio to [0, 1]. Good ≥ 0.5, excellent ≥ 1.0."""
    if ir <= 0:
        return max(0.0, 0.5 + ir * 0.5)   # partial credit for near-zero
    if ir >= 1.0:
        return 1.0
    return 0.5 + ir * 0.5
