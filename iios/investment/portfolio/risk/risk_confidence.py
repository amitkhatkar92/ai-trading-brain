"""iios/investment/portfolio/risk/risk_confidence.py

Confidence in the risk analysis based on data quality and model reliability.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.risk.risk_types import RiskLevel, RiskPosition


@dataclass(frozen=True)
class RiskConfidenceReport:
    """Confidence in the risk analysis output."""

    report_id:           str       = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:        str       = ""

    # Component confidence scores [0, 1]
    data_quality:        float     = 0.0   # completeness of inputs
    model_reliability:   float     = 0.0   # adequacy of parametric model
    coverage_pct:        float     = 0.0   # positions with full data

    # Composite [0, 1]
    confidence_score:    float     = 0.0

    # Qualitative level
    confidence_level:    str       = "low"   # low / moderate / high / very_high

    # Flags
    insufficient_data:   bool      = False
    model_limitations:   tuple     = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence_score":  round(self.confidence_score, 4),
            "confidence_level":  self.confidence_level,
            "data_quality":      round(self.data_quality, 4),
            "model_reliability": round(self.model_reliability, 4),
            "coverage_pct":      round(self.coverage_pct, 4),
            "insufficient_data": self.insufficient_data,
            "model_limitations": list(self.model_limitations),
        }


def _confidence_level(score: float) -> str:
    if score >= 0.80:
        return "very_high"
    if score >= 0.65:
        return "high"
    if score >= 0.50:
        return "moderate"
    return "low"


def compute_risk_confidence(
    positions:         List[RiskPosition],
    analysis_complete: bool = True,
    portfolio_id:      str  = "",
) -> RiskConfidenceReport:
    if not positions:
        return RiskConfidenceReport(
            portfolio_id       = portfolio_id,
            confidence_level   = "low",
            insufficient_data  = True,
            model_limitations  = ("no_positions",),
        )

    # Data quality: fraction of positions with non-default fields
    def _has_sector(p: RiskPosition) -> bool:
        return bool(p.sector and p.sector != "unknown")

    coverage = sum(1 for p in positions if _has_sector(p)) / len(positions)
    data_q   = coverage * 0.7 + (0.3 if analysis_complete else 0.0)

    # Model reliability: parametric model less reliable with few positions
    n = len(positions)
    model_rel = min(1.0, n / 10.0) * 0.8 + 0.2

    composite = data_q * 0.50 + model_rel * 0.30 + coverage * 0.20

    limitations = []
    if n < 5:
        limitations.append("few_positions_reduce_diversification_reliability")
    if coverage < 0.50:
        limitations.append("many_positions_missing_sector_metadata")
    if not analysis_complete:
        limitations.append("analysis_incomplete")

    return RiskConfidenceReport(
        portfolio_id       = portfolio_id,
        data_quality       = round(data_q, 4),
        model_reliability  = round(model_rel, 4),
        coverage_pct       = round(coverage, 4),
        confidence_score   = round(composite, 4),
        confidence_level   = _confidence_level(composite),
        insufficient_data  = n < 2,
        model_limitations  = tuple(limitations),
    )
