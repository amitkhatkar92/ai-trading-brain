"""iios/investment/company/valuation/valuation_score.py
Compute ValuationIntelligenceScore from quality and confidence inputs.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.valuation.valuation_model import ValuationResult, ValuationStatus
from iios.investment.company.valuation.valuation_snapshot import ValuationIntelligenceScore
from iios.investment.company.valuation.valuation_statistics import (
    coefficient_of_variation, clamp,
)
from iios.investment.company.valuation.valuation_quality import ValuationQuality


def compute_valuation_score(
    quality:             ValuationQuality,
    overall_confidence:  float,          # from valuation_confidence.py
    model_results:       List[Optional[ValuationResult]],
    assumptions_calibrated: bool = False,
) -> ValuationIntelligenceScore:
    """
    Compute the 4-dimension ValuationIntelligenceScore (0-100 each dimension).

    Dimension weights:
    - Model coverage:  25%
    - Data quality:    30%
    - Assumption:      25%
    - Convergence:     20%
    """
    # ── Model coverage ────────────────────────────────────────────────────────
    model_coverage_score = clamp(quality.model_count / 4.0, 0, 1.0) * 100

    # ── Data quality ──────────────────────────────────────────────────────────
    depth_score = clamp(quality.history_depth / 8.0, 0, 1.0)
    fcf_score   = 1.0 if quality.fcf_positive else 0.3
    data_quality_score = (depth_score * 0.6 + fcf_score * 0.4) * 100

    # ── Assumption quality ────────────────────────────────────────────────────
    assumption_score = 80.0 if assumptions_calibrated else 40.0

    # ── Convergence ───────────────────────────────────────────────────────────
    valid = [
        r for r in model_results
        if r and r.status == ValuationStatus.COMPUTED and r.intrinsic_value
    ]
    if len(valid) >= 2:
        values = [r.intrinsic_value for r in valid if r.intrinsic_value]
        cv = coefficient_of_variation(values)
        convergence_score = clamp(1.0 - cv, 0.0, 1.0) * 100
    elif len(valid) == 1:
        convergence_score = 40.0
    else:
        convergence_score = 0.0

    # ── Overall (weighted average) ────────────────────────────────────────────
    overall_score = (
        model_coverage_score * 0.25 +
        data_quality_score   * 0.30 +
        assumption_score     * 0.25 +
        convergence_score    * 0.20
    )

    # ── Label ─────────────────────────────────────────────────────────────────
    if overall_score >= 70:
        label = "high"
    elif overall_score >= 45:
        label = "medium"
    elif overall_score >= 20:
        label = "low"
    else:
        label = "insufficient"

    explanation: List[str] = []
    if quality.model_count == 0:
        explanation.append("No valuation model produced a valid result")
    elif quality.model_count == 1:
        explanation.append("Only one model produced a valid result — convergence unknown")
    if quality.history_depth < 3:
        explanation.append("Limited financial history reduces data quality")
    if not quality.fcf_positive:
        explanation.append("Non-positive FCF reduces DCF reliability")
    if convergence_score < 40 and len(valid) >= 2:
        explanation.append("High divergence between model estimates")

    return ValuationIntelligenceScore(
        overall_score        = round(overall_score, 1),
        model_coverage_score = round(model_coverage_score, 1),
        data_quality_score   = round(data_quality_score, 1),
        assumption_score     = round(assumption_score, 1),
        convergence_score    = round(convergence_score, 1),
        label                = label,
        explanation          = explanation,
    )
