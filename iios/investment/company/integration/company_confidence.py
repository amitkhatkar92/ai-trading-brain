"""iios/investment/company/integration/company_confidence.py
Computes overall confidence in a Company Intelligence Snapshot.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.integration.quality_statistics import (
    confidence_from_quality, score_volatility,
)
from iios.investment.company.integration.aggregation_history import AggregationHistory
from iios.investment.company.integration.company_state import SCORED_ENGINES


def compute_confidence(
    ticker:            str,
    completeness:      float,
    consistency:       float,
    freshness:         float,
    conflict_count:    int,
    critical_conflicts: int,
    eval_count:        int,
    history:           Optional[AggregationHistory] = None,
) -> float:
    """
    Compute the 0-1 confidence for the current Company Intelligence Snapshot.

    High confidence requires:
    - Most engines providing data (completeness)
    - Checks passing (consistency)
    - Recent data (freshness)
    - Few conflicts
    - Stable history (low score volatility)
    - Multiple evaluations (depth)
    """
    # Score volatility from history
    if history is not None:
        series = history.score_series(ticker, n=8)
    else:
        series = []
    stdev = score_volatility(series)

    base = confidence_from_quality(
        completeness=completeness,
        consistency=consistency,
        freshness=freshness,
        score_stdev=stdev,
        n_evaluations=eval_count,
    )

    # Conflict penalties
    conflict_penalty  = min(0.10, conflict_count  * 0.02)
    critical_penalty  = min(0.20, critical_conflicts * 0.08)

    return round(max(0.0, min(1.0, base - conflict_penalty - critical_penalty)), 4)


def explain_confidence(
    completeness:       float,
    consistency:        float,
    freshness:          float,
    conflict_count:     int,
    critical_conflicts: int,
    available_engines:  List[str],
) -> str:
    """Generate a short human-readable explanation of the confidence level."""
    parts = []

    n_scored = sum(1 for e in SCORED_ENGINES if e in available_engines)
    parts.append(f"{n_scored}/{len(SCORED_ENGINES)} intelligence engines active")

    if freshness >= 0.90:
        parts.append("data is fresh")
    elif freshness >= 0.60:
        parts.append("data is moderately fresh")
    else:
        parts.append("data is stale")

    if consistency >= 0.90:
        parts.append("intelligence is consistent")
    elif consistency >= 0.70:
        parts.append("minor consistency gaps")
    else:
        parts.append("consistency issues detected")

    if critical_conflicts > 0:
        parts.append(f"{critical_conflicts} critical conflict(s) unresolved")
    elif conflict_count > 0:
        parts.append(f"{conflict_count} conflict(s) detected")

    return "; ".join(parts) + "."
