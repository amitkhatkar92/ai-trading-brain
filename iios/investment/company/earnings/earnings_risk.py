"""iios/investment/company/earnings/earnings_risk.py
Aggregates all risk signals into EarningsRiskProfile.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport
from iios.investment.company.earnings.earnings_snapshot import EarningsRiskProfile
from iios.investment.company.earnings.earnings_volatility import EarningsVolatilityAnalyzer
from iios.investment.company.earnings.forecast_stability import ForecastStabilityAnalyzer
from iios.investment.company.earnings.earnings_revision import EarningsRevisionTracker
from iios.investment.company.earnings.revision_tracker import RevisionSignal


class EarningsRiskAnalyzer:
    """Produces EarningsRiskProfile from history and revision signals."""

    def __init__(self) -> None:
        self._volatility = EarningsVolatilityAnalyzer()
        self._stability  = ForecastStabilityAnalyzer()

    def analyze(
        self,
        ticker:           str,
        history:          List[EarningsReport],
        revision_tracker: Optional[EarningsRevisionTracker] = None,
    ) -> EarningsRiskProfile:
        p = EarningsRiskProfile()
        if not history:
            p.flags.append("no_data")
            return p

        vol = self._volatility.analyze(history)
        stab = self._stability.analyze(history)

        p.eps_volatility    = vol.eps_growth_cv
        p.margin_volatility = vol.net_margin_stdev
        p.revenue_volatility = vol.revenue_growth_cv
        p.ocf_volatility    = vol.ocf_cv
        p.is_cyclical       = vol.cyclicality_score > 50.0

        p.consecutive_profit_years = self._consecutive_profits(history)

        # Revision signals
        if revision_tracker is not None:
            p.revision_count = revision_tracker.revision_count(ticker)
            p.revision_bias  = revision_tracker.revision_bias(ticker)
            if p.revision_count > 3:
                p.flags.append(f"high_revision_frequency:{p.revision_count}")

        # Earnings stability score (inverse of cyclicality + stability)
        revision_quality = RevisionSignal.revision_quality_score(
            revision_tracker, ticker
        ) if revision_tracker else 80.0

        p.earnings_stability_score = (
            stab.stability_score * 0.5
            + (100.0 - vol.cyclicality_score) * 0.3
            + revision_quality * 0.2
        )
        p.earnings_stability_score = max(0.0, min(100.0, p.earnings_stability_score))

        if vol.loss_rate > 0.2:
            p.flags.append(f"high_loss_rate:{vol.loss_rate:.0%}")
        if vol.net_margin_stdev and vol.net_margin_stdev > 5:
            p.flags.append("high_margin_volatility")

        return p

    @staticmethod
    def _consecutive_profits(history: List[EarningsReport]) -> int:
        count = 0
        for r in reversed(history):
            if r.is_profitable():
                count += 1
            else:
                break
        return count
