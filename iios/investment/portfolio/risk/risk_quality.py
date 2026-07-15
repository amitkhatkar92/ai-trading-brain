"""iios/investment/portfolio/risk/risk_quality.py

Quality assessment of a portfolio's risk profile.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from iios.investment.portfolio.risk.portfolio_risk_score import RiskScore


@dataclass(frozen=True)
class RiskQualityReport:
    """Quality gate assessment of the portfolio risk score."""

    report_id:       str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:    str   = ""

    is_acceptable:   bool  = True
    quality_score:   float = 0.0    # overall risk score
    threshold:       float = 0.55   # quality gate threshold

    # Dimension breakdown
    dimensions_above_threshold: Tuple[str, ...] = field(default_factory=tuple)
    n_dimensions_at_risk:       int             = 0

    # Actionable summary
    primary_risk_driver:        str             = ""
    recommendation:             str             = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_acceptable":   self.is_acceptable,
            "quality_score":   round(self.quality_score, 4),
            "threshold":       round(self.threshold, 4),
            "n_dimensions_at_risk": self.n_dimensions_at_risk,
            "primary_risk_driver":  self.primary_risk_driver,
            "recommendation":       self.recommendation,
        }


class RiskQualityAssessor:
    """Assesses whether a risk score meets the acceptable quality threshold."""

    def __init__(self, acceptable_threshold: float = 0.55) -> None:
        self._threshold = acceptable_threshold

    def assess(self, risk_score: RiskScore) -> RiskQualityReport:
        dim_map = {
            "market":        risk_score.market_score,
            "credit":        risk_score.credit_score,
            "liquidity":     risk_score.liquidity_score,
            "concentration": risk_score.concentration_score,
            "tail":          risk_score.tail_score,
            "currency":      risk_score.currency_score,
            "interest_rate": risk_score.interest_rate_score,
        }
        above = tuple(
            d for d, s in dim_map.items() if s > self._threshold
        )
        primary = (
            max(dim_map, key=dim_map.__getitem__) if dim_map else ""
        )
        if risk_score.overall > self._threshold:
            reco = (
                f"Portfolio risk is above acceptable threshold "
                f"({risk_score.overall:.2f} > {self._threshold:.2f}). "
                f"Primary driver: {primary}. Consider reducing {primary} exposure."
            )
        else:
            reco = (
                f"Portfolio risk is within acceptable bounds "
                f"({risk_score.overall:.2f} ≤ {self._threshold:.2f})."
            )

        return RiskQualityReport(
            portfolio_id             = risk_score.portfolio_id,
            is_acceptable            = risk_score.overall <= self._threshold,
            quality_score            = round(risk_score.overall, 4),
            threshold                = self._threshold,
            dimensions_above_threshold = above,
            n_dimensions_at_risk     = len(above),
            primary_risk_driver      = primary,
            recommendation           = reco,
        )
