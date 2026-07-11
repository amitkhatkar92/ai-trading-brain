"""iios/investment/market/breadth/leadership_analysis.py
Identifies leading and lagging sectors from ParticipationSnapshot.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from iios.investment.market.breadth.models import ParticipationSnapshot


def identify_leaders_and_laggers(
    participation: ParticipationSnapshot,
    top_n: int = 5,
) -> Tuple[List[str], List[str]]:
    """
    Returns (leading_sectors, lagging_sectors).

    Leading:  sectors with above-average participation rate.
    Lagging:  sectors with below-average participation rate.
    """
    sector_map = participation.sector_participation
    if not sector_map:
        return [], []

    avg_participation = sum(sector_map.values()) / len(sector_map)
    sorted_sectors = sorted(sector_map.items(), key=lambda x: x[1], reverse=True)

    leaders = [s for s, v in sorted_sectors if v > avg_participation][:top_n]
    laggers = [s for s, v in sorted_sectors if v < avg_participation][:top_n]
    return leaders, laggers


def leadership_breadth(
    participation: ParticipationSnapshot,
) -> Tuple[float, float]:
    """
    Returns (leadership_breadth, lagging_breadth) as fractions of
    total sectors.
    """
    sector_map = participation.sector_participation
    n = len(sector_map)
    if n == 0:
        return 0.0, 0.0
    avg = sum(sector_map.values()) / n
    leaders = sum(1 for v in sector_map.values() if v > avg)
    laggers  = sum(1 for v in sector_map.values() if v < avg)
    return leaders / n, laggers / n


def participation_quality(
    participation: ParticipationSnapshot,
    prev_participation: Optional[ParticipationSnapshot] = None,
) -> float:
    """
    0-1 score representing the quality and breadth of participation.

    Considers:
    - Fraction of sectors participating (participation_breadth)
    - MA positioning (above_ma20_pct)
    - Cap-tier alignment (large/mid/small advancing together)
    """
    part_b     = participation.participation_breadth
    ma_factor  = participation.above_ma20_pct
    cap_align  = _cap_tier_alignment(participation)

    quality = part_b * 0.40 + ma_factor * 0.35 + cap_align * 0.25
    return max(0.0, min(1.0, quality))


def _cap_tier_alignment(participation: ParticipationSnapshot) -> float:
    """Measures how aligned large/mid/small-cap participation is."""
    vals = [
        v for v in [
            participation.large_cap_pct,
            participation.mid_cap_pct,
            participation.small_cap_pct,
        ]
        if v > 0
    ]
    if not vals:
        return 0.5
    avg = sum(vals) / len(vals)
    spread = max(vals) - min(vals)
    # High alignment = low spread relative to mean
    return 1.0 / (1.0 + spread / max(avg, 1e-8))
