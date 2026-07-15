"""iios/investment/portfolio/risk/tail_risk.py

Tail risk analysis: skewness/kurtosis proxies, expected shortfall at extreme
confidence levels, black-swan probability estimate.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from iios.investment.portfolio.risk.risk_types import (
    NORMAL_Z_95, NORMAL_Z_99, NORMAL_Z_999,
    RiskLevel, cvar_parametric, portfolio_volatility,
    var_parametric, weighted_average, risk_score_to_level,
    RiskPosition,
)


@dataclass(frozen=True)
class TailRiskResult:
    """Tail risk metrics: fat-tail exposure, extreme loss estimation."""

    result_id:              str       = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:           str       = ""

    # Tail measures (daily, as fraction of portfolio)
    var_99_1d:              float     = 0.0
    var_999_1d:             float     = 0.0
    cvar_99_1d:             float     = 0.0   # 99% Expected Shortfall
    cvar_95_1d:             float     = 0.0   # 95% Expected Shortfall

    # Skewness proxy: high-risk + concentrated → negative skew
    skewness_proxy:         float     = 0.0   # negative = left-skewed (bad tails)

    # Excess kurtosis proxy: concentrated high-risk → fat tails
    excess_kurtosis_proxy:  float     = 0.0   # positive = fat tails

    # Black swan impact: extreme 5-sigma event
    black_swan_1pct_loss:   float     = 0.0   # 1% probability event loss

    # Tail contribution: which positions contribute most to tail risk
    top_tail_contributor:   str       = ""
    top_tail_weight:        float     = 0.0

    # Systemic risk proxy: avg correlation × portfolio vol
    systemic_risk_proxy:    float     = 0.0

    risk_level:             RiskLevel = RiskLevel.MODERATE
    warnings:               tuple     = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "var_99_1d":             round(self.var_99_1d, 4),
            "var_999_1d":            round(self.var_999_1d, 4),
            "cvar_99_1d":            round(self.cvar_99_1d, 4),
            "cvar_95_1d":            round(self.cvar_95_1d, 4),
            "skewness_proxy":        round(self.skewness_proxy, 4),
            "excess_kurtosis_proxy": round(self.excess_kurtosis_proxy, 4),
            "black_swan_1pct_loss":  round(self.black_swan_1pct_loss, 4),
            "systemic_risk_proxy":   round(self.systemic_risk_proxy, 4),
            "risk_level":            self.risk_level.value,
            "warnings":              list(self.warnings),
        }


def analyze_tail_risk(
    positions:    List[RiskPosition],
    portfolio_id: str = "",
) -> TailRiskResult:
    if not positions:
        return TailRiskResult(portfolio_id=portfolio_id)

    port_vol = portfolio_volatility(positions)
    avg_risk = weighted_average(positions, "risk_score")
    avg_liq  = weighted_average(positions, "liquidity")

    # Parametric VaR / CVaR at multiple confidence levels
    v99    = var_parametric(port_vol, NORMAL_Z_99, 1)
    v999   = var_parametric(port_vol, NORMAL_Z_999, 1)
    es99   = cvar_parametric(port_vol, NORMAL_Z_99, 1)
    es95   = cvar_parametric(port_vol, NORMAL_Z_95, 1)

    # Black swan: 5-sigma daily event
    bs_loss = 5.0 * port_vol / math.sqrt(252)

    # Skewness proxy: high avg_risk + low liquidity → negative skew
    # Concentrated + high-risk positions tend to have left-fat tails
    skewness = -(avg_risk * 0.6 + (1.0 - avg_liq) * 0.4) * 2.0

    # Excess kurtosis proxy: concentrated positions → fat tails
    top_w = max(p.weight for p in positions)
    kurtosis = max(0.0, top_w * 6.0 + avg_risk * 3.0 - 1.5)

    # Systemic risk: correlated loss amplification
    # Proxy: avg pairwise correlation × portfolio vol
    from iios.investment.portfolio.risk.risk_types import CORR_SAME_SECTOR
    n = len(positions)
    if n > 1:
        same_sector_pairs = sum(
            1 for i in range(n) for j in range(i + 1, n)
            if positions[i].sector and positions[i].sector == positions[j].sector
        )
        total_pairs = n * (n - 1) // 2
        avg_corr_proxy = 0.10 + (same_sector_pairs / max(total_pairs, 1)) * 0.45
    else:
        avg_corr_proxy = 1.0
    systemic = avg_corr_proxy * port_vol

    # Top tail contributor: position with highest weight × risk_score
    top_pos = max(positions, key=lambda p: p.weight * p.risk_score)

    # Risk level: driven by CVaR and kurtosis
    raw_risk = min(1.0, es99 / 0.10 + kurtosis / 10.0) * 0.7 + avg_risk * 0.3
    risk_level = risk_score_to_level(min(1.0, raw_risk))

    warnings = []
    if v999 >= 0.08:
        warnings.append(f"Extreme tail risk: 99.9% 1-day VaR at {v999:.1%}")
    if skewness < -1.0:
        warnings.append(f"High left-tail skew (fat bad-tail): {skewness:.2f}")
    if kurtosis > 3.0:
        warnings.append(f"Fat-tailed distribution proxy (excess kurtosis {kurtosis:.2f})")
    if bs_loss >= 0.10:
        warnings.append(f"Black swan 5-sigma event could lose {bs_loss:.1%}")

    return TailRiskResult(
        portfolio_id          = portfolio_id,
        var_99_1d             = round(v99, 6),
        var_999_1d            = round(v999, 6),
        cvar_99_1d            = round(es99, 6),
        cvar_95_1d            = round(es95, 6),
        skewness_proxy        = round(skewness, 4),
        excess_kurtosis_proxy = round(kurtosis, 4),
        black_swan_1pct_loss  = round(bs_loss, 4),
        top_tail_contributor  = top_pos.symbol,
        top_tail_weight       = round(top_pos.weight, 4),
        systemic_risk_proxy   = round(systemic, 6),
        risk_level            = risk_level,
        warnings              = tuple(warnings),
    )
