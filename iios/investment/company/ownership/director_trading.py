"""iios/investment/company/ownership/director_trading.py
Director-level trading pattern analysis.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.company.ownership.ownership_statistics import (
    clamp, score_insider_holding, pct_to_100,
)


@dataclass
class DirectorTradingProfile:
    """Trading behaviour and board ownership analysis."""
    board_total_ownership_pct: Optional[float] = None
    board_buy_count_6m:        int = 0
    board_sell_count_6m:       int = 0
    net_director_sentiment:    float = 0.0    # -100 to +100
    board_holding_score:       float = 0.0    # 0-100
    board_conviction_score:    float = 0.0    # 0-100
    explanation:               List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "board_total_ownership_pct": self.board_total_ownership_pct,
            "board_buy_count_6m":        self.board_buy_count_6m,
            "board_sell_count_6m":       self.board_sell_count_6m,
            "net_director_sentiment":    round(self.net_director_sentiment, 1),
            "board_holding_score":       round(self.board_holding_score, 1),
            "board_conviction_score":    round(self.board_conviction_score, 1),
        }


def analyze_director_trading(insider_data: Optional[Dict]) -> DirectorTradingProfile:
    """Build DirectorTradingProfile from insider_data dict."""
    d = insider_data or {}
    profile = DirectorTradingProfile()

    v = d.get("board_total_ownership_pct")
    if v is not None:
        profile.board_total_ownership_pct = pct_to_100(float(v))

    # Director-level transaction counts (fall back to insider counts if not separately provided)
    profile.board_buy_count_6m  = int(d.get("director_buy_count_6m") or d.get("insider_buy_count_6m") or 0)
    profile.board_sell_count_6m = int(d.get("director_sell_count_6m") or d.get("insider_sell_count_6m") or 0)

    # Sentiment
    total = profile.board_buy_count_6m + profile.board_sell_count_6m
    if total > 0:
        ratio = profile.board_buy_count_6m / total
        profile.net_director_sentiment = (ratio - 0.5) * 200
    else:
        profile.net_director_sentiment = 0.0

    # Board holding score
    profile.board_holding_score = score_insider_holding(profile.board_total_ownership_pct)

    # Board conviction
    sentiment_norm = clamp((profile.net_director_sentiment + 100) / 200 * 100)
    if total == 0:
        profile.board_conviction_score = profile.board_holding_score * 0.80 + 50.0 * 0.20
    else:
        profile.board_conviction_score = clamp(
            profile.board_holding_score * 0.55 + sentiment_norm * 0.45
        )

    return profile
