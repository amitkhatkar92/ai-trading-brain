"""iios/investment/company/governance/governance_events.py
Governance events / incidents tracking and severity scoring.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Known high-severity incident keywords
_HIGH_SEVERITY = {
    "fraud", "accounting_fraud", "accounting_irregularity", "bribery",
    "corruption", "embezzlement", "securities_violation", "insider_trading",
    "money_laundering",
}

_MEDIUM_SEVERITY = {
    "accounting_issue", "restatement", "regulatory_penalty", "sebi_action",
    "sec_action", "governance_concern", "related_party", "whistleblower",
}

_LOW_SEVERITY = {
    "minor_penalty", "late_filing", "disclosure_violation", "data_breach",
    "environmental_violation",
}


@dataclass
class GovernanceEvent:
    """A recorded governance event or incident."""
    event_type:  str
    severity:    str   # "high" | "medium" | "low"
    description: str = ""


@dataclass
class GovernanceEventLog:
    """Aggregated governance event history."""
    events:            List[GovernanceEvent] = field(default_factory=list)
    high_severity_count:   int = 0
    medium_severity_count: int = 0
    low_severity_count:    int = 0
    total_count:           int = 0
    has_critical_events:   bool = False
    reputation_penalty:    float = 0.0   # 0-100; higher = more damage

    def to_dict(self) -> Dict[str, Any]:
        return {
            "high_severity_count":   self.high_severity_count,
            "medium_severity_count": self.medium_severity_count,
            "low_severity_count":    self.low_severity_count,
            "total_count":          self.total_count,
            "has_critical_events":  self.has_critical_events,
            "reputation_penalty":   round(self.reputation_penalty, 1),
        }


def classify_events(incidents: Optional[List[str]]) -> GovernanceEventLog:
    """
    Classify a list of incident strings into a GovernanceEventLog.
    Input items are plain-language strings from caller-provided board_info.
    """
    log = GovernanceEventLog()
    if not incidents:
        return log

    for item in incidents:
        item_l = item.lower().replace(" ", "_")
        if any(k in item_l for k in _HIGH_SEVERITY):
            sev = "high"
            log.high_severity_count += 1
        elif any(k in item_l for k in _MEDIUM_SEVERITY):
            sev = "medium"
            log.medium_severity_count += 1
        else:
            sev = "low"
            log.low_severity_count += 1
        log.events.append(GovernanceEvent(event_type=item, severity=sev))

    log.total_count = len(log.events)
    log.has_critical_events = log.high_severity_count > 0

    # Penalty: 30 per high, 15 per medium, 5 per low
    penalty = (
        log.high_severity_count   * 30.0
        + log.medium_severity_count * 15.0
        + log.low_severity_count    * 5.0
    )
    log.reputation_penalty = min(penalty, 100.0)
    return log
