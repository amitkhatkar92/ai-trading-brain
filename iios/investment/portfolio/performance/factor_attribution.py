"""iios/investment/portfolio/performance/factor_attribution.py

Factor exposure and contribution attribution.

Factors: growth, value, quality, momentum, low_vol, size
Each factor score is extracted from position metadata (conviction,
risk_score, liquidity, confidence).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.performance.performance_types import (
    PerformancePosition, EQUITY_PREMIUM_PROXY,
)


# ---------------------------------------------------------------------------
# Expected annual factor return proxies (Indian market estimates)
# ---------------------------------------------------------------------------
FACTOR_RETURNS: Dict[str, float] = {
    "quality":   0.030,   # high-quality factor premium
    "momentum":  0.035,   # momentum factor premium
    "low_vol":   0.020,   # low-volatility factor premium
    "value":     0.025,   # value factor premium
    "growth":    0.020,   # growth factor premium
    "size":     -0.005,   # size effect (negative for small-cap disadvantage)
}


@dataclass(frozen=True)
class FactorAttributionRecord:
    """Attribution for a single factor."""

    factor_name:    str
    exposure:       float = 0.0   # weighted avg exposure [-1, 1]
    factor_return:  float = 0.0   # expected annual factor return (proxy)
    contribution:   float = 0.0   # exposure × factor_return
    n_positions:    int   = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_name":   self.factor_name,
            "exposure":      round(self.exposure, 4),
            "factor_return": round(self.factor_return, 4),
            "contribution":  round(self.contribution, 4),
        }


@dataclass(frozen=True)
class FactorAttribution:
    """Factor attribution result."""

    result_id:          str   = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:       str   = ""
    total_contribution: float = 0.0
    records:            tuple = field(default_factory=tuple)
    dominant_factor:    str   = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_contribution": round(self.total_contribution, 4),
            "dominant_factor":    self.dominant_factor,
            "records":            [r.to_dict() for r in self.records],
        }


def compute_factor_attribution(
    positions:    List[PerformancePosition],
    portfolio_id: str = "",
) -> FactorAttribution:
    if not positions:
        return FactorAttribution(portfolio_id=portfolio_id)

    total_w = sum(p.weight for p in positions)
    if total_w <= 0:
        total_w = 1.0

    # Build weighted exposures per factor
    factor_exposure: Dict[str, float] = {}

    for p in positions:
        w    = p.weight / total_w
        exp  = _factor_exposures(p)
        for fname, e in exp.items():
            factor_exposure[fname] = factor_exposure.get(fname, 0.0) + w * e

    records: List[FactorAttributionRecord] = []
    for fname, exposure in factor_exposure.items():
        fr  = FACTOR_RETURNS.get(fname, 0.01)
        con = exposure * fr
        records.append(FactorAttributionRecord(
            factor_name   = fname,
            exposure      = round(exposure, 4),
            factor_return = round(fr, 4),
            contribution  = round(con, 6),
            n_positions   = len(positions),
        ))

    records_sorted = sorted(records, key=lambda r: abs(r.contribution), reverse=True)
    total_contr    = sum(r.contribution for r in records)
    dominant       = records_sorted[0].factor_name if records_sorted else ""

    return FactorAttribution(
        portfolio_id       = portfolio_id,
        total_contribution = round(total_contr, 6),
        records            = tuple(records_sorted),
        dominant_factor    = dominant,
    )


def _factor_exposures(p: PerformancePosition) -> Dict[str, float]:
    """Map position attributes to factor exposures in [-1, 1]."""
    # quality: high conviction + high confidence = quality stock
    quality = (p.conviction - 0.5) * 2 * 0.5 + (p.confidence - 0.5)
    quality = max(-1.0, min(1.0, quality))

    # momentum: period return vs expected (positive = momentum)
    expected_period = p.expected_return_annual / 12.0 if p.expected_return_annual else 0.0
    momentum = (p.period_return - expected_period) * 5.0
    momentum = max(-1.0, min(1.0, momentum))

    # low_vol: low risk score → high low-vol exposure
    low_vol = 1.0 - p.risk_score

    # value: risk_score > avg, conviction > avg → cheap stock
    value = (p.risk_score - 0.5) * 0.5 + (p.conviction - 0.5) * 0.5
    value = max(-1.0, min(1.0, value))

    # growth: high conviction, high expected return
    growth = max(0.0, (p.conviction - 0.5) * 2)

    # size: liquidity proxy — low liquidity implies small-cap
    size = -(1.0 - p.liquidity)   # negative: small-cap drag

    return {
        "quality":  quality,
        "momentum": momentum,
        "low_vol":  low_vol,
        "value":    value,
        "growth":   growth,
        "size":     size,
    }
