"""iios/investment/company/ownership/executive_trading.py
Executive trading pattern analysis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.ownership.ownership_statistics import (
    clamp, score_insider_holding, pct_to_100,
)


@dataclass
class ExecutiveTradingProfile:
    """Trading behaviour and ownership stake analysis for executive team."""
    ceo_ownership_pct:       Optional[float] = None
    cfo_ownership_pct:       Optional[float] = None
    exec_team_tenure_avg:    Optional[float] = None
    esop_outstanding_pct:    Optional[float] = None
    net_exec_sentiment:      float = 0.0      # -100 to +100
    exec_buy_count_6m:       int = 0
    exec_sell_count_6m:      int = 0
    exec_holding_score:      float = 0.0      # 0-100
    exec_alignment_score:    float = 0.0      # 0-100
    explanation:             List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ceo_ownership_pct":    self.ceo_ownership_pct,
            "cfo_ownership_pct":    self.cfo_ownership_pct,
            "esop_outstanding_pct": self.esop_outstanding_pct,
            "net_exec_sentiment":   round(self.net_exec_sentiment, 1),
            "exec_buy_count_6m":    self.exec_buy_count_6m,
            "exec_sell_count_6m":   self.exec_sell_count_6m,
            "exec_holding_score":   round(self.exec_holding_score, 1),
            "exec_alignment_score": round(self.exec_alignment_score, 1),
        }


def analyze_executive_trading(insider_data: Optional[Dict]) -> ExecutiveTradingProfile:
    """
    Build ExecutiveTradingProfile from insider_data dict.
    """
    d = insider_data or {}
    profile = ExecutiveTradingProfile()

    profile.ceo_ownership_pct    = _get_pct(d, "ceo_ownership_pct")
    profile.cfo_ownership_pct    = _get_pct(d, "cfo_ownership_pct")
    profile.esop_outstanding_pct = _get_pct(d, "esop_outstanding_pct")

    profile.exec_buy_count_6m  = int(d.get("insider_buy_count_6m") or 0)
    profile.exec_sell_count_6m = int(d.get("insider_sell_count_6m") or 0)

    # Net sentiment from raw data or compute from counts
    net_buying = d.get("net_insider_buying_6m")
    if net_buying is not None:
        # Normalise to -100 to +100 based on sign and magnitude
        # We can't know the scale, so we use a sigmoid-like approach
        import math
        n = float(net_buying)
        profile.net_exec_sentiment = clamp(
            math.tanh(n / max(abs(n), 1000) * 3) * 100, -100, 100
        )
    else:
        total = profile.exec_buy_count_6m + profile.exec_sell_count_6m
        if total > 0:
            buy_ratio = profile.exec_buy_count_6m / total
            profile.net_exec_sentiment = (buy_ratio - 0.5) * 200
        else:
            profile.net_exec_sentiment = 0.0

    # Executive holding score
    ceo_s = score_insider_holding(profile.ceo_ownership_pct)
    cfo_s = score_insider_holding(profile.cfo_ownership_pct)
    if profile.ceo_ownership_pct is not None and profile.cfo_ownership_pct is not None:
        profile.exec_holding_score = ceo_s * 0.65 + cfo_s * 0.35
    elif profile.ceo_ownership_pct is not None:
        profile.exec_holding_score = ceo_s
    else:
        profile.exec_holding_score = 35.0   # insufficient data

    # Alignment score: holding + buying sentiment
    sentiment_norm = clamp((profile.net_exec_sentiment + 100) / 200 * 100)
    if profile.exec_buy_count_6m == 0 and profile.exec_sell_count_6m == 0:
        # No recent transactions
        profile.exec_alignment_score = profile.exec_holding_score * 0.80 + 50.0 * 0.20
    else:
        profile.exec_alignment_score = clamp(
            profile.exec_holding_score * 0.60 + sentiment_norm * 0.40
        )

    return profile


def _get_pct(d: Dict, key: str) -> Optional[float]:
    v = d.get(key)
    if v is None:
        return None
    return pct_to_100(float(v))
