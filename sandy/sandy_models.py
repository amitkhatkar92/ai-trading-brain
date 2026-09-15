"""
sandy/sandy_models.py — Pure data models for Phase 7 "Sandy" supervisor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

TREND_ACTIVE     = "ACTIVE"      # new evidence since last poll
TREND_IDLE       = "IDLE"        # no new evidence for >= IDLE_THRESHOLD_DAYS
TREND_IMPROVING  = "IMPROVING"   # a quality metric moved favorably
TREND_DEGRADING  = "DEGRADING"   # a quality metric moved unfavorably
TREND_UNKNOWN    = "UNKNOWN"     # first poll, no prior snapshot to compare


@dataclass
class AgentHealthReport:
    """One agent's/phase's current health, as seen by Sandy."""
    name:              str
    category:          str                      # "SELF_LEARNING_PHASE" | "BASELINE_LOOP"
    stage:             str                       # agent-reported lifecycle label
    evidence_count:    Optional[int] = None
    last_activity_at:  Optional[str] = None
    trend:             str = TREND_UNKNOWN
    issues:            List[str] = field(default_factory=list)
    summary:           str = ""
    raw:               Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name":             self.name,
            "category":         self.category,
            "stage":            self.stage,
            "evidence_count":   self.evidence_count,
            "last_activity_at": self.last_activity_at,
            "trend":            self.trend,
            "issues":           self.issues,
            "summary":          self.summary,
        }
