"""iios/investment/company/governance/ethics_profile.py
Accounting integrity and ethics scoring.
"""
from __future__ import annotations

from typing import Optional

from iios.investment.company.governance.management_statistics import (
    clamp, score_accruals, score_ocf_to_ni,
)
from iios.investment.company.governance.governance_events import GovernanceEventLog


def score_accounting_integrity(
    avg_accruals_ratio: Optional[float] = None,
    avg_ocf_to_ni:      Optional[float] = None,
    restatement_count:  int = 0,
    event_log:          Optional[GovernanceEventLog] = None,
) -> float:
    """
    Score accounting integrity (0-100).
    Low accruals + high OCF/NI + no restatements + no fraud incidents = high integrity.
    """
    accruals_s = score_accruals(avg_accruals_ratio)
    ocf_s      = score_ocf_to_ni(avg_ocf_to_ni)

    base = (accruals_s + ocf_s) / 2.0

    # Hard penalties
    base -= restatement_count * 20.0
    if event_log is not None:
        base -= event_log.high_severity_count * 30.0   # fraud/corruption is catastrophic

    return clamp(base, 0, 100)
