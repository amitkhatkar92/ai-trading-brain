"""iios/investment/company/growth/margin_growth.py
Margin expansion / contraction analysis engine.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.growth.growth_profile import (
    MarginGrowthProfile, GrowthTrend,
)
from iios.investment.company.growth.growth_statistics import (
    clamp, safe_mean,
)


class MarginGrowthEngine:
    """
    Compute margin expansion intelligence from upstream snapshots.

    Margin expansion (in basis points):
        current_margin - avg_margin   (+ = expanding)
    Annualised expansion rate = delta_bps / history_depth
    """

    def compute(
        self,
        current_net_margin:   Optional[float] = None,  # profitability.net_margin
        avg_net_margin:       Optional[float] = None,  # profitability.avg_net_margin
        current_gross_margin: Optional[float] = None,  # profitability.avg_gross_margin (most recent)
        avg_gross_margin:     Optional[float] = None,  # profitability.avg_gross_margin
        margin_volatility:    Optional[float] = None,  # risk.margin_volatility
        history_depth:        int = 0,
    ) -> MarginGrowthProfile:
        profile = MarginGrowthProfile()
        explanation: List[str] = []

        # ── Net margin expansion ────────────────────────────────────────────────
        if current_net_margin is not None and avg_net_margin is not None:
            delta_pct = current_net_margin - avg_net_margin          # e.g. 0.02 = 2pp
            profile.net_margin_expansion_bps = delta_pct * 10_000.0 # in bps
            profile.current_net_margin       = current_net_margin
            profile.avg_net_margin           = avg_net_margin

            annual_bps = (profile.net_margin_expansion_bps / history_depth
                          if history_depth > 0 else profile.net_margin_expansion_bps)

            if delta_pct > 0.005:
                profile.is_expanding   = True
                profile.is_contracting = False
                profile.trend          = GrowthTrend.ACCELERATING
                explanation.append(
                    f"Net margin expanding: {current_net_margin:.1%} vs avg {avg_net_margin:.1%} "
                    f"(+{profile.net_margin_expansion_bps:.0f}bps total, "
                    f"+{annual_bps:.0f}bps/yr over {history_depth} periods)"
                )
            elif delta_pct < -0.005:
                profile.is_expanding   = False
                profile.is_contracting = True
                profile.trend          = GrowthTrend.DECELERATING
                explanation.append(
                    f"Net margin contracting: {current_net_margin:.1%} vs avg {avg_net_margin:.1%} "
                    f"({profile.net_margin_expansion_bps:.0f}bps total)"
                )
            else:
                profile.is_expanding   = False
                profile.is_contracting = False
                profile.trend          = GrowthTrend.STABLE
                explanation.append("Net margin stable (within 50bps of historical average)")
        else:
            profile.current_net_margin = current_net_margin
            profile.avg_net_margin     = avg_net_margin
            explanation.append("Insufficient net margin data")

        # ── Gross margin expansion ──────────────────────────────────────────────
        if current_gross_margin is not None and avg_gross_margin is not None:
            gross_delta = current_gross_margin - avg_gross_margin
            profile.gross_margin_expansion_bps = gross_delta * 10_000.0
            profile.current_gross_margin        = current_gross_margin
            profile.avg_gross_margin            = avg_gross_margin
            if gross_delta > 0.005:
                explanation.append(
                    f"Gross margin expanding: +{profile.gross_margin_expansion_bps:.0f}bps"
                )
            elif gross_delta < -0.005:
                explanation.append(
                    f"Gross margin contracting: {profile.gross_margin_expansion_bps:.0f}bps"
                )

        # ── Volatility indicator ────────────────────────────────────────────────
        if margin_volatility is not None and margin_volatility > 0.5:
            profile.trend = GrowthTrend.VOLATILE
            explanation.append(f"Margin volatility elevated (CV={margin_volatility:.2f})")

        profile.explanation = explanation
        return profile
