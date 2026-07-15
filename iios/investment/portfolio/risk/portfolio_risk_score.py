"""iios/investment/portfolio/risk/portfolio_risk_score.py

Composite portfolio risk scoring with per-dimension weights and grades.
Lower score = less risky (better).
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.risk.risk_types import (
    WEIGHT_CONCENTRATION, WEIGHT_CREDIT, WEIGHT_CURRENCY,
    WEIGHT_INTEREST_RATE, WEIGHT_LIQUIDITY, WEIGHT_MARKET,
    WEIGHT_TAIL, RiskGrade, RiskLevel,
    risk_score_to_grade, risk_score_to_level,
)


@dataclass(frozen=True)
class RiskDimensionScore:
    """Score for a single risk dimension."""
    dimension:    str
    score:        float   # [0, 1] — lower = safer
    weight:       float
    contribution: float   # weight × score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension":    self.dimension,
            "score":        round(self.score, 4),
            "weight":       round(self.weight, 4),
            "contribution": round(self.contribution, 4),
        }


@dataclass(frozen=True)
class RiskScore:
    """Composite portfolio risk score."""

    score_id:          str                       = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:      str                       = ""

    # Individual dimension scores [0, 1]
    market_score:      float                     = 0.0
    credit_score:      float                     = 0.0
    liquidity_score:   float                     = 0.0
    concentration_score: float                   = 0.0
    tail_score:        float                     = 0.0
    currency_score:    float                     = 0.0
    interest_rate_score: float                   = 0.0

    # Composite
    overall:           float                     = 0.0   # [0, 1]
    delta_overall:     float                     = 0.0   # change vs previous

    # Metadata
    grade:             RiskGrade                 = RiskGrade.B
    risk_level:        RiskLevel                 = RiskLevel.MODERATE
    is_acceptable:     bool                      = True
    quality_gate:      float                     = 0.55  # threshold used

    dimension_scores:  Tuple[RiskDimensionScore, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall":         round(self.overall, 4),
            "grade":           self.grade.value,
            "risk_level":      self.risk_level.value,
            "is_acceptable":   self.is_acceptable,
            "market_score":    round(self.market_score, 4),
            "credit_score":    round(self.credit_score, 4),
            "liquidity_score": round(self.liquidity_score, 4),
            "concentration_score": round(self.concentration_score, 4),
            "tail_score":      round(self.tail_score, 4),
            "currency_score":  round(self.currency_score, 4),
            "interest_rate_score": round(self.interest_rate_score, 4),
        }


class RiskScoreCalculator:
    """Calculates a weighted composite risk score from dimension sub-scores."""

    def __init__(
        self,
        quality_gate: float = 0.55,
    ) -> None:
        self._quality_gate = quality_gate
        self._weights = {
            "market":        WEIGHT_MARKET,
            "credit":        WEIGHT_CREDIT,
            "liquidity":     WEIGHT_LIQUIDITY,
            "concentration": WEIGHT_CONCENTRATION,
            "tail":          WEIGHT_TAIL,
            "currency":      WEIGHT_CURRENCY,
            "interest_rate": WEIGHT_INTEREST_RATE,
        }

    def calculate(
        self,
        market_score:        float,
        credit_score:        float,
        liquidity_score:     float,
        concentration_score: float,
        tail_score:          float,
        currency_score:      float,
        interest_rate_score: float,
        portfolio_id:        str = "",
        previous_overall:    Optional[float] = None,
    ) -> RiskScore:
        scores = {
            "market":        market_score,
            "credit":        credit_score,
            "liquidity":     liquidity_score,
            "concentration": concentration_score,
            "tail":          tail_score,
            "currency":      currency_score,
            "interest_rate": interest_rate_score,
        }
        overall = sum(
            self._weights[dim] * s for dim, s in scores.items()
        )
        delta = (overall - previous_overall) if previous_overall is not None else 0.0

        dim_scores = tuple(
            RiskDimensionScore(
                dimension=dim,
                score=s,
                weight=self._weights[dim],
                contribution=round(self._weights[dim] * s, 6),
            )
            for dim, s in scores.items()
        )

        grade = risk_score_to_grade(overall)
        level = risk_score_to_level(overall)

        return RiskScore(
            portfolio_id         = portfolio_id,
            market_score         = round(market_score, 4),
            credit_score         = round(credit_score, 4),
            liquidity_score      = round(liquidity_score, 4),
            concentration_score  = round(concentration_score, 4),
            tail_score           = round(tail_score, 4),
            currency_score       = round(currency_score, 4),
            interest_rate_score  = round(interest_rate_score, 4),
            overall              = round(overall, 6),
            delta_overall        = round(delta, 6),
            grade                = grade,
            risk_level           = level,
            is_acceptable        = overall <= self._quality_gate,
            quality_gate         = self._quality_gate,
            dimension_scores     = dim_scores,
        )


class RiskScoreHistory:
    """Thread-safe, bounded history of RiskScore for a portfolio."""

    def __init__(self, portfolio_id: str, max_size: int = 100) -> None:
        self._portfolio_id = portfolio_id
        self._max          = max_size
        self._lock         = threading.RLock()
        self._history:     List[RiskScore] = []

    def record(self, score: RiskScore) -> None:
        with self._lock:
            self._history.append(score)
            if len(self._history) > self._max:
                self._history = self._history[-self._max:]

    def latest(self) -> Optional[RiskScore]:
        with self._lock:
            return self._history[-1] if self._history else None

    def all(self, n: Optional[int] = None) -> List[RiskScore]:
        with self._lock:
            if n is None:
                return list(self._history)
            return list(self._history[-n:])
