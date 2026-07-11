"""iios/investment/market/breadth/internal_strength.py
Internal market strength calculation from breadth and participation data.
"""
from __future__ import annotations

from iios.investment.market.breadth.models import BreadthData, ParticipationSnapshot


def internal_strength_score(
    breadth: BreadthData,
    participation: ParticipationSnapshot,
) -> float:
    """
    0-1 composite internal strength score.

    Weights:
      breadth_pct       0.30
      above_ma20_pct    0.25
      above_ma50_pct    0.15
      nh_nl_normalized  0.15
      ad_ratio_norm     0.15
    """
    nh_nl_norm   = participation.nh_nl_ratio / (1.0 + participation.nh_nl_ratio)
    ad_ratio_norm = breadth.ad_ratio / (1.0 + breadth.ad_ratio)

    score = (
        breadth.breadth_pct               * 0.30
        + participation.above_ma20_pct    * 0.25
        + participation.above_ma50_pct    * 0.15
        + nh_nl_norm                      * 0.15
        + ad_ratio_norm                   * 0.15
    )
    return max(0.0, min(1.0, score))


def internal_momentum(
    current_breadth: BreadthData,
    prev_breadth_pct: float,
) -> float:
    """
    Rate of change of internal strength.  Returns value in [-1, 1].
    """
    delta = current_breadth.breadth_pct - prev_breadth_pct
    return max(-1.0, min(1.0, delta / 0.30))
