"""iios/execution/snapshot/execution_snapshot_factory.py
==================================================
ExecutionSnapshotFactory — builds and validates ExecutionSnapshot
objects, then stores them via ExecutionSnapshotStore.

IIOS v1.0: logging, audit, error handling.

C6 Execution Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_FACTORY,
    FACTORY_SYSTEM_ID,
    SnapshotLifecycle,
    SnapshotTrigger,
    VERSION,
)
from .exceptions import SnapshotBuildError, SnapshotValidationError
from .execution_snapshot import ExecutionSnapshot
from .execution_snapshot_builder import ExecutionSnapshotBuilder
from .execution_snapshot_validator import ExecutionSnapshotValidator, SnapshotValidationResult
from .execution_snapshot_metadata import SnapshotAuditMetadata
from .execution_snapshot_statistics import SnapshotBuildStats

_log   = get_logger(__name__, engine_id=FACTORY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=FACTORY_SYSTEM_ID,
                          component="ExecutionSnapshotFactory")


class ExecutionSnapshotFactory:
    """
    Factory that produces validated, audited ExecutionSnapshot objects.

    Steps per creation:
    1. ExecutionSnapshotBuilder assembles the snapshot.
    2. ExecutionSnapshotValidator validates it.
    3. On pass: lifecycle is set to VALIDATED.
    4. SnapshotBuildStats is populated.

    The factory does NOT store snapshots — that is the responsibility
    of ExecutionSnapshotStore.
    """

    def __init__(self) -> None:
        self._validator = ExecutionSnapshotValidator()

    # ── Main creation interface ───────────────────────────────────────────────

    def create(
        self,
        *,
        execution_id:       str,
        workflow_id:        str,
        order_id:           str,
        execution_state:    str                    = "IDLE",
        is_terminal:        bool                   = False,
        succeeded:          bool                   = False,
        portfolio_id:       str                    = "",
        decision_id:        str                    = "",
        strategy_id:        str                    = "",
        broker_id:          str                    = "",
        request_id:         str                    = "",
        correlation_id:     str                    = "",
        trace_id:           str                    = "",
        order_state:        str                    = "",
        error_message:      str                    = "",
        error_code:         str                    = "",
        context_id:         str                    = "",
        context_completeness: float                = 0.0,
        has_market_snapshot:  bool                 = False,
        has_company_snapshot: bool                 = False,
        has_strategy_snapshot: bool                = False,
        has_portfolio_snapshot: bool               = False,
        has_decision:         bool                 = False,
        result_id:            str                  = "",
        validation_errors:    tuple[str, ...]      = (),
        validation_duration_ms:  float             = 0.0,
        preparation_duration_ms: float             = 0.0,
        execution_phase_ms:      float             = 0.0,
        duration_ms:          float                = 0.0,
        execution_started_at: Optional[float]      = None,
        execution_ended_at:   Optional[float]      = None,
        sequence_number:      int                  = 0,
        version:              int                  = 1,
        trigger:              SnapshotTrigger      = SnapshotTrigger.STATE_TRANSITION,
        parent_snapshot_id:   str                  = "",
        tags:                 frozenset[str]       = frozenset(),
        extra:                dict[str, Any] | None = None,
        strict:               bool                 = False,
    ) -> tuple[ExecutionSnapshot, SnapshotBuildStats]:
        """
        Create and validate an ExecutionSnapshot.

        Returns
        -------
        (ExecutionSnapshot, SnapshotBuildStats)

        Raises
        ------
        SnapshotBuildError       If assembly fails.
        SnapshotValidationError  If validation fails.
        """
        t0 = time.time()

        snap = (
            ExecutionSnapshotBuilder()
            .with_ids(
                execution_id   = execution_id,
                workflow_id    = workflow_id,
                order_id       = order_id,
                portfolio_id   = portfolio_id,
                decision_id    = decision_id,
                strategy_id    = strategy_id,
                broker_id      = broker_id,
                request_id     = request_id,
                correlation_id = correlation_id,
                trace_id       = trace_id,
            )
            .with_state(
                execution_state,
                order_state   = order_state,
                is_terminal   = is_terminal,
                succeeded     = succeeded,
                error_message = error_message,
                error_code    = error_code,
            )
            .with_timing(
                execution_started_at = execution_started_at,
                execution_ended_at   = execution_ended_at,
                duration_ms          = duration_ms,
            )
            .with_context_ref(
                context_id             = context_id,
                completeness           = context_completeness,
                has_market_snapshot    = has_market_snapshot,
                has_company_snapshot   = has_company_snapshot,
                has_strategy_snapshot  = has_strategy_snapshot,
                has_portfolio_snapshot = has_portfolio_snapshot,
                has_decision           = has_decision,
            )
            .with_result_ref(result_id, validation_errors)
            .with_statistics(
                validation_duration_ms  = validation_duration_ms,
                preparation_duration_ms = preparation_duration_ms,
                execution_phase_ms      = execution_phase_ms,
            )
            .with_sequence(sequence_number, version)
            .with_audit(trigger, parent_snapshot_id)
            .with_tags(*tags)
            .with_extra(**(extra or {}))
            .build()
        )
        build_ms = (time.time() - t0) * 1_000

        # Validate
        tv0    = time.time()
        result = self._validator.validate(snap)
        val_ms = (time.time() - tv0) * 1_000

        if not result.passed:
            stats = SnapshotBuildStats(
                snapshot_id        = snap.snapshot_id,
                execution_id       = snap.execution_id,
                build_time_ms      = build_ms,
                validation_passed  = False,
                validation_time_ms = val_ms,
                errors             = result.errors,
            )
            raise SnapshotValidationError(
                "ExecutionSnapshot validation failed.",
                errors=result.errors,
            )

        if strict and result.warnings:
            stats = SnapshotBuildStats(
                snapshot_id        = snap.snapshot_id,
                execution_id       = snap.execution_id,
                build_time_ms      = build_ms,
                validation_passed  = False,
                validation_time_ms = val_ms,
                errors             = result.warnings,
            )
            raise SnapshotValidationError(
                "Snapshot has validation warnings (strict mode).",
                errors=result.warnings,
            )

        import dataclasses
        snap = dataclasses.replace(snap, lifecycle=SnapshotLifecycle.VALIDATED)

        stats = SnapshotBuildStats(
            snapshot_id        = snap.snapshot_id,
            execution_id       = snap.execution_id,
            build_time_ms      = build_ms,
            validation_passed  = True,
            validation_time_ms = val_ms,
            sequence_number    = snap.sequence_number,
        )

        _log.info(
            "ExecutionSnapshot created.",
            snapshot_id  = snap.snapshot_id,
            execution_id = snap.execution_id,
            state        = execution_state,
        )
        _audit.log_workflow_event(
            FACTORY_SYSTEM_ID, "create", "SNAPSHOT_CREATED",
            actor        = ACTOR_FACTORY,
            snapshot_id  = snap.snapshot_id,
            execution_id = snap.execution_id,
        )
        return snap, stats

    # ── Identity generation ───────────────────────────────────────────────────

    @staticmethod
    def gen_snapshot_id() -> str:
        return f"SNAP-{uuid.uuid4().hex[:16].upper()}"
