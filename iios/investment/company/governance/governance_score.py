"""iios/investment/company/governance/governance_score.py
Governance-specific score computation (for query APIs).
"""
from __future__ import annotations

from iios.investment.company.governance.management_statistics import clamp


def compute_governance_score(
    board_independence_score:     float = 0.0,
    board_diversity_score:        float = 0.0,
    committee_quality_score:      float = 0.0,
    shareholder_protection_score: float = 0.0,
    governance_structure_score:   float = 0.0,
) -> float:
    """
    Standalone governance-only score (0-100).
    Mirrors the weighting inside GovernanceAnalysisEngine.
    """
    return clamp(
        board_independence_score      * 0.30
        + board_diversity_score       * 0.20
        + committee_quality_score     * 0.25
        + shareholder_protection_score * 0.15
        + governance_structure_score  * 0.10,
        0.0, 100.0,
    )
