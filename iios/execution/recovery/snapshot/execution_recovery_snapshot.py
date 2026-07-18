"""
iios/execution/recovery/snapshot/execution_recovery_snapshot.py
===============================================================
ExecutionRecoverySnapshot — the ONLY published representation of the
Recovery subsystem.

Every downstream subsystem MUST consume ExecutionRecoverySnapshot instead
of internal Recovery objects.

Characteristics:
- Immutable (frozen dataclass)
- Self-serialising (to_dict / to_json)
- Versioned (snapshot_version, framework_version, schema_version)
- Auditable (embedded AuditMetadata)
- Contains NO recovery logic — validated information only

C7 Execution Recovery & Resilience — Phase 1, Module 5
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import (
    LIFECYCLE_TERMINAL_STATES,
    SCHEMA_VERSION,
    VERSION,
    RecoveryResult,
    SnapshotHealth,
    SnapshotStatus,
    VerificationOutcome,
)
from .recovery_snapshot_metadata import AuditMetadata, make_audit_metadata


@dataclass(frozen=True)
class ExecutionRecoverySnapshot:
    """
    Immutable, auditable snapshot of a completed recovery workflow.

    This is the single published representation of the Recovery subsystem.
    All downstream consumers (Audit, Compliance, Analytics, Dashboard,
    AI Supervisor, Incident Management, Reporting) MUST consume this object.

    Fields are grouped by logical concern:
        • Identifiers         — snapshot_id, recovery_session_id, …
        • State               — lifecycle_state, recovery_status, recovery_health
        • Policy & Failover   — selected_recovery_policy, executed_failover_strategy
        • Recovery details    — trigger, reason, result, verification
        • Timing              — recovery_duration_ms, timestamp
        • Rich data           — recovery_statistics, recovery_metadata, audit_metadata
        • Framework           — framework_version, schema_version
    """

    # ── Snapshot identity ─────────────────────────────────────────────────────
    snapshot_id:               str
    snapshot_version:          int

    # ── Session / execution identifiers ──────────────────────────────────────
    recovery_session_id:       str
    recovery_plan_id:          str
    failure_id:                str
    execution_session_id:      str
    execution_id:              str
    workflow_id:               str
    gateway_id:                str
    broker_id:                 str
    portfolio_id:              str
    strategy_id:               str

    # ── State ─────────────────────────────────────────────────────────────────
    lifecycle_state:           str           # value of M1 RecoveryState
    recovery_status:           SnapshotStatus
    recovery_health:           SnapshotHealth

    # ── Policy & Failover selections ──────────────────────────────────────────
    selected_recovery_policy:  str           # policy name from M3
    executed_failover_strategy: str          # FailoverAction.value from M4

    # ── Recovery details ──────────────────────────────────────────────────────
    recovery_trigger:          str           # value of M1 RecoveryTrigger
    recovery_reason:           str
    recovery_result:           RecoveryResult
    verification_result:       VerificationOutcome

    # ── Timing ────────────────────────────────────────────────────────────────
    recovery_duration_ms:      float

    # ── Rich data ─────────────────────────────────────────────────────────────
    recovery_statistics:       Dict[str, Any]
    recovery_metadata:         Dict[str, Any]
    audit_metadata:            AuditMetadata

    # ── Framework ─────────────────────────────────────────────────────────────
    framework_version:         str
    schema_version:            str
    timestamp:                 float

    # ── Computed size (optional) ──────────────────────────────────────────────
    snapshot_size_bytes:       int  = 0

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def is_successful(self) -> bool:
        """True when the recovery workflow completed successfully."""
        return self.recovery_result == RecoveryResult.SUCCESS

    @property
    def is_verified(self) -> bool:
        """True when post-recovery verification passed."""
        return self.verification_result == VerificationOutcome.PASSED

    @property
    def is_published(self) -> bool:
        """True when the snapshot has been published to downstream consumers."""
        return self.recovery_status == SnapshotStatus.PUBLISHED

    @property
    def is_complete(self) -> bool:
        """True when the lifecycle state is terminal."""
        return self.lifecycle_state in LIFECYCLE_TERMINAL_STATES

    @property
    def is_archived(self) -> bool:
        """True when the snapshot is archived."""
        return self.recovery_status == SnapshotStatus.ARCHIVED

    # ── Serialisation ────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            # Identity
            "snapshot_id":               self.snapshot_id,
            "snapshot_version":          self.snapshot_version,
            # Session
            "recovery_session_id":       self.recovery_session_id,
            "recovery_plan_id":          self.recovery_plan_id,
            "failure_id":                self.failure_id,
            "execution_session_id":      self.execution_session_id,
            "execution_id":              self.execution_id,
            "workflow_id":               self.workflow_id,
            "gateway_id":                self.gateway_id,
            "broker_id":                 self.broker_id,
            "portfolio_id":              self.portfolio_id,
            "strategy_id":              self.strategy_id,
            # State
            "lifecycle_state":           self.lifecycle_state,
            "recovery_status":           self.recovery_status.value,
            "recovery_health":           self.recovery_health.value,
            # Policy & Failover
            "selected_recovery_policy":  self.selected_recovery_policy,
            "executed_failover_strategy": self.executed_failover_strategy,
            # Recovery details
            "recovery_trigger":          self.recovery_trigger,
            "recovery_reason":           self.recovery_reason,
            "recovery_result":           self.recovery_result.value,
            "verification_result":       self.verification_result.value,
            # Timing
            "recovery_duration_ms":      self.recovery_duration_ms,
            "timestamp":                 self.timestamp,
            # Rich data
            "recovery_statistics":       dict(self.recovery_statistics),
            "recovery_metadata":         dict(self.recovery_metadata),
            "audit_metadata":            self.audit_metadata.to_dict(),
            # Framework
            "framework_version":         self.framework_version,
            "schema_version":            self.schema_version,
            # Size
            "snapshot_size_bytes":       self.snapshot_size_bytes,
        }

    def to_json(self) -> str:
        """Return a JSON string representation of the snapshot."""
        return json.dumps(self.to_dict(), default=str)


# ── Defaults ──────────────────────────────────────────────────────────────────

_DEFAULT_AUDIT = make_audit_metadata()


def make_execution_recovery_snapshot(  # noqa: PLR0913
    *,
    recovery_session_id:        str,
    execution_session_id:       str,
    lifecycle_state:            str,
    recovery_result:            RecoveryResult,
    verification_result:        VerificationOutcome,
    recovery_duration_ms:       float,
    audit_metadata:             Optional[AuditMetadata] = None,
    snapshot_id:                Optional[str] = None,
    snapshot_version:           int = 1,
    recovery_plan_id:           str = "",
    failure_id:                 str = "",
    execution_id:               str = "",
    workflow_id:                str = "",
    gateway_id:                 str = "",
    broker_id:                  str = "",
    portfolio_id:               str = "",
    strategy_id:                str = "",
    recovery_status:            SnapshotStatus = SnapshotStatus.CREATED,
    recovery_health:            SnapshotHealth = SnapshotHealth.UNKNOWN,
    selected_recovery_policy:   str = "",
    executed_failover_strategy: str = "",
    recovery_trigger:           str = "",
    recovery_reason:            str = "",
    recovery_statistics:        Optional[Dict[str, Any]] = None,
    recovery_metadata:          Optional[Dict[str, Any]] = None,
    framework_version:          str = VERSION,
    schema_version:             str = SCHEMA_VERSION,
    timestamp:                  Optional[float] = None,
    snapshot_size_bytes:        int = 0,
) -> ExecutionRecoverySnapshot:
    """Factory — create a validated ExecutionRecoverySnapshot from primitives."""
    snap = ExecutionRecoverySnapshot(
        snapshot_id                = snapshot_id or str(uuid.uuid4()),
        snapshot_version           = snapshot_version,
        recovery_session_id        = recovery_session_id,
        recovery_plan_id           = recovery_plan_id,
        failure_id                 = failure_id,
        execution_session_id       = execution_session_id,
        execution_id               = execution_id,
        workflow_id                = workflow_id,
        gateway_id                 = gateway_id,
        broker_id                  = broker_id,
        portfolio_id               = portfolio_id,
        strategy_id               = strategy_id,
        lifecycle_state            = lifecycle_state,
        recovery_status            = recovery_status,
        recovery_health            = recovery_health,
        selected_recovery_policy   = selected_recovery_policy,
        executed_failover_strategy = executed_failover_strategy,
        recovery_trigger           = recovery_trigger,
        recovery_reason            = recovery_reason,
        recovery_result            = recovery_result,
        verification_result        = verification_result,
        recovery_duration_ms       = recovery_duration_ms,
        recovery_statistics        = dict(recovery_statistics) if recovery_statistics else {},
        recovery_metadata          = dict(recovery_metadata) if recovery_metadata else {},
        audit_metadata             = audit_metadata or make_audit_metadata(),
        framework_version          = framework_version,
        schema_version             = schema_version,
        timestamp                  = timestamp if timestamp is not None else time.time(),
        snapshot_size_bytes        = snapshot_size_bytes,
    )
    return snap
