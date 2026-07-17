"""iios/execution/risk/snapshot/execution_risk_snapshot.py
==================================================
ExecutionRiskSnapshot — the ONLY published representation of an
execution risk evaluation.

This object is:
  • Immutable — frozen dataclass; no setattr after creation
  • Self-contained — all fields are primitives or nested frozen dataclasses
  • Serializable — to_dict() / to_json()
  • Auditable — AuditMetadata + RiskMetadata embedded
  • Versioned — snapshot_version is baked in at build time

ExecutionRiskSnapshot MUST NOT import from:
  iios.execution.risk.lifecycle
  iios.execution.risk.engine
  iios.execution.risk.rules
  iios.execution.risk.controls

All upstream data has been extracted and serialised by the builder.

C6 Execution Intelligence — Phase 4, Module 5
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import SNAPSHOT_VERSION, SnapshotStatus, VERSION
from .execution_risk_snapshot_metadata import (
    AuditMetadata,
    OverrideMetadata,
    RiskMetadata,
    make_audit_metadata,
    make_risk_metadata,
)


# ── RuleSnapshot ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RuleSnapshot:
    """
    Serialized, immutable representation of a single rule evaluation result.

    Downstream systems receive RuleSnapshot objects — never raw M3 RuleResult.
    """

    rule_id:    str
    rule_name:  str
    category:   str
    outcome:    str
    message:    str
    reason:     str
    elapsed_ms: float
    metadata:   Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id":    self.rule_id,
            "rule_name":  self.rule_name,
            "category":   self.category,
            "outcome":    self.outcome,
            "message":    self.message,
            "reason":     self.reason,
            "elapsed_ms": self.elapsed_ms,
            "metadata":   dict(self.metadata),
        }


# ── ExecutionRiskSnapshot ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class ExecutionRiskSnapshot:
    """
    The ONLY object published outside the Execution Risk subsystem.

    Contains the complete result of a single institutional execution risk
    evaluation, including risk lifecycle state, rule results, and the
    final control decision.

    Downstream systems (Execution Gateway, Broker Adapters, Compliance,
    Audit, Reporting, Monitoring, Analytics) MUST consume this object
    and MUST NOT access internal lifecycle, engine, rules, or control
    objects directly.

    Field categories
    ----------------
    Identifiers     — snapshot_id, risk_id, execution_id, order_id, …
    Classification  — risk_category, risk_state
    Control         — control_action, final_action, policy_used
    Rules           — triggered_rules, warnings, blocks
    Status flags    — override_status, emergency_status
    Timing          — evaluation_duration_ms, snapshot_timestamp
    Metadata        — risk_metadata, audit_metadata, override_metadata
    Framework       — framework_version, snapshot_version, status
    Extended        — risk_statistics, extra_metadata
    """

    # ── Identifiers ──────────────────────────────────────────────────────────
    snapshot_id:      str
    snapshot_version: str
    risk_id:          str
    execution_id:     str
    order_id:         str
    position_id:      str
    portfolio_id:     str
    workflow_id:      str
    decision_id:      str
    strategy_id:      str
    correlation_id:   str

    # ── Risk classification ───────────────────────────────────────────────────
    risk_category:    str    # RiskCategory.value
    risk_state:       str    # RiskState.value

    # ── Control decision ──────────────────────────────────────────────────────
    control_action:   str    # ControlAction before override
    final_action:     str    # ControlAction after override (or same)
    policy_used:      str    # PolicyType.value

    # ── Rule results ──────────────────────────────────────────────────────────
    triggered_rules:  Tuple[RuleSnapshot, ...]   # all non-skipped rules
    warnings:         Tuple[RuleSnapshot, ...]   # WARNING / OVERRIDE_REQUIRED
    blocks:           Tuple[RuleSnapshot, ...]   # BLOCK / FAILED

    # ── Status flags ──────────────────────────────────────────────────────────
    override_status:  bool   # True if a control override was applied
    emergency_status: bool   # True if EMERGENCY_STOP was triggered

    # ── Timing ───────────────────────────────────────────────────────────────
    evaluation_duration_ms: float
    snapshot_timestamp:     float

    # ── Metadata objects ──────────────────────────────────────────────────────
    risk_metadata:     RiskMetadata
    audit_metadata:    AuditMetadata
    override_metadata: Optional[OverrideMetadata]

    # ── Framework ─────────────────────────────────────────────────────────────
    framework_version: str
    status:            SnapshotStatus

    # ── Extended / extensible ─────────────────────────────────────────────────
    risk_statistics:   Dict[str, Any] = field(default_factory=dict, compare=False)
    extra_metadata:    Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def is_blocked(self) -> bool:
        return self.final_action in ("BLOCK", "CANCEL", "EMERGENCY_STOP")

    @property
    def allowed(self) -> bool:
        return self.final_action in ("ALLOW", "ALLOW_WITH_WARNING")

    @property
    def is_emergency(self) -> bool:
        return self.emergency_status or self.final_action == "EMERGENCY_STOP"

    @property
    def was_overridden(self) -> bool:
        return self.override_status

    @property
    def is_published(self) -> bool:
        return self.status == SnapshotStatus.PUBLISHED

    @property
    def is_archived(self) -> bool:
        return self.status == SnapshotStatus.ARCHIVED

    @property
    def rule_count(self) -> int:
        return len(self.triggered_rules)

    @property
    def block_count(self) -> int:
        return len(self.blocks)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def age_ms(self) -> float:
        return (time.time() - self.snapshot_timestamp) * 1_000.0

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            # Identifiers
            "snapshot_id":      self.snapshot_id,
            "snapshot_version": self.snapshot_version,
            "risk_id":          self.risk_id,
            "execution_id":     self.execution_id,
            "order_id":         self.order_id,
            "position_id":      self.position_id,
            "portfolio_id":     self.portfolio_id,
            "workflow_id":      self.workflow_id,
            "decision_id":      self.decision_id,
            "strategy_id":      self.strategy_id,
            "correlation_id":   self.correlation_id,
            # Classification
            "risk_category":    self.risk_category,
            "risk_state":       self.risk_state,
            # Control
            "control_action":   self.control_action,
            "final_action":     self.final_action,
            "policy_used":      self.policy_used,
            # Rule results
            "triggered_rules":  [r.to_dict() for r in self.triggered_rules],
            "warnings":         [r.to_dict() for r in self.warnings],
            "blocks":           [r.to_dict() for r in self.blocks],
            # Status
            "override_status":  self.override_status,
            "emergency_status": self.emergency_status,
            # Timing
            "evaluation_duration_ms": self.evaluation_duration_ms,
            "snapshot_timestamp":     self.snapshot_timestamp,
            # Metadata
            "risk_metadata":    self.risk_metadata.to_dict(),
            "audit_metadata":   self.audit_metadata.to_dict(),
            "override_metadata": self.override_metadata.to_dict()
                                  if self.override_metadata else None,
            # Framework
            "framework_version": self.framework_version,
            "status":            self.status.value,
            # Extended
            "risk_statistics":   dict(self.risk_statistics),
            "extra_metadata":    dict(self.extra_metadata),
            # Derived (convenience for consumers)
            "is_blocked":        self.is_blocked,
            "allowed":           self.allowed,
            "is_emergency":      self.is_emergency,
            "was_overridden":    self.was_overridden,
            "rule_count":        self.rule_count,
            "block_count":       self.block_count,
            "warning_count":     self.warning_count,
        }

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def with_status(self, status: SnapshotStatus) -> "ExecutionRiskSnapshot":
        """Return a copy of this snapshot with a new status."""
        from dataclasses import replace
        return replace(self, status=status)

    def with_published_audit(self, published_by: str = "") -> "ExecutionRiskSnapshot":
        """Return a copy marked as published in audit metadata."""
        from dataclasses import replace
        new_audit = replace(
            self.audit_metadata,
            published_at=time.time(),
            published_by=published_by,
        )
        return replace(self, audit_metadata=new_audit, status=SnapshotStatus.PUBLISHED)

    def with_archived_audit(self, archived_by: str = "") -> "ExecutionRiskSnapshot":
        """Return a copy marked as archived in audit metadata."""
        from dataclasses import replace
        new_audit = replace(
            self.audit_metadata,
            archived_at=time.time(),
            archived_by=archived_by,
        )
        return replace(self, audit_metadata=new_audit, status=SnapshotStatus.ARCHIVED)
