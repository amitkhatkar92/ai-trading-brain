"""iios/investment/company/governance/compliance_tracker.py
Regulatory compliance tracking and scoring.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.governance.management_statistics import clamp
from iios.investment.company.governance.governance_events import GovernanceEventLog


def score_compliance(
    event_log:           Optional[GovernanceEventLog] = None,
    regulatory_actions:  Optional[List[str]] = None,
    governance_standard: str = "generic",
) -> float:
    """
    Compute a compliance score (0-100).
    Clean regulatory record = high score.
    """
    score = 90.0

    if event_log is not None:
        score -= event_log.high_severity_count   * 25.0
        score -= event_log.medium_severity_count * 10.0
        score -= event_log.low_severity_count    * 3.0

    if regulatory_actions:
        score -= len(regulatory_actions) * 8.0

    return clamp(score, 0, 100)
