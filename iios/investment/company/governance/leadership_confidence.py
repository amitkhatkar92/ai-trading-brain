"""iios/investment/company/governance/leadership_confidence.py
Overall confidence scoring for ManagementSnapshot.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.governance.management_statistics import clamp


def compute_leadership_confidence(
    has_board_data:      bool,
    has_executive_data:  bool,
    has_earnings_quality: bool,
    has_financial_data:  bool,
    history_depth:       int,
    has_incidents_data:  bool,
    governance_standard: str = "generic",
) -> float:
    """
    Compute a 0-1 confidence for the ManagementSnapshot.
    Confidence reflects data completeness, not management quality.
    """
    score = 0.0

    # Core data sources
    if has_board_data:       score += 0.25
    if has_executive_data:   score += 0.20
    if has_earnings_quality: score += 0.25
    if has_financial_data:   score += 0.15

    # History depth
    if history_depth >= 8:
        score += 0.10
    elif history_depth >= 4:
        score += 0.05

    # Incidents data availability (even if no incidents — knowing that matters)
    if has_incidents_data:
        score += 0.05

    return clamp(score, 0.0, 1.0)
