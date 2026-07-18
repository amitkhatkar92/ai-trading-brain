"""
iios/execution/recovery/snapshot/recovery_snapshot_factory.py
=============================================================
RecoverySnapshotFactory — creates ExecutionRecoverySnapshot objects
from primitive values.

Used by the builder and directly in tests.  No M1/M2/M3/M4 type
dependencies — only snapshot-local types.

C7 Execution Recovery & Resilience — Phase 1, Module 5
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    FACTORY_ID,
    SCHEMA_VERSION,
    VERSION,
    RecoveryResult,
    SnapshotHealth,
    SnapshotStatus,
    VerificationOutcome,
)
from .exceptions import SnapshotNotRunningError
from .execution_recovery_snapshot import (
    ExecutionRecoverySnapshot,
    make_execution_recovery_snapshot,
)
from .recovery_snapshot_metadata import AuditMetadata

_log = get_logger(__name__)

_RUNNING = frozenset({EngineState.RUNNING, "running"})


class RecoverySnapshotFactory(LifecycleAwareMixin):
    """
    Lifecycle-aware factory for ExecutionRecoverySnapshot objects.

    Creates snapshots from extracted primitive values.
    Does NOT accept M1/M2/M3/M4 objects — use RecoverySnapshotBuilder for that.
    """

    VERSION   = VERSION
    SYSTEM_ID = FACTORY_ID

    def __init__(self) -> None:
        super().__init__()

    def _on_start(self) -> None:
        _log.info("RecoverySnapshotFactory started", system_id=FACTORY_ID)

    def _on_stop(self) -> None:
        _log.info("RecoverySnapshotFactory stopped", system_id=FACTORY_ID)

    def _assert_running(self) -> None:
        if self.lifecycle_state() not in _RUNNING:
            raise SnapshotNotRunningError()

    def create(
        self,
        *,
        recovery_session_id:        str,
        execution_session_id:       str,
        lifecycle_state:            str,
        recovery_result:            RecoveryResult,
        verification_result:        VerificationOutcome,
        recovery_duration_ms:       float,
        audit_metadata:             Optional[AuditMetadata] = None,
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
        snapshot_size_bytes:        int = 0,
    ) -> ExecutionRecoverySnapshot:
        """Create a new ExecutionRecoverySnapshot from primitive values."""
        self._assert_running()
        return make_execution_recovery_snapshot(
            recovery_session_id        = recovery_session_id,
            execution_session_id       = execution_session_id,
            lifecycle_state            = lifecycle_state,
            recovery_result            = recovery_result,
            verification_result        = verification_result,
            recovery_duration_ms       = recovery_duration_ms,
            audit_metadata             = audit_metadata,
            snapshot_version           = snapshot_version,
            recovery_plan_id           = recovery_plan_id,
            failure_id                 = failure_id,
            execution_id               = execution_id,
            workflow_id                = workflow_id,
            gateway_id                 = gateway_id,
            broker_id                  = broker_id,
            portfolio_id               = portfolio_id,
            strategy_id               = strategy_id,
            recovery_status            = recovery_status,
            recovery_health            = recovery_health,
            selected_recovery_policy   = selected_recovery_policy,
            executed_failover_strategy = executed_failover_strategy,
            recovery_trigger           = recovery_trigger,
            recovery_reason            = recovery_reason,
            recovery_statistics        = recovery_statistics,
            recovery_metadata          = recovery_metadata,
            framework_version          = framework_version,
            schema_version             = schema_version,
            snapshot_size_bytes        = snapshot_size_bytes,
        )
