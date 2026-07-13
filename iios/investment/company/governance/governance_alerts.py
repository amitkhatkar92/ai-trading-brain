"""iios/investment/company/governance/governance_alerts.py
Governance alert generation.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.company.governance.governance_events import GovernanceEventLog


def generate_alerts(
    event_log:           Optional[GovernanceEventLog] = None,
    ceo_chairman_same:   bool = False,
    is_family_controlled: bool = False,
    independence_ratio:  Optional[float] = None,
    restatement_count:   int = 0,
    key_person_risk:     float = 0.0,
    regulatory_actions:  Optional[List[str]] = None,
) -> List[str]:
    """
    Generate governance alert messages (human-readable).
    Alerts are informational, not buy/sell/hold signals.
    """
    alerts: List[str] = []

    if event_log and event_log.has_critical_events:
        alerts.append(
            f"CRITICAL: {event_log.high_severity_count} high-severity governance incident(s) recorded"
        )

    if restatement_count > 0:
        alerts.append(f"ALERT: {restatement_count} financial restatement(s) on record")

    if ceo_chairman_same:
        alerts.append("ALERT: CEO and Chairperson roles combined — governance risk elevated")

    if independence_ratio is not None and independence_ratio < 0.33:
        alerts.append(
            f"ALERT: Board independence low ({independence_ratio:.0%}) — "
            "minority shareholder protection may be insufficient"
        )

    if is_family_controlled:
        alerts.append(
            "INFO: Family-controlled company — related-party transaction monitoring recommended"
        )

    if key_person_risk >= 65.0:
        alerts.append(
            f"ALERT: Key-person risk elevated ({key_person_risk:.0f}/100) — "
            "succession planning should be evaluated"
        )

    if regulatory_actions:
        alerts.append(
            f"ALERT: {len(regulatory_actions)} regulatory action(s) on record"
        )

    return alerts
