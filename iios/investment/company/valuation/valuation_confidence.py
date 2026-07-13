"""iios/investment/company/valuation/valuation_confidence.py
Confidence scoring for valuation estimates.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.investment.company.valuation.valuation_model import ValuationResult, ValuationStatus
from iios.investment.company.valuation.valuation_statistics import (
    coefficient_of_variation, clamp,
)


def compute_valuation_confidence(
    model_results:      List[Optional[ValuationResult]],
    history_depth:      int   = 0,    # number of historical periods available
    fcf_stability:      float = 0.5,  # FCF consistency (0-1); from EarningsSnapshot
    assumptions_calibrated: bool = False,
) -> float:
    """
    Returns an overall confidence score (0.0 – 1.0) for the valuation estimate.

    Dimensions:
    - Data confidence:       based on financial history depth + FCF consistency
    - Model confidence:      number of models that produced valid (COMPUTED) results
    - Assumption confidence: whether assumptions have been calibrated
    - Convergence:           agreement between model point estimates
    """
    # ── Data confidence ────────────────────────────────────────────────────────
    depth_score = clamp(history_depth / 8.0, 0, 1.0)   # 8+ years → full
    data_conf   = depth_score * 0.50 + fcf_stability * 0.50

    # ── Model confidence ───────────────────────────────────────────────────────
    valid_results = [
        r for r in model_results
        if r and r.status == ValuationStatus.COMPUTED and r.intrinsic_value
    ]
    n_valid      = len(valid_results)
    model_conf   = clamp(n_valid / 3.0, 0, 1.0)   # 3+ models → full

    # ── Assumption confidence ──────────────────────────────────────────────────
    assump_conf  = 0.80 if assumptions_calibrated else 0.40

    # ── Convergence (agreement between models) ────────────────────────────────
    if n_valid >= 2:
        values = [r.intrinsic_value for r in valid_results if r.intrinsic_value]
        cv = coefficient_of_variation(values)
        # Low CV → high convergence confidence
        convergence_conf = clamp(1.0 - cv, 0.0, 1.0)
    else:
        convergence_conf = 0.30

    # ── Weighted aggregate ────────────────────────────────────────────────────
    overall = (
        data_conf         * 0.35 +
        model_conf        * 0.25 +
        assump_conf       * 0.20 +
        convergence_conf  * 0.20
    )
    return clamp(overall, 0.0, 1.0)
