"""
supervisor_snapshot_builder.py — iios.supervisor.snapshot
-----------------------------------------------------------
Fluent builder for SupervisorSnapshot.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from typing import Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    PLATFORM_VERSION,
    VERSION,
    SnapshotEnterpriseState,
    SnapshotGovernanceState,
    SnapshotLifecycleState,
    SnapshotStatus,
    SupervisorScope,
    SupervisorType,
)
from .exceptions import SupervisorSnapshotBuildError
from .supervisor_snapshot import (
    AnomalySummary,
    AuditSummary,
    DependencySummary,
    EnterpriseSummary,
    GovernanceSummary,
    SelfHealingSummary,
    SnapshotStatistics,
    SubsystemsSummary,
    SupervisionSummary,
    SupervisorSnapshot,
)
from .supervisor_snapshot_metadata import SupervisorSnapshotMetadata

_log = get_logger(__name__)


class SupervisorSnapshotBuilder:
    """
    Fluent builder for :class:`SupervisorSnapshot`.

    Usage::

        snapshot = (
            SupervisorSnapshotBuilder("sess-1", "wf-1")
            .with_enterprise_state(SnapshotEnterpriseState.NORMAL)
            .with_governance_summary(GovernanceSummary.create(governance_decision="continue"))
            .build()
        )
    """

    def __init__(
        self,
        session_id:  str,
        workflow_id: str = "",
        *,
        enterprise_session_id: str             = "",
        scope:                 SupervisorScope  = SupervisorScope.PLATFORM,
        supervisor_type:       SupervisorType   = SupervisorType.STANDARD,
        snapshot_id:           Optional[str]    = None,
        environment:           str              = "production",
    ) -> None:
        if not session_id:
            raise SupervisorSnapshotBuildError("session_id must not be empty")

        self._snapshot_id           = snapshot_id or str(uuid.uuid4())
        self._session_id            = session_id
        self._workflow_id           = workflow_id or str(uuid.uuid4())
        self._enterprise_session_id = enterprise_session_id or str(uuid.uuid4())
        self._scope                 = scope
        self._supervisor_type       = supervisor_type
        self._environment           = environment

        # Content sections — safe defaults
        self._enterprise_summary:   EnterpriseSummary      = EnterpriseSummary.create()
        self._subsystems_summary:   SubsystemsSummary      = SubsystemsSummary.unknown()
        self._governance_summary:   GovernanceSummary      = GovernanceSummary.create()
        self._supervision_summary:  SupervisionSummary     = SupervisionSummary.create()
        self._anomaly_summary:      AnomalySummary         = AnomalySummary.create()
        self._self_healing_summary: SelfHealingSummary     = SelfHealingSummary.create()
        self._dependency_summary:   DependencySummary      = DependencySummary.create()
        self._audit_summary:        AuditSummary           = AuditSummary.create()
        self._snapshot_statistics:  SnapshotStatistics     = SnapshotStatistics.create()
        self._metadata:             SupervisorSnapshotMetadata = (
            SupervisorSnapshotMetadata.create(environment=environment)
        )

        # State defaults
        self._lifecycle_state:    SnapshotLifecycleState  = SnapshotLifecycleState.UNKNOWN
        self._governance_state:   SnapshotGovernanceState = SnapshotGovernanceState.UNKNOWN
        self._enterprise_state:   SnapshotEnterpriseState = SnapshotEnterpriseState.UNKNOWN
        self._snapshot_status:    SnapshotStatus          = SnapshotStatus.BUILDING
        self._supervisor_version: str                     = VERSION
        self._started_at:         float                   = time.time()

    # ------------------------------------------------------------------
    # State setters
    # ------------------------------------------------------------------

    def with_lifecycle_state(self, state: SnapshotLifecycleState) -> "SupervisorSnapshotBuilder":
        self._lifecycle_state = state
        return self

    def with_governance_state(self, state: SnapshotGovernanceState) -> "SupervisorSnapshotBuilder":
        self._governance_state = state
        return self

    def with_enterprise_state(self, state: SnapshotEnterpriseState) -> "SupervisorSnapshotBuilder":
        self._enterprise_state = state
        return self

    def with_status(self, status: SnapshotStatus) -> "SupervisorSnapshotBuilder":
        self._snapshot_status = status
        return self

    def with_supervisor_version(self, version: str) -> "SupervisorSnapshotBuilder":
        self._supervisor_version = version
        return self

    # ------------------------------------------------------------------
    # Section setters
    # ------------------------------------------------------------------

    def with_enterprise_summary(self, summary: EnterpriseSummary) -> "SupervisorSnapshotBuilder":
        self._enterprise_summary = summary
        return self

    def with_subsystems_summary(self, summary: SubsystemsSummary) -> "SupervisorSnapshotBuilder":
        self._subsystems_summary = summary
        return self

    def with_governance_summary(self, summary: GovernanceSummary) -> "SupervisorSnapshotBuilder":
        self._governance_summary = summary
        return self

    def with_supervision_summary(self, summary: SupervisionSummary) -> "SupervisorSnapshotBuilder":
        self._supervision_summary = summary
        return self

    def with_anomaly_summary(self, summary: AnomalySummary) -> "SupervisorSnapshotBuilder":
        self._anomaly_summary = summary
        return self

    def with_self_healing_summary(self, summary: SelfHealingSummary) -> "SupervisorSnapshotBuilder":
        self._self_healing_summary = summary
        return self

    def with_dependency_summary(self, summary: DependencySummary) -> "SupervisorSnapshotBuilder":
        self._dependency_summary = summary
        return self

    def with_audit_summary(self, summary: AuditSummary) -> "SupervisorSnapshotBuilder":
        self._audit_summary = summary
        return self

    def with_statistics(self, statistics: SnapshotStatistics) -> "SupervisorSnapshotBuilder":
        self._snapshot_statistics = statistics
        return self

    def with_metadata(self, metadata: SupervisorSnapshotMetadata) -> "SupervisorSnapshotBuilder":
        self._metadata = metadata
        return self

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> SupervisorSnapshot:
        """Build and return the immutable SupervisorSnapshot."""
        now     = time.time()
        elapsed = now - self._started_at

        stats = self._snapshot_statistics
        if stats.assessment_duration == 0.0 and elapsed > 0.0:
            stats = SnapshotStatistics.create(
                assessment_duration  = elapsed,
                supervision_duration = stats.supervision_duration,
                snapshot_size        = stats.snapshot_size,
                component_count      = stats.component_count,
            )

        snapshot = SupervisorSnapshot(
            snapshot_id             = self._snapshot_id,
            supervisor_session_id   = self._session_id,
            supervisor_workflow_id  = self._workflow_id,
            enterprise_session_id   = self._enterprise_session_id,
            platform_version        = PLATFORM_VERSION,
            supervisor_scope        = self._scope,
            supervisor_type         = self._supervisor_type,
            lifecycle_state         = self._lifecycle_state,
            governance_state        = self._governance_state,
            enterprise_state        = self._enterprise_state,
            supervisor_version      = self._supervisor_version,
            framework_version       = VERSION,
            snapshot_timestamp      = now,
            created_at              = self._started_at,
            updated_at              = now,
            snapshot_status         = self._snapshot_status,
            enterprise_summary      = self._enterprise_summary,
            subsystems_summary      = self._subsystems_summary,
            governance_summary      = self._governance_summary,
            supervision_summary     = self._supervision_summary,
            anomaly_summary         = self._anomaly_summary,
            self_healing_summary    = self._self_healing_summary,
            dependency_summary      = self._dependency_summary,
            audit_summary           = self._audit_summary,
            snapshot_statistics     = stats,
            metadata                = self._metadata,
        )
        _log.debug(f"SupervisorSnapshot built: snapshot_id={self._snapshot_id!r}")
        return snapshot
