"""iios/execution/snapshot/execution_snapshot_builder.py
==================================================
ExecutionSnapshotBuilder — fluent builder that assembles an
immutable ExecutionSnapshot from validated component parts.

C6 Execution Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import dataclasses
import time
import uuid
from typing import Any, Optional

from iios.common.logging.logging_manager import get_logger

from iios.execution.snapshot.constants import (
    BUILDER_SYSTEM_ID,
    SnapshotLifecycle,
    SnapshotTrigger,
    VERSION,
)
from iios.execution.snapshot.exceptions import (
    SnapshotBuildError,
    SnapshotIncompleteError,
    SnapshotInconsistencyError,
)
from iios.execution.snapshot.execution_snapshot import ExecutionSnapshot
from iios.execution.snapshot.execution_snapshot_metadata import SnapshotAuditMetadata

_log = get_logger(__name__, engine_id=BUILDER_SYSTEM_ID)


class ExecutionSnapshotBuilder:
    """
    Fluent builder that produces an immutable ExecutionSnapshot.

    Usage::

        snap = (
            ExecutionSnapshotBuilder()
            .with_ids(
                execution_id = "EXEC-001",
                workflow_id  = "WF-001",
                order_id     = "ORD-001",
            )
            .with_state("COMPLETED", is_terminal=True, succeeded=True)
            .with_sequence(3)
            .build()
        )
    """

    def __init__(self) -> None:
        # Identity
        self._execution_id:   str = ""
        self._workflow_id:    str = ""
        self._order_id:       str = ""
        self._portfolio_id:   str = ""
        self._decision_id:    str = ""
        self._strategy_id:    str = ""
        self._broker_id:      str = ""
        self._request_id:     str = ""
        self._correlation_id: str = ""
        self._trace_id:       str = ""

        # State
        self._execution_state: str  = "IDLE"
        self._order_state:     str  = ""
        self._is_terminal:     bool = False
        self._succeeded:       bool = False
        self._error_message:   str  = ""
        self._error_code:      str  = ""

        # Lifecycle
        self._lifecycle: SnapshotLifecycle = SnapshotLifecycle.CREATED

        # Timing
        self._captured_at:            float          = 0.0
        self._execution_started_at:   Optional[float] = None
        self._execution_ended_at:     Optional[float] = None
        self._duration_ms:            float          = 0.0

        # Context ref
        self._context_id:             str   = ""
        self._context_completeness:   float = 0.0
        self._has_market_snapshot:    bool  = False
        self._has_company_snapshot:   bool  = False
        self._has_strategy_snapshot:  bool  = False
        self._has_portfolio_snapshot: bool  = False
        self._has_decision:           bool  = False

        # Result ref
        self._result_id:           str            = ""
        self._validation_errors:   tuple[str, ...] = ()

        # Statistics
        self._validation_duration_ms:  float = 0.0
        self._preparation_duration_ms: float = 0.0
        self._execution_phase_ms:      float = 0.0

        # Versioning
        self._sequence_number: int = 0
        self._version:         int = 1

        # Audit
        self._audit_metadata:  Optional[SnapshotAuditMetadata] = None
        self._tags:            frozenset[str]   = frozenset()
        self._extra:           dict[str, Any]   = {}

    # ── Fluent setters ────────────────────────────────────────────────────────

    def with_ids(
        self,
        *,
        execution_id:   str = "",
        workflow_id:    str = "",
        order_id:       str = "",
        portfolio_id:   str = "",
        decision_id:    str = "",
        strategy_id:    str = "",
        broker_id:      str = "",
        request_id:     str = "",
        correlation_id: str = "",
        trace_id:       str = "",
    ) -> "ExecutionSnapshotBuilder":
        self._execution_id   = execution_id   or self._execution_id
        self._workflow_id    = workflow_id    or self._workflow_id
        self._order_id       = order_id       or self._order_id
        self._portfolio_id   = portfolio_id   or self._portfolio_id
        self._decision_id    = decision_id    or self._decision_id
        self._strategy_id    = strategy_id    or self._strategy_id
        self._broker_id      = broker_id      or self._broker_id
        self._request_id     = request_id     or self._request_id
        self._correlation_id = correlation_id or self._correlation_id
        self._trace_id       = trace_id       or self._trace_id
        return self

    def with_state(
        self,
        execution_state: str,
        *,
        order_state:   str  = "",
        is_terminal:   bool = False,
        succeeded:     bool = False,
        error_message: str  = "",
        error_code:    str  = "",
    ) -> "ExecutionSnapshotBuilder":
        self._execution_state = execution_state
        self._order_state     = order_state
        self._is_terminal     = is_terminal
        self._succeeded       = succeeded
        self._error_message   = error_message
        self._error_code      = error_code
        return self

    def with_lifecycle(
        self,
        lifecycle: SnapshotLifecycle,
    ) -> "ExecutionSnapshotBuilder":
        self._lifecycle = lifecycle
        return self

    def with_timing(
        self,
        *,
        captured_at:           float          = 0.0,
        execution_started_at:  Optional[float] = None,
        execution_ended_at:    Optional[float] = None,
        duration_ms:           float          = 0.0,
    ) -> "ExecutionSnapshotBuilder":
        self._captured_at           = captured_at
        self._execution_started_at  = execution_started_at
        self._execution_ended_at    = execution_ended_at
        self._duration_ms           = duration_ms
        return self

    def with_context_ref(
        self,
        *,
        context_id:            str   = "",
        completeness:          float = 0.0,
        has_market_snapshot:   bool  = False,
        has_company_snapshot:  bool  = False,
        has_strategy_snapshot: bool  = False,
        has_portfolio_snapshot: bool = False,
        has_decision:          bool  = False,
    ) -> "ExecutionSnapshotBuilder":
        self._context_id             = context_id
        self._context_completeness   = completeness
        self._has_market_snapshot    = has_market_snapshot
        self._has_company_snapshot   = has_company_snapshot
        self._has_strategy_snapshot  = has_strategy_snapshot
        self._has_portfolio_snapshot = has_portfolio_snapshot
        self._has_decision           = has_decision
        return self

    def with_result_ref(
        self,
        result_id:        str,
        validation_errors: tuple[str, ...] = (),
    ) -> "ExecutionSnapshotBuilder":
        self._result_id         = result_id
        self._validation_errors = validation_errors
        return self

    def with_statistics(
        self,
        *,
        validation_duration_ms:  float = 0.0,
        preparation_duration_ms: float = 0.0,
        execution_phase_ms:      float = 0.0,
    ) -> "ExecutionSnapshotBuilder":
        self._validation_duration_ms  = validation_duration_ms
        self._preparation_duration_ms = preparation_duration_ms
        self._execution_phase_ms      = execution_phase_ms
        return self

    def with_sequence(
        self,
        sequence_number: int,
        version:         int = 1,
    ) -> "ExecutionSnapshotBuilder":
        self._sequence_number = sequence_number
        self._version         = version
        return self

    def with_audit(
        self,
        trigger:            SnapshotTrigger = SnapshotTrigger.STATE_TRANSITION,
        parent_snapshot_id: str = "",
        *,
        created_by: str = "iios:system",
        tags:       frozenset[str] = frozenset(),
    ) -> "ExecutionSnapshotBuilder":
        self._audit_metadata = SnapshotAuditMetadata(
            created_by          = created_by,
            trigger             = trigger,
            parent_snapshot_id  = parent_snapshot_id,
            sequence_number     = self._sequence_number,
            tags                = tags,
        )
        return self

    def with_tags(self, *tags: str) -> "ExecutionSnapshotBuilder":
        self._tags = frozenset(tags)
        return self

    def with_extra(self, **kwargs: Any) -> "ExecutionSnapshotBuilder":
        self._extra.update(kwargs)
        return self

    # ── Build ─────────────────────────────────────────────────────────────────

    def build(self) -> ExecutionSnapshot:
        """
        Validate required fields and produce an immutable ExecutionSnapshot.

        Raises
        ------
        SnapshotIncompleteError
            If any required identifier is missing.
        SnapshotBuildError
            For any other assembly failure.
        """
        self._assert_required_ids()

        captured_at = self._captured_at or time.time()

        try:
            snap = ExecutionSnapshot(
                execution_id           = self._execution_id,
                workflow_id            = self._workflow_id,
                order_id               = self._order_id,
                portfolio_id           = self._portfolio_id,
                decision_id            = self._decision_id,
                strategy_id            = self._strategy_id,
                broker_id              = self._broker_id,
                request_id             = self._request_id,
                correlation_id         = self._correlation_id,
                trace_id               = self._trace_id,
                execution_state        = self._execution_state,
                order_state            = self._order_state,
                is_terminal            = self._is_terminal,
                succeeded              = self._succeeded,
                error_message          = self._error_message,
                error_code             = self._error_code,
                lifecycle              = self._lifecycle,
                captured_at            = captured_at,
                execution_started_at   = self._execution_started_at,
                execution_ended_at     = self._execution_ended_at,
                duration_ms            = self._duration_ms,
                context_id             = self._context_id,
                context_completeness   = self._context_completeness,
                has_market_snapshot    = self._has_market_snapshot,
                has_company_snapshot   = self._has_company_snapshot,
                has_strategy_snapshot  = self._has_strategy_snapshot,
                has_portfolio_snapshot = self._has_portfolio_snapshot,
                has_decision           = self._has_decision,
                result_id              = self._result_id,
                validation_errors      = self._validation_errors,
                validation_duration_ms  = self._validation_duration_ms,
                preparation_duration_ms = self._preparation_duration_ms,
                execution_phase_ms      = self._execution_phase_ms,
                sequence_number        = self._sequence_number,
                version                = self._version,
                audit_metadata         = self._audit_metadata,
                tags                   = self._tags,
                extra                  = dict(self._extra),
            )
        except Exception as exc:
            raise SnapshotBuildError(f"Failed to assemble ExecutionSnapshot: {exc}") from exc

        _log.info(
            "ExecutionSnapshot built.",
            execution_id = self._execution_id,
            state        = self._execution_state,
            seq          = self._sequence_number,
        )
        return snap

    # ── Internal validation ───────────────────────────────────────────────────

    def _assert_required_ids(self) -> None:
        missing: list[str] = []
        for name, value in [
            ("execution_id", self._execution_id),
            ("workflow_id",  self._workflow_id),
            ("order_id",     self._order_id),
        ]:
            if not value or not value.strip():
                missing.append(name)
        if missing:
            raise SnapshotIncompleteError(
                f"Missing required fields: {missing}",
                missing_fields=tuple(missing),
            )
