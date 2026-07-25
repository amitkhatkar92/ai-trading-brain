"""
workflow_snapshot.py — iios.workflow.snapshot
----------------------------------------------
WorkflowSnapshot — the immutable, versioned, canonical published
representation of Enterprise Workflow & Process Orchestration.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 5
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import (
    ExecutionStatus,
    GovernanceDecision,
    LifecycleState,
    PREFIX_SNAPSHOT,
    SNAPSHOT_VERSION,
    SnapshotStatus,
    WorkflowHealthStatus,
)
from .workflow_snapshot_metadata import WorkflowSnapshotMetadata


@dataclass(frozen=True)
class WorkflowSnapshot:
    """
    Immutable, versioned canonical snapshot of enterprise workflow state.

    Aggregates:
      - Workflow identification and type
      - Execution state and summary
      - Governance decision and compliance state
      - Lifecycle state
      - Resource and dependency summaries
      - Audit trail
      - Metadata (provenance, versioning, correlation)

    Downstream IIOS components MUST consume WorkflowSnapshot rather than
    directly accessing M1-M4 internals.
    """
    # ── Identity ──────────────────────────────────────────────────────────────
    snapshot_id:          str
    snapshot_version:     str
    workflow_id:          str
    workflow_session_id:  str
    workflow_execution_id: str
    enterprise_session_id: str
    workflow_name:        str
    workflow_category:    str
    workflow_type:        str
    correlation_id:       str
    trace_id:             str

    # ── State ─────────────────────────────────────────────────────────────────
    snapshot_status:   SnapshotStatus
    execution_status:  ExecutionStatus
    governance_decision: GovernanceDecision
    lifecycle_state:   LifecycleState
    health_status:     WorkflowHealthStatus

    # ── Workflow Summary ──────────────────────────────────────────────────────
    priority:           int                  # 0=highest
    execution_mode:     str
    current_step:       str
    completed_steps:    int
    remaining_steps:    int
    total_steps:        int
    execution_progress: float                # 0.0 – 1.0

    # ── Execution Summary ─────────────────────────────────────────────────────
    execution_duration_ms: float
    queue_time_ms:         float
    scheduling_time_ms:    float
    execution_time_ms:     float
    retry_count:           int
    timeout_count:         int
    compensation_count:    int
    checkpoint_count:      int
    recovery_status:       str

    # ── Resource Summary ─────────────────────────────────────────────────────
    allocated_resources:  Dict[str, Any]
    active_resources:     Dict[str, Any]
    released_resources:   Dict[str, Any]
    resource_utilization: float              # 0.0 – 1.0

    # ── Dependency Summary ────────────────────────────────────────────────────
    resolved_dependencies: List[str]
    pending_dependencies:  List[str]
    dependency_health:     str

    # ── Governance Summary ────────────────────────────────────────────────────
    policy_version:    str
    approval_status:   str
    compliance_status: str
    security_status:   str
    risk_status:       str
    governance_notes:  str

    # ── Audit ─────────────────────────────────────────────────────────────────
    validation_summary: Dict[str, Any]
    execution_summary:  Dict[str, Any]
    audit_trail:        List[str]

    # ── Metadata ──────────────────────────────────────────────────────────────
    metadata:    WorkflowSnapshotMetadata
    extra:       Dict[str, Any]

    # ── Timestamps ────────────────────────────────────────────────────────────
    snapshot_timestamp: str
    created_at:         str
    updated_at:         str

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def is_healthy(self) -> bool:
        return self.health_status == WorkflowHealthStatus.HEALTHY

    @property
    def is_completed(self) -> bool:
        return self.execution_status == ExecutionStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self.execution_status in (
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMED_OUT,
        )

    @property
    def is_governance_approved(self) -> bool:
        return self.governance_decision in (
            GovernanceDecision.APPROVED,
            GovernanceDecision.APPROVED_WITH_CONDITIONS,
        )

    @property
    def is_published(self) -> bool:
        return self.snapshot_status == SnapshotStatus.PUBLISHED

    @property
    def step_ids(self) -> List[str]:
        return []

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            # Identity
            "snapshot_id":           self.snapshot_id,
            "snapshot_version":      self.snapshot_version,
            "workflow_id":           self.workflow_id,
            "workflow_session_id":   self.workflow_session_id,
            "workflow_execution_id": self.workflow_execution_id,
            "enterprise_session_id": self.enterprise_session_id,
            "workflow_name":         self.workflow_name,
            "workflow_category":     self.workflow_category,
            "workflow_type":         self.workflow_type,
            "correlation_id":        self.correlation_id,
            "trace_id":              self.trace_id,
            # State
            "snapshot_status":    self.snapshot_status.value,
            "execution_status":   self.execution_status.value,
            "governance_decision": self.governance_decision.value,
            "lifecycle_state":    self.lifecycle_state.value,
            "health_status":      self.health_status.value,
            # Workflow summary
            "priority":           self.priority,
            "execution_mode":     self.execution_mode,
            "current_step":       self.current_step,
            "completed_steps":    self.completed_steps,
            "remaining_steps":    self.remaining_steps,
            "total_steps":        self.total_steps,
            "execution_progress": self.execution_progress,
            # Execution summary
            "execution_duration_ms": self.execution_duration_ms,
            "queue_time_ms":         self.queue_time_ms,
            "scheduling_time_ms":    self.scheduling_time_ms,
            "execution_time_ms":     self.execution_time_ms,
            "retry_count":           self.retry_count,
            "timeout_count":         self.timeout_count,
            "compensation_count":    self.compensation_count,
            "checkpoint_count":      self.checkpoint_count,
            "recovery_status":       self.recovery_status,
            # Resource summary
            "allocated_resources":   self.allocated_resources,
            "active_resources":      self.active_resources,
            "released_resources":    self.released_resources,
            "resource_utilization":  self.resource_utilization,
            # Dependency summary
            "resolved_dependencies": self.resolved_dependencies,
            "pending_dependencies":  self.pending_dependencies,
            "dependency_health":     self.dependency_health,
            # Governance summary
            "policy_version":    self.policy_version,
            "approval_status":   self.approval_status,
            "compliance_status": self.compliance_status,
            "security_status":   self.security_status,
            "risk_status":       self.risk_status,
            "governance_notes":  self.governance_notes,
            # Audit
            "validation_summary": self.validation_summary,
            "execution_summary":  self.execution_summary,
            "audit_trail":        self.audit_trail,
            # Metadata
            "metadata":  self.metadata.to_dict(),
            # Timestamps
            "snapshot_timestamp": self.snapshot_timestamp,
            "created_at":         self.created_at,
            "updated_at":         self.updated_at,
            # Computed
            "is_healthy":              self.is_healthy,
            "is_completed":            self.is_completed,
            "is_failed":               self.is_failed,
            "is_governance_approved":  self.is_governance_approved,
            "is_published":            self.is_published,
        }
