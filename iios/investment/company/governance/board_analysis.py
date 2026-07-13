"""iios/investment/company/governance/board_analysis.py
Board of Directors quality analysis.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.governance.management_statistics import (
    clamp, score_board_independence,
)
from iios.investment.company.governance.board_profile import BoardComposition
from iios.investment.company.governance.management_profile import BoardIndependenceLevel


def score_board_independence_full(
    board: BoardComposition,
    ceo_chairman_same: bool = False,
) -> float:
    """Detailed board independence score (0-100)."""
    base = score_board_independence(board.independence_ratio)
    if ceo_chairman_same:
        base -= 15.0   # CEO/Chairman duality is a governance concern
    return clamp(base, 0, 100)


def score_board_diversity(board: BoardComposition) -> float:
    """Board diversity score — gender diversity + tenure mix."""
    score = 50.0   # neutral baseline

    # Gender diversity
    if board.female_ratio is not None:
        if board.female_ratio >= 0.33:
            score += 25.0
        elif board.female_ratio >= 0.20:
            score += 15.0
        elif board.female_ratio >= 0.10:
            score += 5.0
        else:
            score -= 10.0

    # Tenure diversity proxy: avg tenure in 3-10yr range is ideal
    if board.avg_director_tenure_years is not None:
        t = board.avg_director_tenure_years
        if 3 <= t <= 10:
            score += 20.0
        elif 1 <= t < 3 or 10 < t <= 15:
            score += 8.0
        else:
            score -= 5.0

    return clamp(score, 0, 100)


def score_board_size(total_directors: int) -> float:
    """
    Score board size.
    Optimal: 7-12 members (per governance best practice).
    Too small (<5) = concentration risk; too large (>15) = ineffective.
    """
    if total_directors == 0:
        return 0.0
    if 7 <= total_directors <= 12:
        return 85.0
    if 5 <= total_directors < 7 or 12 < total_directors <= 15:
        return 65.0
    if total_directors < 5:
        return 40.0
    return 40.0  # >15 members
