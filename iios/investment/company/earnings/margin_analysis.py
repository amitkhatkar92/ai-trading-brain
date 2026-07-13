"""iios/investment/company/earnings/margin_analysis.py
Margin analysis across historical periods.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport
from iios.investment.company.earnings.earnings_statistics import (
    safe_mean, _clean, linear_slope, normalised_slope,
)


@dataclass
class MarginProfile:
    """Current and historical margin metrics."""
    # Current period
    gross_margin:   Optional[float] = None
    ebitda_margin:  Optional[float] = None
    ebit_margin:    Optional[float] = None
    net_margin:     Optional[float] = None
    fcf_margin:     Optional[float] = None

    # Historical averages
    avg_gross_margin:  Optional[float] = None
    avg_ebitda_margin: Optional[float] = None
    avg_ebit_margin:   Optional[float] = None
    avg_net_margin:    Optional[float] = None

    # Peak/trough from history
    peak_gross_margin:  Optional[float] = None
    trough_gross_margin: Optional[float] = None
    peak_net_margin:    Optional[float] = None
    trough_net_margin:  Optional[float] = None

    # vs average
    gross_vs_avg: Optional[float] = None   # current - avg
    net_vs_avg:   Optional[float] = None

    # Trend slopes (normalised)
    gross_slope:  Optional[float] = None
    net_slope:    Optional[float] = None

    is_margin_expanding: bool = False
    is_margin_contracting: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gross_margin":       self.gross_margin,
            "ebitda_margin":      self.ebitda_margin,
            "ebit_margin":        self.ebit_margin,
            "net_margin":         self.net_margin,
            "fcf_margin":         self.fcf_margin,
            "avg_gross_margin":   self.avg_gross_margin,
            "avg_ebitda_margin":  self.avg_ebitda_margin,
            "avg_net_margin":     self.avg_net_margin,
            "peak_gross_margin":  self.peak_gross_margin,
            "trough_gross_margin": self.trough_gross_margin,
            "gross_vs_avg":       self.gross_vs_avg,
            "net_vs_avg":         self.net_vs_avg,
            "gross_slope":        self.gross_slope,
            "net_slope":          self.net_slope,
            "is_margin_expanding": self.is_margin_expanding,
            "is_margin_contracting": self.is_margin_contracting,
        }


class MarginAnalyzer:
    """Analyzes margin trends from earnings history."""

    _EXPAND_THRESHOLD  = 0.02    # normalised slope > 2% per period = expanding
    _CONTRACT_THRESHOLD = -0.02  # normalised slope < -2% = contracting

    def analyze(
        self,
        history: List[EarningsReport],
        latest: Optional[EarningsReport] = None,
    ) -> MarginProfile:
        m = MarginProfile()
        latest = latest or (history[-1] if history else None)

        if latest:
            m.gross_margin  = latest.gross_margin
            m.ebitda_margin = latest.ebitda_margin
            m.ebit_margin   = latest.ebit_margin
            m.net_margin    = latest.net_margin
            m.fcf_margin    = latest.fcf_margin

        if not history:
            return m

        # Historical averages
        m.avg_gross_margin  = safe_mean([r.gross_margin  for r in history])
        m.avg_ebitda_margin = safe_mean([r.ebitda_margin for r in history])
        m.avg_ebit_margin   = safe_mean([r.ebit_margin   for r in history])
        m.avg_net_margin    = safe_mean([r.net_margin    for r in history])

        # Peak/trough
        gm = _clean([r.gross_margin for r in history])
        nm = _clean([r.net_margin   for r in history])
        if gm:
            m.peak_gross_margin   = max(gm)
            m.trough_gross_margin = min(gm)
        if nm:
            m.peak_net_margin   = max(nm)
            m.trough_net_margin = min(nm)

        # vs average
        if m.gross_margin is not None and m.avg_gross_margin is not None:
            m.gross_vs_avg = m.gross_margin - m.avg_gross_margin
        if m.net_margin is not None and m.avg_net_margin is not None:
            m.net_vs_avg = m.net_margin - m.avg_net_margin

        # Slopes
        if len(gm) >= 3:
            m.gross_slope = normalised_slope(gm)
        if len(nm) >= 3:
            m.net_slope = normalised_slope(nm)

        # Expansion / contraction flags
        if m.net_slope is not None:
            m.is_margin_expanding   = m.net_slope > self._EXPAND_THRESHOLD
            m.is_margin_contracting = m.net_slope < self._CONTRACT_THRESHOLD

        return m
