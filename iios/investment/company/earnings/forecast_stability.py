"""iios/investment/company/earnings/forecast_stability.py
Evaluates stability of earnings reporting patterns.
Not forward-looking forecasting — assesses historical reporting quality.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport
from iios.investment.company.earnings.earnings_statistics import (
    safe_stdev, _clean, linear_slope,
)


@dataclass
class ForecastStabilityMetrics:
    """
    Historical reporting stability metrics.
    Assesses how predictable past earnings have been based on historical patterns.
    """
    # EPS mean-reversion: how quickly EPS returns to trend after deviation
    eps_mean_reversion_half_life: Optional[float] = None   # periods (lower = faster reversion)

    # Earnings surprise proxy: stdev of EPS vs its trailing 2-period average
    eps_surprise_vol:    Optional[float] = None

    # Margin stability
    net_margin_stdev:    Optional[float] = None
    is_margin_stable:    bool = False   # stdev < 3pp

    # Reporting frequency
    periods_available:   int = 0
    has_gaps:            bool = False

    stability_score:     float = 50.0   # 0-100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "eps_surprise_vol":    self.eps_surprise_vol,
            "net_margin_stdev":    self.net_margin_stdev,
            "is_margin_stable":    self.is_margin_stable,
            "periods_available":   self.periods_available,
            "has_gaps":            self.has_gaps,
            "stability_score":     round(self.stability_score, 1),
        }


class ForecastStabilityAnalyzer:
    """Assesses historical earnings reporting stability."""

    _STABLE_MARGIN_STDEV = 3.0   # pp; stdev < 3pp = stable

    def analyze(self, history: List[EarningsReport]) -> ForecastStabilityMetrics:
        m = ForecastStabilityMetrics(periods_available=len(history))
        if len(history) < 3:
            m.stability_score = 50.0
            return m

        eps_vals    = [r.effective_eps() for r in history]
        net_margins = [r.net_margin for r in history]

        # EPS surprise volatility: stdev of (eps[t] - avg(eps[t-2:t]))
        eps_clean = _clean(eps_vals)
        surprises = []
        for i in range(2, len(eps_clean)):
            trailing_avg = sum(eps_clean[i-2:i]) / 2
            if trailing_avg != 0:
                surprises.append(abs(eps_clean[i] - trailing_avg) / abs(trailing_avg))
        m.eps_surprise_vol = (sum(surprises) / len(surprises)) if surprises else None

        # Net margin stdev
        m.net_margin_stdev = safe_stdev(net_margins)
        if m.net_margin_stdev is not None:
            m.is_margin_stable = m.net_margin_stdev < self._STABLE_MARGIN_STDEV

        # Stability score
        score = 80.0
        if m.eps_surprise_vol is not None:
            score -= min(40.0, m.eps_surprise_vol * 100)
        if m.net_margin_stdev is not None:
            score -= min(30.0, m.net_margin_stdev * 5)
        m.stability_score = max(0.0, min(100.0, score))

        return m
