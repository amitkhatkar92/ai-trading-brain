"""iios/execution/positions/engine/position_manager.py
==================================================
PositionManager — internal coordinator for all Position Engine
operations.

Implements the six operations (create / update / close / sync /
archive / query) using M1 Position Lifecycle components, and maintains
engine-level statistics, history, and events.

C6 Execution Intelligence — Phase 3, Module 2
"""
from __future__ import annotations

import copy
import threading
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger

from iios.execution.positions.lifecycle import (
    ACTIVE_STATES,
    Position,
    PositionState,
)

from .constants import (
    ACTOR_ENGINE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POSITIONS,
    MANAGER_SYSTEM_ID,
    OperationType,
    EngineEventType,
    VERSION,
)
from .exceptions import (
    PositionArchiveError,
    PositionCloseError,
    PositionCreationError,
    PositionEngineNotRunningError,
    PositionOperationError,
    PositionQueryError,
    PositionSyncError,
    PositionUpdateError,
)
from .position_events import (
    EngineEvent,
    make_engine_started_event,
    make_engine_stopped_event,
    make_position_archived_event,
    make_position_closed_event,
    make_position_created_event,
    make_position_synchronized_event,
    make_position_updated_event,
)
from .position_factory import EngineFactory
from .position_history import EngineHistory
from .position_registry import EngineRegistry
from .position_request import (
    ArchivePositionRequest,
    ClosePositionRequest,
    CreatePositionRequest,
    QueryPositionRequest,
    SyncPositionRequest,
    UpdatePositionRequest,
)
from .position_result import PositionResult, make_failure_result, make_success_result
from .position_snapshot import EngineSnapshot, make_engine_snapshot
from .position_statistics import EngineStatistics
from .position_validation import EngineValidator

_log   = get_logger(__name__, engine_id=MANAGER_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=MANAGER_SYSTEM_ID)


class PositionManager(LifecycleAwareMixin):
    """
    Internal coordinator for all position engine operations.

    Responsibilities
    ----------------
    * Validate every incoming request (via EngineValidator).
    * Execute the operation using M1 Position Lifecycle objects.
    * Record results in EngineHistory and EngineStatistics.
    * Emit EngineEvents on every successful operation.

    Non-responsibilities
    --------------------
    * No broker logic.
    * No risk calculations.
    * No portfolio optimisation.
    * No execution routing.
    """

    def __init__(
        self,
        max_positions: int = DEFAULT_MAX_POSITIONS,
        max_history:   int = DEFAULT_MAX_HISTORY,
    ) -> None:
        super().__init__()
        self._registry  = EngineRegistry(max_positions=max_positions)
        self._factory   = EngineFactory()
        self._validator = EngineValidator()
        self._statistics = EngineStatistics()
        self._history   = EngineHistory(max_size=max_history)
        self._events:   List[EngineEvent] = []
        self._lock      = threading.Lock()

    # ── LifecycleAwareMixin ───────────────────────────────────────────────────

    def _on_start(self) -> None:
        self._registry.start()
        _audit.log_lifecycle_event(MANAGER_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION)
        _log.info("PositionManager started.")
        self._append_event(make_engine_started_event())

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(MANAGER_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION)
        self._append_event(make_engine_stopped_event())
        _log.info("PositionManager stopped.", position_count=self._registry.count)
        self._registry.stop()

    # ── CREATE ────────────────────────────────────────────────────────────────

    def create_position(self, request: CreatePositionRequest) -> PositionResult:
        """Create a new position and register it in the engine registry."""
        self._assert_running()
        t0 = time.time()

        # Validate
        v = self._validator.validate_create(request)
        if not v.is_valid:
            elapsed = (time.time() - t0) * 1_000
            self._statistics.record_failed()
            r = make_failure_result(
                request.request_id, OperationType.CREATE_POSITION,
                "PE2-009", "; ".join(v.errors), elapsed,
            )
            self._history.append(r)
            return r

        # Create
        try:
            position = self._factory.create_from_request(request)
        except PositionCreationError as exc:
            elapsed = (time.time() - t0) * 1_000
            self._statistics.record_failed()
            r = make_failure_result(
                request.request_id, OperationType.CREATE_POSITION,
                "PE2-003", str(exc), elapsed,
            )
            self._history.append(r)
            return r

        # Register
        self._registry.register(position)

        # Optionally advance to OPENING
        if request.auto_open:
            try:
                position.transition_to(PositionState.OPENING, actor=ACTOR_ENGINE, reason="auto_open")
            except Exception:  # noqa: BLE001
                pass  # Already beyond CREATED — ignore

        elapsed = (time.time() - t0) * 1_000
        self._statistics.record_created(elapsed_ms=elapsed)
        self._registry.notify_transition(position.state)

        self._append_event(
            make_position_created_event(
                position.position_id,
                portfolio_id=position.portfolio_id,
                strategy_id=position.strategy_id,
            )
        )

        r = make_success_result(
            request.request_id, OperationType.CREATE_POSITION,
            position.position_id, elapsed,
            position=position,
        )
        self._history.append(r)
        _log.info(
            "Position created.",
            position_id=position.position_id,
            instrument=position.instrument,
            state=position.state.value,
        )
        return r

    # ── UPDATE ────────────────────────────────────────────────────────────────

    def update_position(self, request: UpdatePositionRequest) -> PositionResult:
        """Update fields and/or lifecycle state of an existing position."""
        self._assert_running()
        t0 = time.time()

        position = self._registry.get(request.position_id)
        if position is None:
            elapsed = (time.time() - t0) * 1_000
            self._statistics.record_failed()
            r = make_failure_result(
                request.request_id, OperationType.UPDATE_POSITION,
                "PE2-002", f"Position '{request.position_id}' not found", elapsed,
                position_id=request.position_id,
            )
            self._history.append(r)
            return r

        v = self._validator.validate_update(position, request)
        if not v.is_valid:
            elapsed = (time.time() - t0) * 1_000
            self._statistics.record_failed()
            r = make_failure_result(
                request.request_id, OperationType.UPDATE_POSITION,
                "PE2-009", "; ".join(v.errors), elapsed,
                position_id=request.position_id,
            )
            self._history.append(r)
            return r

        try:
            # Apply field updates
            if request.has_field_updates:
                if request.open_quantity is not None or request.closed_quantity is not None:
                    oq = request.open_quantity   if request.open_quantity   is not None else position.open_quantity
                    cq = request.closed_quantity if request.closed_quantity is not None else position.closed_quantity
                    position.update_quantities(oq, cq)
                if request.avg_entry_price is not None or request.avg_exit_price is not None:
                    position.update_prices(
                        avg_entry=request.avg_entry_price,
                        avg_exit=request.avg_exit_price,
                    )
                if request.realized_pnl is not None or request.unrealized_pnl is not None:
                    position.update_pnl(
                        realized=request.realized_pnl,
                        unrealized=request.unrealized_pnl,
                    )

            # Apply state transition
            if request.new_state is not None:
                position.transition_to(
                    request.new_state,
                    actor=request.actor or ACTOR_ENGINE,
                    reason=request.reason,
                )
                self._registry.notify_transition(request.new_state)

        except Exception as exc:
            elapsed = (time.time() - t0) * 1_000
            self._statistics.record_failed()
            r = make_failure_result(
                request.request_id, OperationType.UPDATE_POSITION,
                "PE2-004", str(exc), elapsed, position_id=request.position_id,
            )
            self._history.append(r)
            return r

        elapsed = (time.time() - t0) * 1_000
        self._statistics.record_updated(elapsed_ms=elapsed)
        self._append_event(
            make_position_updated_event(
                position.position_id,
                portfolio_id=position.portfolio_id,
                strategy_id=position.strategy_id,
            )
        )

        r = make_success_result(
            request.request_id, OperationType.UPDATE_POSITION,
            position.position_id, elapsed, position=position,
        )
        self._history.append(r)
        return r

    # ── CLOSE ─────────────────────────────────────────────────────────────────

    def close_position(self, request: ClosePositionRequest) -> PositionResult:
        """Drive a position through CLOSING → CLOSED."""
        self._assert_running()
        t0 = time.time()

        position = self._registry.get(request.position_id)
        if position is None:
            elapsed = (time.time() - t0) * 1_000
            self._statistics.record_failed()
            r = make_failure_result(
                request.request_id, OperationType.CLOSE_POSITION,
                "PE2-002", f"Position '{request.position_id}' not found", elapsed,
                position_id=request.position_id,
            )
            self._history.append(r)
            return r

        v = self._validator.validate_close(position, request)
        if not v.is_valid:
            elapsed = (time.time() - t0) * 1_000
            self._statistics.record_failed()
            r = make_failure_result(
                request.request_id, OperationType.CLOSE_POSITION,
                "PE2-009", "; ".join(v.errors), elapsed,
                position_id=request.position_id,
            )
            self._history.append(r)
            return r

        actor  = request.actor or ACTOR_ENGINE
        reason = request.reason

        try:
            # Advance to CLOSING if needed
            if position.state in {PositionState.OPENING, PositionState.OPEN, PositionState.PARTIALLY_CLOSED}:
                position.transition_to(PositionState.CLOSING, actor=actor, reason=reason)

            # Apply exit price and PnL before CLOSED
            if request.avg_exit_price is not None:
                position.update_prices(avg_exit=request.avg_exit_price)
            if request.realized_pnl is not None:
                position.update_pnl(realized=request.realized_pnl)

            # Drive to CLOSED
            position.transition_to(PositionState.CLOSED, actor=actor, reason=reason)
            self._registry.notify_transition(PositionState.CLOSED)

        except Exception as exc:
            elapsed = (time.time() - t0) * 1_000
            self._statistics.record_failed()
            r = make_failure_result(
                request.request_id, OperationType.CLOSE_POSITION,
                "PE2-005", str(exc), elapsed, position_id=request.position_id,
            )
            self._history.append(r)
            return r

        elapsed = (time.time() - t0) * 1_000
        self._statistics.record_closed(elapsed_ms=elapsed)
        self._append_event(
            make_position_closed_event(
                position.position_id,
                portfolio_id=position.portfolio_id,
                strategy_id=position.strategy_id,
            )
        )

        r = make_success_result(
            request.request_id, OperationType.CLOSE_POSITION,
            position.position_id, elapsed, position=position,
        )
        self._history.append(r)
        _log.info("Position closed.", position_id=position.position_id)
        return r

    # ── SYNC ──────────────────────────────────────────────────────────────────

    def sync_position(self, request: SyncPositionRequest) -> PositionResult:
        """
        Synchronize execution data into a position.

        Applies fields from ``ExecutionSnapshot`` (if provided) or from
        individual overrides, then optionally applies a lifecycle transition.
        """
        self._assert_running()
        t0 = time.time()

        position = self._registry.get(request.position_id)
        if position is None:
            elapsed = (time.time() - t0) * 1_000
            self._statistics.record_failed()
            r = make_failure_result(
                request.request_id, OperationType.SYNC_POSITION,
                "PE2-002", f"Position '{request.position_id}' not found", elapsed,
                position_id=request.position_id,
            )
            self._history.append(r)
            return r

        v = self._validator.validate_sync(position, request)
        if not v.is_valid:
            elapsed = (time.time() - t0) * 1_000
            self._statistics.record_failed()
            r = make_failure_result(
                request.request_id, OperationType.SYNC_POSITION,
                "PE2-009", "; ".join(v.errors), elapsed,
                position_id=request.position_id,
            )
            self._history.append(r)
            return r

        try:
            snap = request.execution_snapshot

            # Resolve field values: snapshot → then individual overrides
            oq = snap.open_quantity   if snap else None
            cq = snap.closed_quantity if snap else None
            ae = snap.avg_entry_price if snap else None
            ax = snap.avg_exit_price  if snap else None
            rp = snap.realized_pnl    if snap else None
            up = snap.unrealized_pnl  if snap else None

            # Individual overrides win over snapshot values
            oq = request.open_quantity    if request.open_quantity    is not None else oq
            cq = request.closed_quantity  if request.closed_quantity  is not None else cq
            ae = request.avg_entry_price  if request.avg_entry_price  is not None else ae
            ax = request.avg_exit_price   if request.avg_exit_price   is not None else ax
            rp = request.realized_pnl     if request.realized_pnl     is not None else rp
            up = request.unrealized_pnl   if request.unrealized_pnl   is not None else up

            if oq is not None or cq is not None:
                position.update_quantities(
                    oq if oq is not None else position.open_quantity,
                    cq if cq is not None else position.closed_quantity,
                )
            if ae is not None or ax is not None:
                position.update_prices(avg_entry=ae, avg_exit=ax)
            if rp is not None or up is not None:
                position.update_pnl(realized=rp, unrealized=up)

            if request.new_state is not None:
                position.transition_to(
                    request.new_state,
                    actor=request.actor or ACTOR_ENGINE,
                    reason=request.reason,
                )
                self._registry.notify_transition(request.new_state)

        except Exception as exc:
            elapsed = (time.time() - t0) * 1_000
            self._statistics.record_failed()
            r = make_failure_result(
                request.request_id, OperationType.SYNC_POSITION,
                "PE2-006", str(exc), elapsed, position_id=request.position_id,
            )
            self._history.append(r)
            return r

        elapsed = (time.time() - t0) * 1_000
        self._statistics.record_synchronized(elapsed_ms=elapsed)
        self._append_event(
            make_position_synchronized_event(
                position.position_id,
                portfolio_id=position.portfolio_id,
                strategy_id=position.strategy_id,
            )
        )

        r = make_success_result(
            request.request_id, OperationType.SYNC_POSITION,
            position.position_id, elapsed, position=position,
        )
        self._history.append(r)
        return r

    # ── ARCHIVE ───────────────────────────────────────────────────────────────

    def archive_position(self, request: ArchivePositionRequest) -> PositionResult:
        """Transition a CLOSED position to ARCHIVED."""
        self._assert_running()
        t0 = time.time()

        position = self._registry.get(request.position_id)
        if position is None:
            elapsed = (time.time() - t0) * 1_000
            self._statistics.record_failed()
            r = make_failure_result(
                request.request_id, OperationType.ARCHIVE_POSITION,
                "PE2-002", f"Position '{request.position_id}' not found", elapsed,
                position_id=request.position_id,
            )
            self._history.append(r)
            return r

        v = self._validator.validate_archive(position, request)
        if not v.is_valid:
            elapsed = (time.time() - t0) * 1_000
            self._statistics.record_failed()
            r = make_failure_result(
                request.request_id, OperationType.ARCHIVE_POSITION,
                "PE2-009", "; ".join(v.errors), elapsed,
                position_id=request.position_id,
            )
            self._history.append(r)
            return r

        try:
            position.transition_to(
                PositionState.ARCHIVED,
                actor=request.actor or ACTOR_ENGINE,
                reason=request.reason,
            )
            self._registry.notify_transition(PositionState.ARCHIVED)
        except Exception as exc:
            elapsed = (time.time() - t0) * 1_000
            self._statistics.record_failed()
            r = make_failure_result(
                request.request_id, OperationType.ARCHIVE_POSITION,
                "PE2-007", str(exc), elapsed, position_id=request.position_id,
            )
            self._history.append(r)
            return r

        elapsed = (time.time() - t0) * 1_000
        self._statistics.record_archived(elapsed_ms=elapsed)
        self._append_event(
            make_position_archived_event(
                position.position_id,
                portfolio_id=position.portfolio_id,
                strategy_id=position.strategy_id,
            )
        )

        r = make_success_result(
            request.request_id, OperationType.ARCHIVE_POSITION,
            position.position_id, elapsed, position=position,
        )
        self._history.append(r)
        _log.info("Position archived.", position_id=position.position_id)
        return r

    # ── QUERY ─────────────────────────────────────────────────────────────────

    def query_position(self, request: QueryPositionRequest) -> PositionResult:
        """Query one or more positions by ID or filters."""
        self._assert_running()
        t0 = time.time()

        v = self._validator.validate_query(request)
        if not v.is_valid:
            elapsed = (time.time() - t0) * 1_000
            self._statistics.record_failed()
            r = make_failure_result(
                request.request_id, OperationType.QUERY_POSITION,
                "PE2-009", "; ".join(v.errors), elapsed,
            )
            self._history.append(r)
            return r

        try:
            if request.is_single_lookup:
                pos = self._registry.get(request.position_id)
                positions = [pos] if pos else []
            else:
                positions = self._registry.all()
                if request.portfolio_id:
                    positions = [p for p in positions if p.portfolio_id == request.portfolio_id]
                if request.strategy_id:
                    positions = [p for p in positions if p.strategy_id == request.strategy_id]
                if request.instrument:
                    positions = [p for p in positions if p.instrument == request.instrument]
                if request.state:
                    positions = [p for p in positions if p.state == request.state]
                positions = positions[: request.limit]
        except Exception as exc:
            elapsed = (time.time() - t0) * 1_000
            self._statistics.record_failed()
            r = make_failure_result(
                request.request_id, OperationType.QUERY_POSITION,
                "PE2-008", str(exc), elapsed,
            )
            self._history.append(r)
            return r

        elapsed  = (time.time() - t0) * 1_000
        self._statistics.record_queried(elapsed_ms=elapsed)
        data = {
            "positions": [p.to_dict() for p in positions],
            "count":     len(positions),
        }
        first_pid = positions[0].position_id if positions else ""
        r = make_success_result(
            request.request_id, OperationType.QUERY_POSITION,
            first_pid, elapsed,
            result_count=len(positions), data=data,
        )
        self._history.append(r)
        return r

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot(self) -> EngineSnapshot:
        """Return a full point-in-time snapshot of the engine state."""
        return make_engine_snapshot(
            positions=self._registry.all(),
            statistics=copy.copy(self._statistics),
        )

    # ── Inspection ────────────────────────────────────────────────────────────

    def statistics(self) -> EngineStatistics:
        with self._lock:
            return copy.copy(self._statistics)

    def history(self) -> EngineHistory:
        return self._history

    def events(self) -> List[EngineEvent]:
        with self._lock:
            return list(self._events)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _append_event(self, event: EngineEvent) -> None:
        with self._lock:
            self._events.append(event)

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise PositionEngineNotRunningError()

    # ── Registry passthrough ──────────────────────────────────────────────────

    @property
    def registry(self) -> EngineRegistry:
        return self._registry
