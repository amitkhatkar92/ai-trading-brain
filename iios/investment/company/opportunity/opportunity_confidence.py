"""iios/investment/company/opportunity/opportunity_confidence.py
Confidence computation for the Opportunity Engine.
Confidence reflects data completeness and signal consistency.
"""
from __future__ import annotations

from typing import Any, List, Optional

from iios.investment.company.opportunity.opportunity_statistics import clamp


_SNAPSHOT_WEIGHTS = {
    "financial":   0.22,
    "earnings":    0.20,
    "business":    0.20,
    "valuation":   0.14,
    "growth":      0.12,
    "management":  0.07,
    "ownership":   0.05,
}
_MIN_CONFIDENCE     = 0.15
_MAX_CONFIDENCE     = 0.95
_CONSISTENCY_WEIGHT = 0.20   # fraction of confidence driven by score consistency


def compute_opportunity_confidence(
    financial_snapshot:  Any,
    earnings_snapshot:   Any,
    business_quality:    Any,
    valuation_snapshot:  Any = None,
    growth_snapshot:     Any = None,
    management_snapshot: Any = None,
    ownership_snapshot:  Any = None,
    score_history:       Optional[List[float]] = None,
) -> float:
    """
    Compute a 0-1 confidence value for the opportunity evaluation.

    Factors:
    1. Data completeness — which upstream snapshots are present.
    2. Score consistency — how stable the score has been over past evaluations.
    """
    # ── Data completeness ─────────────────────────────────────────────────────
    presence = {
        "financial":  financial_snapshot is not None,
        "earnings":   earnings_snapshot is not None,
        "business":   business_quality is not None,
        "valuation":  valuation_snapshot is not None,
        "growth":     growth_snapshot is not None,
        "management": management_snapshot is not None,
        "ownership":  ownership_snapshot is not None,
    }
    completeness = sum(
        _SNAPSHOT_WEIGHTS[k] for k, v in presence.items() if v
    )  # 0-1

    # ── Score consistency ─────────────────────────────────────────────────────
    consistency = _compute_score_consistency(score_history)

    # ── Blend ─────────────────────────────────────────────────────────────────
    raw = (1 - _CONSISTENCY_WEIGHT) * completeness + _CONSISTENCY_WEIGHT * consistency
    return clamp(raw, _MIN_CONFIDENCE, _MAX_CONFIDENCE)


def _compute_score_consistency(history: Optional[List[float]]) -> float:
    """
    Return 0-1 consistency score based on score stability.
    Returns 0.5 (neutral) with no history.
    """
    if not history or len(history) < 2:
        return 0.5
    vals = history[-6:]   # last 6 evaluations
    n    = len(vals)
    mean = sum(vals) / n
    variance = sum((v - mean) ** 2 for v in vals) / n
    std_dev  = variance ** 0.5
    # StdDev of 0 → 1.0 (perfectly stable); StdDev of 20+ → 0.1
    return clamp(1.0 - std_dev / 20.0, 0.1, 1.0)


def explain_confidence(
    financial:  bool,
    earnings:   bool,
    business:   bool,
    valuation:  bool,
    growth:     bool,
    management: bool,
    ownership:  bool,
    confidence: float,
) -> str:
    """Generate a human-readable explanation of the confidence level."""
    present = sum([financial, earnings, business, valuation, growth, management, ownership])
    total   = 7
    parts   = []

    if present == total:
        parts.append("All seven intelligence sources are available")
    elif present >= 5:
        missing = []
        if not valuation:  missing.append("valuation")
        if not growth:     missing.append("growth")
        if not management: missing.append("management")
        if not ownership:  missing.append("ownership")
        parts.append(f"Missing: {', '.join(missing)}")
    else:
        parts.append(f"Only {present}/{total} intelligence sources available")

    if confidence >= 0.80:
        parts.append("high signal consistency across evaluations")
    elif confidence >= 0.60:
        parts.append("moderate signal consistency")
    else:
        parts.append("limited evaluation history")

    return ". ".join(parts) + "."
