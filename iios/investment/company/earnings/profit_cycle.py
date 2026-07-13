"""iios/investment/company/earnings/profit_cycle.py
Detects the current phase of the profitability cycle.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.earnings.earnings_report import EarningsReport, ProfitCyclePhase
from iios.investment.company.earnings.earnings_statistics import (
    safe_mean, _clean, linear_slope,
)


def detect_profit_cycle(
    history: List[EarningsReport],
    field: str = "net_margin",
    lookback: int = 6,
) -> ProfitCyclePhase:
    """
    Detect profit cycle phase using field's position relative to history.

    Logic:
    - Compare current value to historical average
    - Check if slope is positive or negative
    → 4 quadrants: above_avg+rising, above_avg+falling, below_avg+rising, below_avg+falling
    → Map to: PEAK, CONTRACTION, RECOVERY, TROUGH
    """
    if not history or len(history) < 3:
        return ProfitCyclePhase.UNKNOWN

    values = _clean([getattr(r, field, None) for r in history])
    if len(values) < 3:
        return ProfitCyclePhase.UNKNOWN

    current   = values[-1]
    hist_avg  = sum(values) / len(values)
    lookback_window = values[-min(lookback, len(values)):]

    slope = linear_slope(lookback_window)

    above_avg = current > hist_avg
    rising    = slope > 0

    # Check slope magnitude relative to mean (avoid noise)
    slope_significant = abs(slope) > abs(hist_avg) * 0.05 if hist_avg != 0 else abs(slope) > 0.001

    if above_avg and rising:
        return ProfitCyclePhase.EXPANSION
    if above_avg and not rising and slope_significant:
        return ProfitCyclePhase.PEAK
    if not above_avg and not rising and slope_significant:
        return ProfitCyclePhase.CONTRACTION
    if not above_avg and not rising:
        return ProfitCyclePhase.TROUGH
    if not above_avg and rising:
        return ProfitCyclePhase.RECOVERY

    return ProfitCyclePhase.UNKNOWN
