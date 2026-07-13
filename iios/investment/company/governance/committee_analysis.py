"""iios/investment/company/governance/committee_analysis.py
Board committee quality analysis.
"""
from __future__ import annotations

from iios.investment.company.governance.management_statistics import clamp
from iios.investment.company.governance.board_profile import CommitteeStructure


def score_committee_quality(committees: CommitteeStructure) -> float:
    """
    Score committee structure quality (0-100).
    Critical committees (audit, remuneration, nomination, risk) each contribute.
    Fully-independent audit committee is the most important.
    """
    score = 0.0

    # Audit committee — most critical for transparency (weight: 35)
    if committees.has_audit_committee:
        score += 25.0
        if committees.audit_committee_all_independent:
            score += 10.0
    else:
        score -= 10.0   # absence of audit committee is a major red flag

    # Remuneration committee (weight: 20)
    if committees.has_remuneration_committee:
        score += 20.0

    # Nomination committee (weight: 15)
    if committees.has_nomination_committee:
        score += 15.0

    # Risk committee (weight: 15)
    if committees.has_risk_committee:
        score += 15.0

    # ESG committee (weight: 10, emerging best practice)
    if committees.has_esg_committee:
        score += 10.0

    # Start from 15 if no data (minimum floor for unknown)
    if committees.committee_count == 0 and score == 0.0:
        score = 15.0   # unknown → below average

    return clamp(score, 0, 100)
