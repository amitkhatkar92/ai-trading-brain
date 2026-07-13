"""iios/investment/company/governance/key_person_risk.py
Key person risk assessment.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.governance.management_statistics import clamp


def score_key_person_risk(
    ceo_tenure_years:    Optional[float] = None,
    is_founder_led:      bool = False,
    cfo_tenure_years:    Optional[float] = None,
    executive_team_size: int = 0,
    leadership_changes_3y: int = 0,
) -> float:
    """
    Compute key person risk score (0-100).
    Higher = more risky.
    
    Risk is elevated when:
    - Very long-tenured founder CEO (succession unclear)
    - Only one dominant executive
    - Frequent leadership changes
    """
    risk = 30.0   # moderate base risk

    # Founder CEO: high impact if they leave
    if is_founder_led:
        risk += 20.0
        # Very long tenure amplifies key person risk
        if ceo_tenure_years is not None and ceo_tenure_years > 20:
            risk += 10.0

    # Short-tenured CEO is a transition risk
    if ceo_tenure_years is not None and ceo_tenure_years < 2:
        risk += 15.0

    # CFO instability
    if cfo_tenure_years is not None and cfo_tenure_years < 2:
        risk += 10.0

    # Small team = high concentration
    if executive_team_size > 0 and executive_team_size < 3:
        risk += 15.0

    # Frequent changes = organisational instability
    if leadership_changes_3y >= 3:
        risk += 20.0
    elif leadership_changes_3y == 2:
        risk += 10.0

    return clamp(risk, 0, 100)
