"""iios/investment/company/growth/driver_analysis.py
Core growth driver scoring logic.
Heuristic-based; uses signals from upstream snapshots.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from iios.investment.company.growth.growth_statistics import clamp


def _score_operational_leverage(
    avg_net_margin:    Optional[float],
    current_net_margin: Optional[float],
    revenue_cagr:      Optional[float],
) -> Tuple[float, Optional[str]]:
    """
    Operational leverage: revenue growth that drops disproportionately to the bottom line.
    Signal: margins expanding faster than revenue CAGR implies operating leverage.
    """
    if None in (avg_net_margin, current_net_margin, revenue_cagr):
        return 0.0, None
    margin_improvement = current_net_margin - avg_net_margin
    if revenue_cagr > 0.05 and margin_improvement > 0.02:
        score = clamp(50.0 + margin_improvement * 500.0, 50.0, 100.0)
        return score, "operating_leverage"
    if revenue_cagr > 0.0:
        return 30.0, None
    return 0.0, None


def _score_pricing_power(
    moat_score:         Optional[float],   # 0-100
    gross_margin_exp:   Optional[float],   # bps
    avg_gross_margin:   Optional[float],
) -> Tuple[float, Optional[str]]:
    """Pricing power: ability to raise prices without volume loss."""
    score = 0.0
    if moat_score is not None:
        score += clamp(moat_score * 0.5, 0, 50)
    if gross_margin_exp is not None and gross_margin_exp > 0:
        score += clamp(gross_margin_exp / 100.0 * 10.0, 0, 30)
    if avg_gross_margin is not None and avg_gross_margin > 0.40:
        score += 20.0
    score = clamp(score, 0, 100)
    driver = "pricing_power" if score >= 60 else None
    return score, driver


def _score_market_expansion(
    revenue_cagr:     Optional[float],
    eps_cagr:         Optional[float],
    history_depth:    int,
) -> Tuple[float, Optional[str]]:
    """Market expansion: top-line growth outpacing profit growth."""
    if revenue_cagr is None:
        return 0.0, None
    if revenue_cagr > 0.15:
        score = clamp(40.0 + (revenue_cagr - 0.15) * 200, 40, 90)
        return score, "market_expansion" if score >= 60 else None
    if revenue_cagr > 0.05:
        return 35.0, None
    return 0.0, None


def _score_innovation(
    operational_quality: Optional[float],   # 0-100 from BusinessQualitySnapshot
    moat_types:          List[str],          # from moat.detected_moat_types
) -> Tuple[float, Optional[str]]:
    """Innovation score proxy from moat types and operational quality."""
    score = 0.0
    innovation_moats = {"technology", "ip", "patent", "network", "intangible"}
    for m in moat_types:
        if any(k in m.lower() for k in innovation_moats):
            score += 30.0
            break
    if operational_quality is not None:
        score += clamp(operational_quality * 0.40, 0, 40)
    score = clamp(score, 0, 100)
    driver = "innovation" if score >= 60 else None
    return score, driver


def analyse_drivers(
    avg_net_margin:       Optional[float] = None,
    current_net_margin:   Optional[float] = None,
    revenue_cagr:         Optional[float] = None,
    eps_cagr:             Optional[float] = None,
    moat_score:           Optional[float] = None,
    moat_types:           Optional[List[str]] = None,
    gross_margin_exp_bps: Optional[float] = None,
    avg_gross_margin:     Optional[float] = None,
    operational_quality:  Optional[float] = None,
    history_depth:        int = 0,
) -> Dict[str, Any]:
    """Run all driver scores and return a unified result dict."""
    moat_types = moat_types or []

    ol_score, ol_driver   = _score_operational_leverage(avg_net_margin, current_net_margin, revenue_cagr)
    pp_score, pp_driver   = _score_pricing_power(moat_score, gross_margin_exp_bps, avg_gross_margin)
    me_score, me_driver   = _score_market_expansion(revenue_cagr, eps_cagr, history_depth)
    inn_score, inn_driver = _score_innovation(operational_quality, moat_types)

    drivers = [d for d in [ol_driver, pp_driver, me_driver, inn_driver] if d]
    primary = drivers[0] if drivers else None

    # Confidence based on data availability
    available = sum(1 for v in [avg_net_margin, current_net_margin, revenue_cagr,
                                 moat_score, operational_quality] if v is not None)
    confidence = clamp(available / 5.0, 0.0, 1.0)

    return {
        "detected_drivers":           drivers,
        "primary_driver":             primary,
        "operational_leverage_score": ol_score,
        "pricing_power_score":        pp_score,
        "market_expansion_score":     me_score,
        "innovation_score":           inn_score,
        "driver_confidence":          confidence,
    }
