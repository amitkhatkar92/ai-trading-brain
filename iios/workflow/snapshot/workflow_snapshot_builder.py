"""
workflow_snapshot_builder.py — iios.workflow.snapshot
------------------------------------------------------
WorkflowSnapshotBuilder — constructs immutable WorkflowSnapshot objects
from subsystem outputs.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 5
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ExecutionStatus,
    GovernanceDecision,
    LifecycleState,
    PREFIX_SNAPSHOT,
    SNAPSHOT_VERSION,
    SnapshotStatus,
    WorkflowHealthStatus,
)
from .exceptions import WorkflowSnapshotBuildError
from .workflow_snapshot import WorkflowSnapshot
from .workflow_snapshot_metadata import WorkflowSnapshotMetadata

_log = get_logger(__name__)


def _compute_health(
    execution_status: ExecutionStatus,
    governance_decision: GovernanceDecision,
) -> WorkflowHealthStatus:
    if execution_status in (ExecutionStatus.FAILED, ExecutionStatus.TIMED_OUT):
        return WorkflowHealthStatus.FAILED
    if governance_decision in (
        GovernanceDecision.REJECTED,
        GovernanceDecision.BLOCKED,
        GovernanceDecision.EMERGENCY_STOPPED,
    ):
        return WorkflowHealthStatus.FAILED
    if execution_status == ExecutionStatus.COMPLETED and governance_decision in (
        GovernanceDecision.APPROVED,
        GovernanceDecision.APPROVED_WITH_CONDITIONS,
        GovernanceDecision.NOT_EVALUATED,
    ):
        return WorkflowHealthStatus.HEALTHY
    if execution_status == ExecutionStatus.RUNNING:
        return WorkflowHealthStatus.HEALTHY
    return WorkflowHealthStatus.DEGRADED


class WorkflowSnapshotBuilder:
    """
    Constructs immutable WorkflowSnapshot objects.

    Stateless — thread-safe.
    """

    def build(
        self,
        *,
        # Identity
        workflow_id:           str,
        workflow_name:         str,
        workflow_session_id:   str          = "",
        workflow_execution_id: str          = "",
        enterprise_session_id: str          = "",
        workflow_category:     str          = "enterprise",
        workflow_type:         str          = "sequential",
        correlation_id:        str          = "",
        trace_id:              str          = "",
        # State
        execution_status:      ExecutionStatus    = ExecutionStatus.COMPLETED,
        governance_decision:   GovernanceDecision = GovernanceDecision.NOT_EVALUATED,
        lifecycle_state:       LifecycleState     = LifecycleState.ACTIVE,
        snapshot_status:       SnapshotStatus     = SnapshotStatus.VALID,
        # Workflow summary
        priority:              int      = 2,
        execution_mode:        str      = "sync",
        current_step:          str      = "",
        completed_steps:       int      = 0,
        remaining_steps:       int      = 0,
        total_steps:           int      = 0,
        execution_progress:    float    = 0.0,
        # Execution summary
        execution_duration_ms: float    = 0.0,
        queue_time_ms:         float    = 0.0,
        scheduling_time_ms:    float    = 0.0,
        execution_time_ms:     float    = 0.0,
        retry_count:           int      = 0,
        timeout_count:         int      = 0,
        compensation_count:    int      = 0,
        checkpoint_count:      int      = 0,
        recovery_status:       str      = "none",
        # Resource summary
        allocated_resources:   Optional[Dict[str, Any]] = None,
        active_resources:      Optional[Dict[str, Any]] = None,
        released_resources:    Optional[Dict[str, Any]] = None,
        resource_utilization:  float    = 0.0,
        # Dependency summary
        resolved_dependencies: Optional[List[str]] = None,
        pending_dependencies:  Optional[List[str]] = None,
        dependency_health:     str      = "healthy",
        # Governance summary
        policy_version:        str      = "1.0",
        approval_status:       str      = "not_required",
        compliance_status:     str      = "compliant",
        security_status:       str      = "secure",
        risk_status:           str      = "low",
        governance_notes:      str      = "",
        # Audit
        validation_summary:    Optional[Dict[str, Any]] = None,
        execution_summary:     Optional[Dict[str, Any]] = None,
        audit_trail:           Optional[List[str]]      = None,
        # Metadata
        metadata:              Optional[WorkflowSnapshotMetadata] = None,
        extra:                 Optional[Dict[str, Any]]           = None,
        # Override
        snapshot_id:           Optional[str] = None,
    ) -> WorkflowSnapshot:
        """
        Build an immutable WorkflowSnapshot.

        All fields have sensible defaults.  Provide overrides as needed.
        Raises WorkflowSnapshotBuildError on invalid inputs.
        """
        if not workflow_id:
            raise WorkflowSnapshotBuildError("workflow_id is required")
        if not workflow_name:
            raise WorkflowSnapshotBuildError("workflow_name is required")

        now          = datetime.now(tz=timezone.utc).isoformat()
        sid          = snapshot_id or f"{PREFIX_SNAPSHOT}{uuid.uuid4().hex[:12]}"
        health       = _compute_health(execution_status, governance_decision)
        meta         = metadata or WorkflowSnapshotMetadata.create(
            correlation_id = correlation_id,
            trace_id       = trace_id,
            source_components = ["M1-Lifecycle", "M2-Engine", "M3-Governance", "M4-Orchestration"],
        )

        snap = WorkflowSnapshot(
            snapshot_id           = sid,
            snapshot_version      = SNAPSHOT_VERSION,
            workflow_id           = workflow_id,
            workflow_session_id   = workflow_session_id,
            workflow_execution_id = workflow_execution_id,
            enterprise_session_id = enterprise_session_id,
            workflow_name         = workflow_name,
            workflow_category     = workflow_category,
            workflow_type         = workflow_type,
            correlation_id        = correlation_id or meta.correlation_id,
            trace_id              = trace_id       or meta.trace_id,
            snapshot_status       = snapshot_status,
            execution_status      = execution_status,
            governance_decision   = governance_decision,
            lifecycle_state       = lifecycle_state,
            health_status         = health,
            priority              = priority,
            execution_mode        = execution_mode,
            current_step          = current_step,
            completed_steps       = completed_steps,
            remaining_steps       = remaining_steps,
            total_steps           = total_steps,
            execution_progress    = round(execution_progress, 4),
            execution_duration_ms = round(execution_duration_ms, 3),
            queue_time_ms         = round(queue_time_ms, 3),
            scheduling_time_ms    = round(scheduling_time_ms, 3),
            execution_time_ms     = round(execution_time_ms, 3),
            retry_count           = retry_count,
            timeout_count         = timeout_count,
            compensation_count    = compensation_count,
            checkpoint_count      = checkpoint_count,
            recovery_status       = recovery_status,
            allocated_resources   = dict(allocated_resources or {}),
            active_resources      = dict(active_resources or {}),
            released_resources    = dict(released_resources or {}),
            resource_utilization  = round(resource_utilization, 4),
            resolved_dependencies = list(resolved_dependencies or []),
            pending_dependencies  = list(pending_dependencies or []),
            dependency_health     = dependency_health,
            policy_version        = policy_version,
            approval_status       = approval_status,
            compliance_status     = compliance_status,
            security_status       = security_status,
            risk_status           = risk_status,
            governance_notes      = governance_notes,
            validation_summary    = dict(validation_summary or {}),
            execution_summary     = dict(execution_summary or {}),
            audit_trail           = list(audit_trail or []),
            metadata              = meta,
            extra                 = dict(extra or {}),
            snapshot_timestamp    = now,
            created_at            = now,
            updated_at            = now,
        )
        _log.debug(
            f"Builder: built snapshot={sid!r} "
            f"workflow={workflow_id!r} "
            f"status={execution_status.value!r}"
        )
        return snap
