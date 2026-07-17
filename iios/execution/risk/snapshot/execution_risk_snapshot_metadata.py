"""iios/execution/risk/snapshot/execution_risk_snapshot_metadata.py
==================================================
Metadata value objects for ExecutionRiskSnapshot.

Defines three frozen dataclasses:
  AuditMetadata    — who created/published/archived the snapshot
  RiskMetadata     — aggregate risk statistics
  OverrideMetadata — override details if a control decision was overridden

C6 Execution Intelligence — Phase 4, Module 5
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class AuditMetadata:
    """Audit trail for a snapshot's lifecycle transitions."""

    created_by:        str
    created_at:        float
    framework_version: str
    source_module:     str
    correlation_id:    str

    published_at:  Optional[float] = None
    published_by:  str             = ""
    archived_at:   Optional[float] = None
    archived_by:   str             = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "created_by":        self.created_by,
            "created_at":        self.created_at,
            "published_at":      self.published_at,
            "published_by":      self.published_by,
            "archived_at":       self.archived_at,
            "archived_by":       self.archived_by,
            "framework_version": self.framework_version,
            "source_module":     self.source_module,
            "correlation_id":    self.correlation_id,
        }


@dataclass(frozen=True)
class RiskMetadata:
    """Aggregate statistics derived from the risk evaluation."""

    risk_category:          str
    evaluation_duration_ms: float
    rule_count:             int
    pass_count:             int
    warning_count:          int
    block_count:            int
    skip_count:             int
    failed_count:           int
    override_count:         int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_category":          self.risk_category,
            "evaluation_duration_ms": self.evaluation_duration_ms,
            "rule_count":             self.rule_count,
            "pass_count":             self.pass_count,
            "warning_count":          self.warning_count,
            "block_count":            self.block_count,
            "skip_count":             self.skip_count,
            "failed_count":           self.failed_count,
            "override_count":         self.override_count,
        }


@dataclass(frozen=True)
class OverrideMetadata:
    """Details of an authorized control override."""

    override_id:       str
    approver:          str
    reason:            str
    timestamp:         float
    original_action:   str
    new_action:        str
    affected_rule_ids: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "override_id":       self.override_id,
            "approver":          self.approver,
            "reason":            self.reason,
            "timestamp":         self.timestamp,
            "original_action":   self.original_action,
            "new_action":        self.new_action,
            "affected_rule_ids": list(self.affected_rule_ids),
        }


# ── Factory helpers ───────────────────────────────────────────────────────────

def make_audit_metadata(
    *,
    created_by:        str = "iios:execution:risk",
    framework_version: str = "1.0.0",
    source_module:     str = "snapshot",
    correlation_id:    str = "",
    published_at:      Optional[float] = None,
    published_by:      str = "",
    archived_at:       Optional[float] = None,
    archived_by:       str = "",
) -> AuditMetadata:
    return AuditMetadata(
        created_by=created_by,
        created_at=time.time(),
        framework_version=framework_version,
        source_module=source_module,
        correlation_id=correlation_id,
        published_at=published_at,
        published_by=published_by,
        archived_at=archived_at,
        archived_by=archived_by,
    )


def make_risk_metadata(
    *,
    risk_category:          str   = "",
    evaluation_duration_ms: float = 0.0,
    rule_count:             int   = 0,
    pass_count:             int   = 0,
    warning_count:          int   = 0,
    block_count:            int   = 0,
    skip_count:             int   = 0,
    failed_count:           int   = 0,
    override_count:         int   = 0,
) -> RiskMetadata:
    return RiskMetadata(
        risk_category=risk_category,
        evaluation_duration_ms=evaluation_duration_ms,
        rule_count=rule_count,
        pass_count=pass_count,
        warning_count=warning_count,
        block_count=block_count,
        skip_count=skip_count,
        failed_count=failed_count,
        override_count=override_count,
    )


def make_override_metadata_from(override_info: Any) -> OverrideMetadata:
    """Build OverrideMetadata from an M4 OverrideInfo object."""
    return OverrideMetadata(
        override_id=getattr(override_info, "override_id", ""),
        approver=getattr(override_info, "approver", ""),
        reason=getattr(override_info, "reason", ""),
        timestamp=getattr(override_info, "timestamp", time.time()),
        original_action=str(getattr(
            getattr(override_info, "original_action", ""), "value",
            getattr(override_info, "original_action", "")
        )),
        new_action=str(getattr(
            getattr(override_info, "new_action", ""), "value",
            getattr(override_info, "new_action", "")
        )),
        affected_rule_ids=tuple(getattr(override_info, "affected_rule_ids", ())),
    )
