"""iios/investment/company/business_quality/cyclicality.py
Cyclicality detector — how sensitive is the business to economic cycles.
"""
from __future__ import annotations

from iios.investment.company.business_quality.assessment_context import AssessmentContext
from iios.investment.company.business_quality.business_resilience import (
    CyclicalityLabel, CyclicalityProfile,
)
from iios.investment.company.business_quality.quality_statistics import clamp


class CyclicalityDetector:
    """Infers cyclicality from earnings volatility and margin behaviour."""

    def analyze(self, ctx: AssessmentContext) -> CyclicalityProfile:
        p = CyclicalityProfile()

        # Pull from earnings risk profile
        if ctx.earnings_snapshot is not None:
            try:
                risk  = ctx.earnings_snapshot.risk
                earn  = ctx.earnings_snapshot

                rev_vol    = getattr(risk, "revenue_volatility", None)
                margin_vol = getattr(risk, "margin_volatility", None)
                loss_rate  = getattr(risk, "earnings_stability_score", None)
                is_cycl    = getattr(risk, "is_cyclical", False)

                p.revenue_volatility = rev_vol
                p.margin_volatility  = margin_vol
                p.loss_rate          = getattr(risk, "earnings_stability_score", 50.0)

                # Cyclicality score: high = more cyclical
                if rev_vol is not None and margin_vol is not None:
                    raw = (rev_vol * 30 + margin_vol * 5)
                    p.cyclicality_score = clamp(raw, 0, 100)
                elif is_cycl:
                    p.cyclicality_score = 70.0
                else:
                    p.cyclicality_score = 40.0

                # Min margin (worst period)
                if hasattr(earn, "profitability"):
                    p.min_gross_margin = getattr(
                        earn.profitability, "trough_gross_margin", None
                    )

            except Exception:
                pass

        # ── Supplemental from financials ────────────────────────────────────────
        current_gm = ctx.income_metric("gross_margin") or ctx.ratio("gross_margin")
        if current_gm is not None and current_gm < 15.0:
            p.cyclicality_score = clamp(p.cyclicality_score + 15.0)
            p.flags.append("thin_margins_cyclical_risk")

        # ── Label ──────────────────────────────────────────────────────────────
        s = p.cyclicality_score
        if s < 20:
            p.label = CyclicalityLabel.DEFENSIVE
        elif s < 40:
            p.label = CyclicalityLabel.LOW_CYCLICAL
        elif s < 60:
            p.label = CyclicalityLabel.MODERATE
        else:
            p.label = CyclicalityLabel.HIGH_CYCLICAL

        return p
