"""iios/investment/market/sector_rotation/relative_strength_score.py
Relative strength score computation for a single sector or security.
"""
from __future__ import annotations

from iios.investment.market.sector_rotation.models import RelativeStrengthScore

_EPSILON = 1e-9


def compute_rs_score(
    symbol: str,
    vs_benchmark: float,   # raw excess return vs benchmark over lookback
    vs_group: float,       # excess return vs peer group (sector avg or index)
    rank: int,
    total: int,
) -> RelativeStrengthScore:
    """Compute a :class:`RelativeStrengthScore` from raw relative-return inputs.

    Composite score (0-100) emphasises benchmark-relative strength (60%) and
    intra-group rank (40%).
    """
    # Map raw excess return to 0-100: ±10% excess → ±50 points from centre
    benchmark_component = 50.0 + max(-50.0, min(50.0, vs_benchmark * 500.0))
    group_component     = 50.0 + max(-50.0, min(50.0, vs_group * 500.0))

    composite = benchmark_component * 0.6 + group_component * 0.4

    percentile = 1.0 - (rank - 1) / max(total - 1, 1)

    return RelativeStrengthScore(
        symbol=symbol,
        vs_benchmark=vs_benchmark,
        vs_group=vs_group,
        composite=composite,
        rank=rank,
        percentile=percentile,
    )
