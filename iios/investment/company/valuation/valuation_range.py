"""iios/investment/company/valuation/valuation_range.py
Build a ValuationRange from individual model results.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.valuation.valuation_model import ValuationResult, ValuationStatus
from iios.investment.company.valuation.fair_value_estimate import ValuationRange


def build_valuation_range(
    results: List[Optional[ValuationResult]],
) -> Optional[ValuationRange]:
    """
    Combine valid model results into a single ValuationRange.
    Returns None if no valid results are provided.
    """
    values: List[float] = []
    lows:   List[float] = []
    highs:  List[float] = []

    for r in results:
        if r is None:
            continue
        if r.status != ValuationStatus.COMPUTED:
            continue
        if r.intrinsic_value is not None and r.intrinsic_value > 0:
            values.append(r.intrinsic_value)
        if r.value_low is not None and r.value_low > 0:
            lows.append(r.value_low)
        if r.value_high is not None and r.value_high > 0:
            highs.append(r.value_high)

    if not values:
        return None

    # Aggregate: mid = mean of point estimates, low/high from extremes
    mid = sum(values) / len(values)
    low = min(lows)  if lows  else mid * 0.80
    high= max(highs) if highs else mid * 1.20

    return ValuationRange(low=low, mid=mid, high=high)
