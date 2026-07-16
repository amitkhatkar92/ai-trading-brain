"""iios/execution/engine/execution_registry.py
==================================================
ExecutionRegistry — thread-safe store of all execution records.

Responsibilities
----------------
• Register new executions (ExecutionRecord).
• Track state transitions and history.
• Maintain secondary indexes (by portfolio, strategy, state).
• Accumulate engine-level statistics.
• Provide query methods (active, completed, failed, by-id).

IIOS v1.0 framework: LifecycleAwareMixin, logging, audit, error handling.

C6 Execution Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from iios.common.errors.error_context import ErrorContext
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import ACTOR_REGISTRY, DEFAULT_MAX_EXECUTIONS, REGISTRY_SYSTEM_ID, VERSION
from .exceptions import (
    DuplicateExecutionError, ExecutionCapacityError, ExecutionEngineNotRunningError,
    ExecutionNotFoundError, ExecutionStateError,
)
from .execution_context import ExecutionContext
from .execution_events import ExecutionEvent
from .execution_history import ExecutionHistory, make_history_entry
from .execution_result import ExecutionResult
from .execution_snapshot import ExecutionSnapshot
from .execution_state import (
    ACTIVE_ENGINE_STATES, TERMINAL_ENGINE_STATES, EngineExecutionState,
    assert_engine_transition,
)
from .execution_statistics import EngineStatistics, ExecutionStatistics

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID,
                          component="ExecutionRegistry")


@dataclass
class ExecutionRecord:
    """
    Container for all data associated with one execution session.

    Attributes
    ----------
    execution_id  : Unique execution session identifier.
    request_id    : Originating request.
    order_id      : Associated order.
    portfolio_id  : Portfolio this execution belongs to.
    strategy_id   : Originating strategy.
    state         : Current engine execution state.
    context       : ExecutionContext assembled during PREPARING (may be None).
    result        : ExecutionResult set on terminal state (may be None).
    history       : Transition history.
    statistics    : Per-execution timing and outcome metrics.
    created_at    : Unix timestamp of record creation.
    """
    execution_id: str
    request_id:   str
    order_id:     str
    portfolio_id: str
    strategy_id:  str
    state:        EngineExecutionState = EngineExecutionState.IDLE
    context:      Optional[ExecutionContext] = None
    result:       Optional[ExecutionResult]  = None
    history:      ExecutionHistory           = field(init=False)
    statistics:   ExecutionStatistics        = field(init=False)
    created_at:   float                      = field(default_factory=time.time)

    def __post_init__(self) -> None:
        self.history    = ExecutionHistory(self.execution_id)
        self.statistics = ExecutionStatistics(execution_id=self.execution_id,
                                              created_at=self.created_at)

    def set_context(self, context: ExecutionContext) -> None:
        self.context = context

    def set_result(self, result: ExecutionResult) -> None:
        self.result = result

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "request_id":   self.request_id,
            "order_id":     self.order_id,
            "portfolio_id": self.portfolio_id,
            "strategy_id":  self.strategy_id,
            "state":        self.state.value,
            "has_context":  self.context is not None,
            "has_result":   self.result is not None,
            "created_at":   self.created_at,
            "statistics":   self.statistics.to_dict(),
        }


@dataclass
class RegistryStatistics:
    """Point-in-time snapshot of registry counters."""
    total_registered:   int
    active_count:       int
    completed_count:    int
    failed_count:       int
    cancelled_count:    int
    capacity:           int
    utilisation_pct:    float
    engine_statistics:  dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_registered":  self.total_registered,
            "active_count":      self.active_count,
            "completed_count":   self.completed_count,
            "failed_count":      self.failed_count,
            "cancelled_count":   self.cancelled_count,
            "capacity":          self.capacity,
            "utilisation_pct":   round(self.utilisation_pct, 2),
            "engine_statistics": self.engine_statistics,
        }


class ExecutionRegistry(LifecycleAwareMixin):
    """
    Thread-safe registry of execution records.

    Must be started (``registry.start()``) before any operation.

    Parameters
    ----------
    max_executions : int
        Maximum number of records the registry accepts.
    """

    SYSTEM_ID = REGISTRY_SYSTEM_ID
    VERSION   = VERSION

    def __init__(self, max_executions: int = DEFAULT_MAX_EXECUTIONS) -> None:
        super().__init__()
        self._max_executions = max(1, max_executions)

        # Primary store
        self._records: Dict[str, ExecutionRecord] = {}

        # Secondary indexes
        self._by_portfolio: Dict[str, List[str]] = defaultdict(list)
        self._by_strategy:  Dict[str, List[str]] = defaultdict(list)
        self._by_state:     Dict[str, List[str]] = defaultdict(list)

        # Aggregate statistics
        self._engine_stats = EngineStatistics()

        # Event listeners
        self._listeners: List[Callable[[ExecutionEvent], None]] = []

        # Registry lock
        self._lock = threading.RLock()

    # ── LifecycleAwareMixin hooks ─────────────────────────────────────────────

    def _on_start(self) -> None:
        _log.info("ExecutionRegistry started.", max_executions=self._max_executions)
        _audit.log_lifecycle_event(REGISTRY_SYSTEM_ID, "stopped", "started", VERSION)

    def _on_stop(self) -> None:
        with self._lock:
            count = len(self._records)
        _log.info("ExecutionRegistry stopped.", total_records=count)
        _audit.log_lifecycle_event(REGISTRY_SYSTEM_ID, "started", "stopped", VERSION)

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == EngineState.RUNNING

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        execution_id: str,
        request_id:   str,
        order_id:     str,
        portfolio_id: str,
        strategy_id:  str,
    ) -> ExecutionRecord:
        """
        Register a new execution record.

        Returns
        -------
        ExecutionRecord
            The newly created record (initial state IDLE).

        Raises
        ------
        ExecutionEngineNotRunningError
        ExecutionCapacityError
        DuplicateExecutionError
        """
        self._assert_running()
        with self._lock:
            if len(self._records) >= self._max_executions:
                raise ExecutionCapacityError(
                    f"ExecutionRegistry capacity ({self._max_executions}) reached.",
                    code = "EX-007",
                )
            if execution_id in self._records:
                raise DuplicateExecutionError(execution_id)

            record = ExecutionRecord(
                execution_id = execution_id,
                request_id   = request_id,
                order_id     = order_id,
                portfolio_id = portfolio_id,
                strategy_id  = strategy_id,
            )
            self._records[execution_id] = record

            # Update secondary indexes
            self._by_portfolio[portfolio_id].append(execution_id)
            self._by_strategy[strategy_id].append(execution_id)
            self._by_state[EngineExecutionState.IDLE.value].append(execution_id)

            _log.debug(
                "Execution registered.",
                execution_id = execution_id,
                order_id     = order_id,
            )
            return record

    # ── State transitions ─────────────────────────────────────────────────────

    def apply_transition(
        self,
        execution_id: str,
        to_state:     EngineExecutionState,
        *,
        reason:  str = "",
        actor:   str = ACTOR_REGISTRY,
        occurred_at: Optional[float] = None,
    ) -> ExecutionRecord:
        """
        Advance an execution to *to_state*.

        Returns
        -------
        ExecutionRecord
            The updated record.

        Raises
        ------
        ExecutionNotFoundError
        ExecutionStateError
        ExecutionEngineNotRunningError
        """
        self._assert_running()
        with self._lock:
            record = self._get_or_raise(execution_id)
            assert_engine_transition(record.state, to_state, execution_id)

            now = occurred_at if occurred_at is not None else time.time()

            # Update secondary indexes
            old_state_key = record.state.value
            new_state_key = to_state.value
            if execution_id in self._by_state[old_state_key]:
                self._by_state[old_state_key].remove(execution_id)
            self._by_state[new_state_key].append(execution_id)

            # Record history entry
            entry = make_history_entry(
                execution_id = execution_id,
                from_state   = record.state,
                to_state     = to_state,
                reason       = reason,
                actor        = actor,
                occurred_at  = now,
            )
            record.history.record(entry)

            # Update statistics
            record.statistics.on_transition(record.state, to_state, occurred_at=now)

            # Apply state change
            record.state = to_state

            # If terminal, update engine-level statistics
            if to_state in TERMINAL_ENGINE_STATES:
                self._engine_stats.record_completion(record.statistics)

            _log.debug(
                "Execution state advanced.",
                execution_id = execution_id,
                to_state     = to_state.value,
                reason       = reason,
            )
            return record

    def set_context(self, execution_id: str, context: ExecutionContext) -> None:
        """Attach the resolved ExecutionContext to a record."""
        self._assert_running()
        with self._lock:
            record = self._get_or_raise(execution_id)
            record.set_context(context)

    def set_result(self, execution_id: str, result: ExecutionResult) -> None:
        """Attach the final ExecutionResult to a record."""
        self._assert_running()
        with self._lock:
            record = self._get_or_raise(execution_id)
            record.set_result(result)

    # ── Queries ───────────────────────────────────────────────────────────────

    def get(self, execution_id: str) -> ExecutionRecord:
        """
        Retrieve a record by ID.

        Raises
        ------
        ExecutionNotFoundError
        """
        with self._lock:
            return self._get_or_raise(execution_id)

    def contains(self, execution_id: str) -> bool:
        with self._lock:
            return execution_id in self._records

    def get_active(self) -> list[ExecutionRecord]:
        """Return all records in an ACTIVE_ENGINE_STATES state."""
        with self._lock:
            return [
                r for r in self._records.values()
                if r.state in ACTIVE_ENGINE_STATES
            ]

    def get_completed(self) -> list[ExecutionRecord]:
        with self._lock:
            ids = list(self._by_state.get(EngineExecutionState.COMPLETED.value, []))
        return [self._records[eid] for eid in ids if eid in self._records]

    def get_failed(self) -> list[ExecutionRecord]:
        with self._lock:
            ids = list(self._by_state.get(EngineExecutionState.FAILED.value, []))
        return [self._records[eid] for eid in ids if eid in self._records]

    def get_by_portfolio(self, portfolio_id: str) -> list[ExecutionRecord]:
        with self._lock:
            ids = list(self._by_portfolio.get(portfolio_id, []))
        return [self._records[eid] for eid in ids if eid in self._records]

    def get_by_strategy(self, strategy_id: str) -> list[ExecutionRecord]:
        with self._lock:
            ids = list(self._by_strategy.get(strategy_id, []))
        return [self._records[eid] for eid in ids if eid in self._records]

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def statistics(self) -> RegistryStatistics:
        with self._lock:
            active    = sum(1 for r in self._records.values()
                            if r.state in ACTIVE_ENGINE_STATES)
            completed = len(self._by_state.get(EngineExecutionState.COMPLETED.value, []))
            failed    = len(self._by_state.get(EngineExecutionState.FAILED.value, []))
            cancelled = len(self._by_state.get(EngineExecutionState.CANCELLED.value, []))
            total     = len(self._records)
            util      = (total / self._max_executions) * 100.0
        return RegistryStatistics(
            total_registered  = total,
            active_count      = active,
            completed_count   = completed,
            failed_count      = failed,
            cancelled_count   = cancelled,
            capacity          = self._max_executions,
            utilisation_pct   = util,
            engine_statistics = self._engine_stats.to_dict(),
        )

    # ── Event listeners ───────────────────────────────────────────────────────

    def add_listener(self, listener: Callable[[ExecutionEvent], None]) -> None:
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[ExecutionEvent], None]) -> None:
        with self._lock:
            self._listeners = [l for l in self._listeners if l != listener]

    def dispatch(self, event: ExecutionEvent) -> None:
        """Dispatch *event* to all registered listeners (called outside lock)."""
        with self._lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as exc:
                _log.warning(
                    "ExecutionRegistry listener raised an exception; ignoring.",
                    exc = exc,
                )

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_or_raise(self, execution_id: str) -> ExecutionRecord:
        """Caller must hold self._lock."""
        record = self._records.get(execution_id)
        if record is None:
            raise ExecutionNotFoundError(execution_id)
        return record

    def _assert_running(self) -> None:
        if not self.is_running:
            raise ExecutionEngineNotRunningError(
                "ExecutionRegistry is not running. Call start() first.",
                code = "EX-008",
            )
