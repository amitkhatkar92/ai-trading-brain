"""iios/investment/portfolio/performance/performance_confidence.py

Confidence score for portfolio performance analysis.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.performance.performance_types import PerformancePosition


# Minimum positions for a credible analysis
MIN_POSITIONS_BASIC  = 3
MIN_POSITIONS_MEDIUM = 10
MIN_POSITIONS_HIGH   = 20


@dataclass(frozen=True)
class PerformanceConfidenceReport:
    """Confidence in the performance analysis results."""

    report_id:         str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:      str   = ""

    confidence_score:  float = 0.0   # [0, 1]
    data_quality:      float = 0.0   # quality of input data
    model_reliability: float = 0.0   # model's inherent reliability
    coverage_pct:      float = 0.0   # % of positions with actual return data

    confidence_level:  str   = "low"   # low / medium / high / very_high
    insufficient_data: bool  = False
    limitations:       tuple = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence_score":  round(self.confidence_score, 4),
            "confidence_level":  self.confidence_level,
            "data_quality":      round(self.data_quality, 4),
            "insufficient_data": self.insufficient_data,
            "limitations":       list(self.limitations),
        }


def compute_performance_confidence(
    positions:         List[PerformancePosition],
    has_nav_series:    bool  = False,
    analysis_complete: bool  = True,
    portfolio_id:      str   = "",
) -> PerformanceConfidenceReport:
    """
    Compute confidence in the performance analysis.

    Confidence is driven by:
    - Number of positions
    - Availability of actual NAV / return data
    - Completeness of analysis
    - Data quality of position metadata
    """
    n = len(positions)
    limitations: List[str] = []

    # Data quality: how many positions have non-zero period returns
    with_returns = sum(1 for p in positions if abs(p.period_return) > 1e-10)
    coverage = with_returns / n if n > 0 else 0.0
    if coverage < 0.5:
        limitations.append("Less than 50% of positions have actual period returns; using estimates.")

    # Position count factor
    if n < MIN_POSITIONS_BASIC:
        pos_factor = 0.3
        limitations.append(f"Very few positions ({n}); statistical reliability is low.")
    elif n < MIN_POSITIONS_MEDIUM:
        pos_factor = 0.6
    elif n < MIN_POSITIONS_HIGH:
        pos_factor = 0.8
    else:
        pos_factor = 1.0

    # NAV series factor
    nav_factor = 0.90 if has_nav_series else 0.55

    # Analysis completeness
    complete_factor = 1.0 if analysis_complete else 0.7

    # Average conviction quality
    if positions:
        avg_conviction = sum(p.conviction for p in positions) / n
        # conviction near 0.5 = uncertain, near 0 or 1 = definite
        conviction_quality = abs(avg_conviction - 0.5) * 2   # [0, 1]
    else:
        conviction_quality = 0.0
        limitations.append("No positions — confidence is zero.")
        # Explicit zero: nothing to analyse
        return PerformanceConfidenceReport(
            portfolio_id      = portfolio_id,
            confidence_score  = 0.0,
            data_quality      = 0.0,
            model_reliability = 0.0,
            coverage_pct      = 0.0,
            confidence_level  = "low",
            insufficient_data = True,
            limitations       = tuple(limitations),
        )

    # Weighted composite
    data_quality = 0.4 * coverage + 0.3 * conviction_quality + 0.3 * (1 if has_nav_series else 0.4)
    model_rel    = 0.5 * nav_factor + 0.3 * pos_factor + 0.2 * complete_factor
    confidence   = 0.6 * model_rel + 0.4 * data_quality

    confidence = max(0.0, min(1.0, confidence))

    # Classify level
    if confidence >= 0.80:
        level = "very_high"
    elif confidence >= 0.60:
        level = "high"
    elif confidence >= 0.40:
        level = "medium"
    else:
        level = "low"

    return PerformanceConfidenceReport(
        portfolio_id      = portfolio_id,
        confidence_score  = round(confidence, 4),
        data_quality      = round(data_quality, 4),
        model_reliability = round(model_rel, 4),
        coverage_pct      = round(coverage, 4),
        confidence_level  = level,
        insufficient_data = n < MIN_POSITIONS_BASIC,
        limitations       = tuple(limitations),
    )
