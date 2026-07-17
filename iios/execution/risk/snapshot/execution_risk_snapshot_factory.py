"""iios/execution/risk/snapshot/execution_risk_snapshot_factory.py
==================================================
SnapshotFactory — convenience factories for creating snapshots.

Provides:
  • build_from_pipeline()  — single-call convenience wrapper over SnapshotBuilder
  • create_minimal()       — minimal snapshot for testing
  • create_allow_snapshot() / create_block_snapshot() / create_emergency_snapshot()

C6 Execution Intelligence — Phase 4, Module 5
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from .constants import SNAPSHOT_VERSION, VERSION, SnapshotStatus
from .execution_risk_snapshot import ExecutionRiskSnapshot, RuleSnapshot
from .execution_risk_snapshot_builder import SnapshotBuilder
from .execution_risk_snapshot_metadata import (
    AuditMetadata,
    RiskMetadata,
    make_audit_metadata,
    make_risk_metadata,
)


class SnapshotFactory:
    """
    Convenience factory for ExecutionRiskSnapshot instances.

    The primary creation path is ``build_from_pipeline()`` which wraps
    SnapshotBuilder.  The ``create_*`` methods are for tests and minimal
    in-process use only.
    """

    @staticmethod
    def build_from_pipeline(
        lifecycle:        Any,
        engine_result:    Any,
        rule_results:     List[Any],
        control_decision: Any,
        *,
        correlation_id:  str = "",
        extra_metadata:  Dict[str, Any] | None = None,
        risk_statistics: Dict[str, Any] | None = None,
    ) -> ExecutionRiskSnapshot:
        """
        Build a snapshot from the four pipeline inputs (M1–M4).

        This is the primary production entry point.
        """
        builder = (
            SnapshotBuilder()
            .with_lifecycle(lifecycle)
            .with_engine_result(engine_result)
            .with_rule_results(rule_results)
            .with_control_decision(control_decision)
        )
        if correlation_id:
            builder.with_correlation_id(correlation_id)
        if extra_metadata:
            builder.with_extra_metadata(**extra_metadata)
        if risk_statistics:
            builder.with_risk_statistics(risk_statistics)
        return builder.build()

    @staticmethod
    def create_minimal(
        *,
        risk_id:          str = "",
        execution_id:     str = "",
        order_id:         str = "",
        portfolio_id:     str = "",
        strategy_id:      str = "",
        risk_state:       str = "PASSED",
        control_action:   str = "ALLOW",
        final_action:     str = "ALLOW",
        risk_category:    str = "EXECUTION",
        status:           SnapshotStatus = SnapshotStatus.CREATED,
        extra_metadata:   Dict[str, Any] | None = None,
    ) -> ExecutionRiskSnapshot:
        """
        Create a minimal snapshot with default values.

        Intended for unit tests and tooling — NOT for production.
        """
        audit_md = make_audit_metadata(
            created_by="factory:minimal",
            framework_version=VERSION,
            source_module="snapshot.factory",
        )
        risk_md = make_risk_metadata(
            risk_category=risk_category,
            evaluation_duration_ms=0.0,
        )
        return ExecutionRiskSnapshot(
            snapshot_id=str(uuid.uuid4()),
            snapshot_version=SNAPSHOT_VERSION,
            risk_id=risk_id or str(uuid.uuid4()),
            execution_id=execution_id or str(uuid.uuid4()),
            order_id=order_id,
            position_id="",
            portfolio_id=portfolio_id,
            workflow_id="",
            decision_id=str(uuid.uuid4()),
            strategy_id=strategy_id,
            correlation_id="",
            risk_category=risk_category,
            risk_state=risk_state,
            control_action=control_action,
            final_action=final_action,
            policy_used="HIGHEST_SEVERITY",
            triggered_rules=(),
            warnings=(),
            blocks=(),
            override_status=False,
            emergency_status=False,
            evaluation_duration_ms=0.0,
            snapshot_timestamp=time.time(),
            risk_metadata=risk_md,
            audit_metadata=audit_md,
            override_metadata=None,
            framework_version=VERSION,
            status=status,
            risk_statistics={},
            extra_metadata=extra_metadata or {},
        )

    @staticmethod
    def create_allow_snapshot(**kw) -> ExecutionRiskSnapshot:
        kw.setdefault("risk_state",     "PASSED")
        kw.setdefault("control_action", "ALLOW")
        kw.setdefault("final_action",   "ALLOW")
        kw.setdefault("status",         SnapshotStatus.PUBLISHED)
        return SnapshotFactory.create_minimal(**kw)

    @staticmethod
    def create_block_snapshot(**kw) -> ExecutionRiskSnapshot:
        kw.setdefault("risk_state",     "BLOCKED")
        kw.setdefault("control_action", "BLOCK")
        kw.setdefault("final_action",   "BLOCK")
        kw.setdefault("status",         SnapshotStatus.PUBLISHED)
        return SnapshotFactory.create_minimal(**kw)

    @staticmethod
    def create_warning_snapshot(**kw) -> ExecutionRiskSnapshot:
        kw.setdefault("risk_state",     "WARNING")
        kw.setdefault("control_action", "ALLOW_WITH_WARNING")
        kw.setdefault("final_action",   "ALLOW_WITH_WARNING")
        kw.setdefault("status",         SnapshotStatus.PUBLISHED)
        return SnapshotFactory.create_minimal(**kw)

    @staticmethod
    def create_emergency_snapshot(**kw) -> ExecutionRiskSnapshot:
        kw.setdefault("risk_state",     "BLOCKED")
        kw.setdefault("control_action", "EMERGENCY_STOP")
        kw.setdefault("final_action",   "EMERGENCY_STOP")
        kw.setdefault("status",         SnapshotStatus.PUBLISHED)
        kw.setdefault("extra_metadata", {"emergency_reason": "manual"})
        return SnapshotFactory.create_minimal(**kw)
