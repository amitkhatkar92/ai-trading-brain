"""
workflow_snapshot_factory.py — iios.workflow.snapshot
------------------------------------------------------
WorkflowSnapshotFactory — fluent factory for creating standard
WorkflowSnapshot objects with sensible defaults.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 5
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .constants import ExecutionStatus, GovernanceDecision, LifecycleState
from .workflow_snapshot import WorkflowSnapshot
from .workflow_snapshot_builder import WorkflowSnapshotBuilder
from .workflow_snapshot_bundle import WorkflowSnapshotBundle
from .workflow_snapshot_metadata import WorkflowSnapshotMetadata

_builder = WorkflowSnapshotBuilder()


class WorkflowSnapshotFactory:
    """
    Factory for creating well-formed WorkflowSnapshot objects.
    """

    @staticmethod
    def create_completed(
        workflow_id:   str,
        workflow_name: str,
        *,
        execution_duration_ms: float = 0.0,
        completed_steps:       int   = 0,
        total_steps:           int   = 0,
        retry_count:           int   = 0,
        governance_decision:   GovernanceDecision = GovernanceDecision.APPROVED,
        metadata:              Optional[WorkflowSnapshotMetadata] = None,
        extra:                 Optional[Dict[str, Any]] = None,
    ) -> WorkflowSnapshot:
        """Create a snapshot representing a successfully completed workflow."""
        progress = (completed_steps / total_steps) if total_steps > 0 else 1.0
        return _builder.build(
            workflow_id           = workflow_id,
            workflow_name         = workflow_name,
            execution_status      = ExecutionStatus.COMPLETED,
            governance_decision   = governance_decision,
            lifecycle_state       = LifecycleState.COMPLETED,
            completed_steps       = completed_steps,
            total_steps           = total_steps,
            execution_progress    = progress,
            execution_duration_ms = execution_duration_ms,
            retry_count           = retry_count,
            metadata              = metadata,
            extra                 = extra or {},
        )

    @staticmethod
    def create_failed(
        workflow_id:   str,
        workflow_name: str,
        *,
        error_note:            str   = "",
        execution_duration_ms: float = 0.0,
        completed_steps:       int   = 0,
        total_steps:           int   = 0,
        retry_count:           int   = 0,
        governance_decision:   GovernanceDecision = GovernanceDecision.APPROVED,
        metadata:              Optional[WorkflowSnapshotMetadata] = None,
        extra:                 Optional[Dict[str, Any]] = None,
    ) -> WorkflowSnapshot:
        """Create a snapshot representing a failed workflow."""
        progress = (completed_steps / total_steps) if total_steps > 0 else 0.0
        audit: List[str] = []
        if error_note:
            audit.append(f"FAILURE: {error_note}")
        return _builder.build(
            workflow_id           = workflow_id,
            workflow_name         = workflow_name,
            execution_status      = ExecutionStatus.FAILED,
            governance_decision   = governance_decision,
            lifecycle_state       = LifecycleState.FAILED,
            completed_steps       = completed_steps,
            total_steps           = total_steps,
            execution_progress    = progress,
            execution_duration_ms = execution_duration_ms,
            retry_count           = retry_count,
            audit_trail           = audit,
            metadata              = metadata,
            extra                 = extra or {},
        )

    @staticmethod
    def create_running(
        workflow_id:   str,
        workflow_name: str,
        *,
        current_step:       str   = "",
        completed_steps:    int   = 0,
        total_steps:        int   = 0,
        governance_decision: GovernanceDecision = GovernanceDecision.APPROVED,
        metadata:           Optional[WorkflowSnapshotMetadata] = None,
        extra:              Optional[Dict[str, Any]] = None,
    ) -> WorkflowSnapshot:
        """Create a snapshot representing an in-progress workflow."""
        progress = (completed_steps / total_steps) if total_steps > 0 else 0.0
        return _builder.build(
            workflow_id         = workflow_id,
            workflow_name       = workflow_name,
            execution_status    = ExecutionStatus.RUNNING,
            governance_decision = governance_decision,
            lifecycle_state     = LifecycleState.ACTIVE,
            current_step        = current_step,
            completed_steps     = completed_steps,
            total_steps         = total_steps,
            execution_progress  = progress,
            metadata            = metadata,
            extra               = extra or {},
        )

    @staticmethod
    def create_bundle(
        bundle_name: str,
        snapshots:   List[WorkflowSnapshot],
        *,
        enterprise_id:  str = "",
        correlation_id: str = "",
    ) -> WorkflowSnapshotBundle:
        """Create a bundle from a list of snapshots."""
        return WorkflowSnapshotBundle.create(
            bundle_name    = bundle_name,
            snapshots      = snapshots,
            enterprise_id  = enterprise_id,
            correlation_id = correlation_id,
        )

    @staticmethod
    def create_metadata(
        *,
        environment:       str               = "production",
        correlation_id:    str               = "",
        trace_id:          str               = "",
        source_components: Optional[List[str]] = None,
    ) -> WorkflowSnapshotMetadata:
        return WorkflowSnapshotMetadata.create(
            environment        = environment,
            correlation_id     = correlation_id,
            trace_id           = trace_id,
            source_components  = source_components or [],
        )
