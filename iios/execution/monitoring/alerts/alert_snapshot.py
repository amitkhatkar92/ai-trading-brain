"""iios/execution/monitoring/alerts/alert_snapshot.py
==================================================
AlertSnapshot — immutable point-in-time snapshot of the alert state.

Consumed by M5 (Monitoring Snapshot) and downstream dashboards.

C6 Execution Intelligence — Phase 6, Module 4
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    ACTIVE_ALERT_STATUSES,
    AlertCategory,
    AlertSeverity,
    AlertStatus,
    AlertType,
    SEVERITY_WEIGHT,
    VERSION,
)


@dataclass(frozen=True)
class AlertSnapshot:
    """
    Immutable, versioned snapshot of all current alert framework state.

    Fields
    ------
    snapshot_id               : globally unique snapshot ID
    snapshot_version          : monotonic version per session_id
    session_id                : monitoring session this snapshot belongs to
    portfolio_id              : owning portfolio
    active_alert_ids          : IDs of alerts in ACTIVE/ACKNOWLEDGED/ESCALATED
    alert_counts_by_severity  : severity.value → count
    alert_counts_by_category  : category.value → count
    alert_counts_by_type      : alert_type.value → count
    alert_counts_by_status    : status.value → count
    total_active              : count of ACTIVE alerts
    total_acknowledged        : count of ACKNOWLEDGED alerts
    total_escalated           : count of ESCALATED alerts
    total_resolved            : count of RESOLVED alerts
    total_suppressed          : count of SUPPRESSED alerts
    highest_severity          : AlertSeverity.value of the most severe active alert
    created_at                : wall-time of snapshot creation
    framework_version         : framework version string
    gateway_id                : associated gateway (optional)
    strategy_id               : associated strategy (optional)
    """

    snapshot_id:              str
    snapshot_version:         int
    session_id:               str
    portfolio_id:             str
    active_alert_ids:         Tuple[str, ...]
    alert_counts_by_severity: Dict[str, int]
    alert_counts_by_category: Dict[str, int]
    alert_counts_by_type:     Dict[str, int]
    alert_counts_by_status:   Dict[str, int]
    total_active:             int
    total_acknowledged:       int
    total_escalated:          int
    total_resolved:           int
    total_suppressed:         int
    highest_severity:         Optional[str]   # AlertSeverity.value or None
    created_at:               float
    framework_version:        str

    gateway_id:  Optional[str] = None
    strategy_id: Optional[str] = None

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def has_active_alerts(self) -> bool:
        return self.total_active > 0

    @property
    def has_critical_or_above(self) -> bool:
        return bool(
            self.alert_counts_by_severity.get(AlertSeverity.CRITICAL.value, 0)
            + self.alert_counts_by_severity.get(AlertSeverity.EMERGENCY.value, 0)
        )

    @property
    def total_open(self) -> int:
        """Active + acknowledged + escalated."""
        return self.total_active + self.total_acknowledged + self.total_escalated

    def is_newer_than(self, other: "AlertSnapshot") -> bool:
        if self.session_id != other.session_id:
            return self.created_at > other.created_at
        return self.snapshot_version > other.snapshot_version

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":              self.snapshot_id,
            "snapshot_version":         self.snapshot_version,
            "session_id":               self.session_id,
            "portfolio_id":             self.portfolio_id,
            "total_active":             self.total_active,
            "total_acknowledged":       self.total_acknowledged,
            "total_escalated":          self.total_escalated,
            "total_resolved":           self.total_resolved,
            "total_suppressed":         self.total_suppressed,
            "highest_severity":         self.highest_severity,
            "alert_counts_by_severity": self.alert_counts_by_severity,
            "alert_counts_by_category": self.alert_counts_by_category,
            "alert_counts_by_type":     self.alert_counts_by_type,
            "alert_counts_by_status":   self.alert_counts_by_status,
            "created_at":               self.created_at,
            "framework_version":        self.framework_version,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ── Factory ───────────────────────────────────────────────────────────────────

def make_alert_snapshot(
    session_id:    str,
    portfolio_id:  str,
    alerts:        List[Any],   # List[Alert] (from alert_rule)
    *,
    snapshot_version: int          = 1,
    gateway_id:       Optional[str] = None,
    strategy_id:      Optional[str] = None,
    snapshot_id:      Optional[str] = None,
) -> AlertSnapshot:
    """
    Build an AlertSnapshot from a list of Alert domain objects.

    Counts all statuses; ``active_alert_ids`` contains only ACTIVE,
    ACKNOWLEDGED, and ESCALATED alerts.
    """
    counts_by_sev:    Dict[str, int] = {}
    counts_by_cat:    Dict[str, int] = {}
    counts_by_type:   Dict[str, int] = {}
    counts_by_status: Dict[str, int] = {}
    active_ids:       List[str]      = []

    total_active       = 0
    total_acknowledged = 0
    total_escalated    = 0
    total_resolved     = 0
    total_suppressed   = 0
    highest_sev_weight = 0
    highest_sev: Optional[str] = None

    for alert in alerts:
        # ── status counts ────────────────────────────────────────────────
        st = alert.status.value if hasattr(alert.status, "value") else str(alert.status)
        counts_by_status[st] = counts_by_status.get(st, 0) + 1
        if st == AlertStatus.ACTIVE.value:
            total_active += 1
            active_ids.append(alert.alert_id)
        elif st == AlertStatus.ACKNOWLEDGED.value:
            total_acknowledged += 1
            active_ids.append(alert.alert_id)
        elif st == AlertStatus.ESCALATED.value:
            total_escalated += 1
            active_ids.append(alert.alert_id)
        elif st == AlertStatus.RESOLVED.value:
            total_resolved += 1
        elif st == AlertStatus.SUPPRESSED.value:
            total_suppressed += 1
        # expired not in active_ids

        # ── severity counts ──────────────────────────────────────────────
        sv = alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity)
        counts_by_sev[sv] = counts_by_sev.get(sv, 0) + 1
        w = SEVERITY_WEIGHT.get(alert.severity, 0)
        if w > highest_sev_weight and st in (
            AlertStatus.ACTIVE.value,
            AlertStatus.ACKNOWLEDGED.value,
            AlertStatus.ESCALATED.value,
        ):
            highest_sev_weight = w
            highest_sev = sv

        # ── category counts ──────────────────────────────────────────────
        cat = alert.category.value if hasattr(alert.category, "value") else str(alert.category)
        counts_by_cat[cat] = counts_by_cat.get(cat, 0) + 1

        # ── type counts ──────────────────────────────────────────────────
        atype = alert.alert_type.value if hasattr(alert.alert_type, "value") else str(alert.alert_type)
        counts_by_type[atype] = counts_by_type.get(atype, 0) + 1

    return AlertSnapshot(
        snapshot_id              = snapshot_id or str(uuid.uuid4()),
        snapshot_version         = snapshot_version,
        session_id               = session_id,
        portfolio_id             = portfolio_id,
        active_alert_ids         = tuple(active_ids),
        alert_counts_by_severity = counts_by_sev,
        alert_counts_by_category = counts_by_cat,
        alert_counts_by_type     = counts_by_type,
        alert_counts_by_status   = counts_by_status,
        total_active             = total_active,
        total_acknowledged       = total_acknowledged,
        total_escalated          = total_escalated,
        total_resolved           = total_resolved,
        total_suppressed         = total_suppressed,
        highest_severity         = highest_sev,
        created_at               = time.time(),
        framework_version        = VERSION,
        gateway_id               = gateway_id,
        strategy_id              = strategy_id,
    )
