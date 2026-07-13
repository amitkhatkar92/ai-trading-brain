"""iios/investment/company/valuation/relative_valuation.py
Relative valuation: implied fair value from target multiples.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from iios.investment.company.valuation.valuation_model import (
    ValuationModelType, ValuationResult, ValuationStatus,
)
from iios.investment.company.valuation.valuation_assumptions import RelativeValuationAssumptions
from iios.investment.company.valuation.valuation_statistics import (
    safe_mean, safe_median, weighted_average, clamp,
)


class RelativeValuationEngine:
    """
    Computes implied fair value per share from multiple relative valuation approaches.
    Blends P/E, EV/EBITDA, EV/Sales, P/B, and P/FCF implied values.
    """

    def estimate(
        self,
        assumptions:         RelativeValuationAssumptions,
        # Per-share data
        earnings_per_share:  Optional[float],
        book_value_per_share: Optional[float],
        fcf_per_share:       Optional[float],
        revenue_per_share:   Optional[float],
        ebitda_per_share:    Optional[float],
        net_debt_per_share:  Optional[float] = None,
        # Historical own multiples (for mean-reversion target)
        historical_pe:       Optional[List[float]] = None,
        historical_pb:       Optional[List[float]] = None,
        historical_ev_ebitda: Optional[List[float]] = None,
        confidence_inputs:   float = 0.55,
    ) -> ValuationResult:
        estimates: Dict[str, float] = {}
        weights:   Dict[str, float] = {}

        # ── P/E implied value ──────────────────────────────────────────────────
        if earnings_per_share and earnings_per_share > 0:
            target_pe = (
                assumptions.target_pe
                or safe_median(historical_pe or [])
            )
            if target_pe and target_pe > 0:
                estimates["pe"]  = earnings_per_share * target_pe
                weights["pe"]    = 0.35

        # ── EV/EBITDA implied value ────────────────────────────────────────────
        if ebitda_per_share and ebitda_per_share > 0:
            target_ev_ebitda = (
                assumptions.target_ev_ebitda
                or safe_median(historical_ev_ebitda or [])
            )
            if target_ev_ebitda and target_ev_ebitda > 0:
                # EV/share × multiple → equity per share (subtract net debt)
                nd = net_debt_per_share or 0.0
                ev_per_share = ebitda_per_share * target_ev_ebitda
                equity_per_share = ev_per_share - nd
                if equity_per_share > 0:
                    estimates["ev_ebitda"] = equity_per_share
                    weights["ev_ebitda"]   = 0.30

        # ── P/B implied value ──────────────────────────────────────────────────
        if book_value_per_share and book_value_per_share > 0:
            target_pb = (
                assumptions.target_pb
                or safe_median(historical_pb or [])
            )
            if target_pb and target_pb > 0:
                estimates["pb"]  = book_value_per_share * target_pb
                weights["pb"]    = 0.15

        # ── P/FCF implied value ────────────────────────────────────────────────
        if fcf_per_share and fcf_per_share > 0:
            target_pfcf = assumptions.target_pfcf or 20.0
            estimates["pfcf"] = fcf_per_share * target_pfcf
            weights["pfcf"]   = 0.15

        # ── EV/Sales implied value ─────────────────────────────────────────────
        if revenue_per_share and revenue_per_share > 0:
            target_ev_sales = assumptions.target_ev_sales
            if target_ev_sales and target_ev_sales > 0:
                nd = net_debt_per_share or 0.0
                estimates["ev_sales"] = revenue_per_share * target_ev_sales - nd
                weights["ev_sales"]   = 0.05

        if not estimates:
            return ValuationResult(
                model_type=ValuationModelType.RELATIVE_PE,
                status=ValuationStatus.INSUFFICIENT_DATA,
                explanation=["No basis for relative valuation (need EPS, EBITDA/share, or BV/share)"],
            )

        # ── Blend ──────────────────────────────────────────────────────────────
        blended = weighted_average(estimates, weights)

        # Confidence: higher when multiple estimates agree
        values = list(estimates.values())
        if len(values) > 1:
            spread = (max(values) - min(values)) / max(1.0, blended)
            convergence_bonus = max(0.0, 0.20 - spread * 0.10)
        else:
            convergence_bonus = 0.0

        confidence = clamp(confidence_inputs * 0.60 + convergence_bonus, 0, 0.85)

        return ValuationResult(
            model_type      = ValuationModelType.RELATIVE_PE,
            status          = ValuationStatus.COMPUTED,
            intrinsic_value = blended,
            value_low       = min(values),
            value_high      = max(values),
            confidence      = confidence,
            assumptions_used = {
                "method_estimates": {k: round(v, 2) for k, v in estimates.items()},
                "method_weights":   weights,
                "blended_value":    round(blended, 2),
                "target_pe":        assumptions.target_pe,
                "target_ev_ebitda": assumptions.target_ev_ebitda,
            },
            explanation = [
                f"Method estimates: {', '.join(f'{k}={v:.2f}' for k, v in estimates.items())}",
                f"Blended fair value: {blended:.2f}",
            ],
        )
