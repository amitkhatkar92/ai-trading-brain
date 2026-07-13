"""iios/investment/company/growth/growth_catalysts.py
Qualitative growth catalyst detection from available signals.
"""
from __future__ import annotations

from typing import List, Optional


def detect_catalysts(
    moat_score:          Optional[float] = None,   # 0-100
    moat_types:          Optional[List[str]] = None,
    revenue_trend:       str = "",
    earnings_trend:      str = "",
    margin_expanding:    Optional[bool] = None,
    resilience_score:    Optional[float] = None,   # 0-100
    is_cyclical:         Optional[bool] = None,
    avg_roic:            Optional[float] = None,
) -> List[str]:
    """
    Return a list of detected growth catalysts (plain-English labels).
    These are heuristic indicators, not guarantees.
    """
    catalysts: List[str] = []
    moat_types = moat_types or []

    # Moat-based catalysts
    if moat_score is not None and moat_score >= 70:
        catalysts.append("strong_economic_moat")
    for mtype in moat_types:
        mtype_l = mtype.lower()
        if "network" in mtype_l:
            catalysts.append("network_effects")
        if "switch" in mtype_l:
            catalysts.append("switching_costs")
        if "scale" in mtype_l or "cost" in mtype_l:
            catalysts.append("cost_advantage")

    # Margin expansion catalyst
    if margin_expanding is True:
        catalysts.append("margin_expansion")

    # High-ROIC capital deployment
    if avg_roic is not None and avg_roic >= 0.20:
        catalysts.append("high_return_capital_deployment")

    # Revenue acceleration
    if "accelerat" in revenue_trend.lower():
        catalysts.append("revenue_acceleration")

    # Resilient growth (non-cyclical, high resilience)
    if resilience_score is not None and resilience_score >= 70 and not is_cyclical:
        catalysts.append("resilient_compounding")

    return list(dict.fromkeys(catalysts))   # deduplicate while preserving order
