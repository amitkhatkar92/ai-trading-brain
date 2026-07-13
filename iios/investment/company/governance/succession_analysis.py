"""iios/investment/company/governance/succession_analysis.py
Succession planning quality analysis.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.governance.management_statistics import clamp


def score_succession_quality(
    ceo_tenure_years:     Optional[float] = None,
    avg_director_tenure:  Optional[float] = None,
    has_nomination_committee: bool = False,
    is_founder_led:       bool = False,
    executive_team_size:  int = 0,
    leadership_changes_3y: int = 0,
) -> float:
    """
    Estimate succession planning quality (0-100).
    Higher = better succession preparedness.
    
    Succession is estimated from structural signals, not direct disclosure.
    Having a nomination committee, deep executive team, and board with
    mixed tenures indicates a succession-conscious governance structure.
    """
    score = 50.0  # neutral baseline

    # Nomination committee → formal succession process
    if has_nomination_committee:
        score += 20.0

    # Deep executive bench
    if executive_team_size >= 5:
        score += 15.0
    elif executive_team_size >= 3:
        score += 5.0
    elif executive_team_size == 1:
        score -= 15.0  # single-person dependency

    # Founder-led without nomination committee → high succession risk
    if is_founder_led and not has_nomination_committee:
        score -= 15.0

    # Board tenure diversity (older + newer directors)
    if avg_director_tenure is not None:
        if 4 <= avg_director_tenure <= 8:
            score += 10.0  # good mix of institutional memory and fresh perspective

    # Recent leadership changes can indicate planned succession
    if leadership_changes_3y == 1:
        score += 0.0   # single planned succession = neutral
    elif leadership_changes_3y >= 3:
        score -= 15.0  # chaotic changes = poor planning

    return clamp(score, 0, 100)
