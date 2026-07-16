"""iios/execution/context/execution_context_registry.py
==================================================
ExecutionContextRegistry — IIOS v1.0 thread-safe registry of
ExecutionContext objects.

Responsibilities
----------------
• Store and retrieve ExecutionContext objects.
• Maintain secondary indexes (by execution_id, workflow_id, status).
• Track history revisions per execution.
• Accumulate aggregate statistics.
• Dispatch events to registered listeners.

C6 Execution Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from iios.common.errors.error_context import ErrorContext
from iios.common.errors.error_manager import get_error_manager as _get_err_mgr
from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from .constants import (
    ACTOR_REGISTRY,
    ACTOR_SYSTEM,
    ContextStatus,
    DEFAULT_MAX_CONTEXTS,
    DEFAULT_MAX_HISTORY,
    REGISTRY_SYSTEM_ID,
    VERSION,
)
from .exceptions import (
    ContextCapacityError,
    ContextNotFoundError,
    ContextRegistryNotRunning,
    DuplicateContextError,
)
from .execution_context import ExecutionContext
from .execution_context_events import (
    ExecutionContextEvent,
    ExecutionContextEventType,
    make_context_event,
)
from .execution_context_history import (
    ContextRevision,
    ExecutionContextHistory,
    make_revision,
)
from .execution_context_statistics import ContextBuildStatistics, ExecutionContextStatistics

_log   = get_logger(__name__, engine_id=REGISTRY_SYSTEM_ID)
_audit = get_audit_logger(__name__, engine_id=REGISTRY_SYSTEM_ID,
                          component="ExecutionContextRegistry")


@dataclass
class ContextRecord:
    """Container for a registered ExecutionContext and its history."""

    context_id:   str
    execution_id: str
    context:      ExecutionContext
    history:      ExecutionContextHistory = field(init=False)
    registered_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        self.history = ExecutionContextHistory(
            self.execution_id,
            max_entries=DEFAULT_MAX_HISTORY,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id":    self.context_id,
            "execution_id":  self.execution_id,
            "registered_at": self.registered_at,
            "revision_count": self.history.count(),
            "context":       self.context.to_dict(),
        }


class ExecutionContextRegistry(LifecycleAwareMixin):
    """
    IIOS v1.0 registry for ExecutionContext objects.

    Thread-safe. Lifecycle-aware. Dispatches events to listeners.
    """

    SYSTEM_ID = REGISTRY_SYSTEM_ID
    VERSION   = VERSION

    def __init__(self, max_contexts: int = DEFAULT_MAX_CONTEXTS) -> None:
        self._records:    dict[str, ContextRecord]    = {}
        # Secondary indexes
        self._by_execution: dict[str, list[str]]      = {}  # execution_id → [context_id]
        self._by_workflow:  dict[str, list[str]]      = {}  # workflow_id → [context_id]
        self._by_status:    dict[ContextStatus, list[str]] = {s: [] for s in ContextStatus}
        self._max_contexts  = max_contexts
        self._lock          = threading.RLock()
        self._listeners:    list[Callable[[ExecutionContextEvent], None]] = []
        self._statistics    = ExecutionContextStatistics()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "STOPPED", "RUNNING", self.VERSION
        )
        _log.info("ExecutionContextRegistry started.", capacity=self._max_contexts)

    def _on_stop(self) -> None:
        _audit.log_lifecycle_event(
            self.SYSTEM_ID, "RUNNING", "STOPPED", self.VERSION
        )
        _log.info("ExecutionContextRegistry stopped.", registered=len(self._records))

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state() == EngineState.RUNNING

    def _assert_running(self) -> None:
        if not self.is_running:
            raise ContextRegistryNotRunning(
                "ExecutionContextRegistry must be started before use."
            )

    # ── Registration ──────────────────────────────────────────────────────────

    def register(
        self,
        context:  ExecutionContext,
        overwrite: bool = False,
    ) -> ContextRecord:
        """Register an ExecutionContext."""
        self._assert_running()
        ctx_id = context.context_id
        with self._lock:
            if ctx_id in self._records and not overwrite:
                raise DuplicateContextError(ctx_id)
            if (
                len(self._records) >= self._max_contexts
                and ctx_id not in self._records
            ):
                raise ContextCapacityError(
                    f"Registry capacity reached ({self._max_contexts})"
                )
            record = ContextRecord(
                context_id   = ctx_id,
                execution_id = context.execution_id,
                context      = context,
            )
            # Record initial revision
            rev = make_revision(
                context, revision=0,
                actor=ACTOR_REGISTRY, reason="registered",
            )
            record.history.record(rev)
            self._records[ctx_id] = record

            # Update indexes
            self._by_execution.setdefault(context.execution_id, []).append(ctx_id)
            self._by_workflow.setdefault(context.workflow_id,   []).append(ctx_id)
            self._by_status[context.status].append(ctx_id)

        _log.info("ExecutionContext registered.",
                  context_id=ctx_id, execution_id=context.execution_id)
        _audit.log_workflow_event(
            self.SYSTEM_ID, "register", "CONTEXT_REGISTERED",
            actor=ACTOR_REGISTRY,
            context_id=ctx_id,
            execution_id=context.execution_id,
        )
        event = make_context_event(
            ExecutionContextEventType.CONTEXT_CREATED,
            ctx_id,
            execution_id  = context.execution_id,
            workflow_id   = context.workflow_id,
            execution_mode = context.execution_mode,
            status         = context.status,
        )
        self._dispatch(event)
        return record

    def update_status(
        self,
        context_id: str,
        new_status: ContextStatus,
        *,
        actor:  str = ACTOR_SYSTEM,
        reason: str = "",
    ) -> ContextRecord:
        """Update the status of a registered context (creates a new revision)."""
        self._assert_running()
        with self._lock:
            record = self._get_or_raise(context_id)
            old_status = record.context.status

            # Replace the frozen context with a new one carrying the updated status
            import dataclasses
            new_ctx = dataclasses.replace(record.context, status=new_status)
            record.context = new_ctx

            # Update status index
            if context_id in self._by_status[old_status]:
                self._by_status[old_status].remove(context_id)
            self._by_status[new_status].append(context_id)

            # Record revision
            rev_num = record.history.count()
            rev = make_revision(new_ctx, revision=rev_num, actor=actor, reason=reason)
            record.history.record(rev)

        # Dispatch event
        et_map = {
            ContextStatus.VALIDATED: ExecutionContextEventType.CONTEXT_VALIDATED,
            ContextStatus.PUBLISHED: ExecutionContextEventType.CONTEXT_PUBLISHED,
            ContextStatus.REJECTED:  ExecutionContextEventType.CONTEXT_REJECTED,
            ContextStatus.ARCHIVED:  ExecutionContextEventType.CONTEXT_ARCHIVED,
        }
        if new_status in et_map:
            event = make_context_event(
                et_map[new_status],
                context_id,
                execution_id  = record.context.execution_id,
                workflow_id   = record.context.workflow_id,
                execution_mode = record.context.execution_mode,
                status         = new_status,
            )
            self._dispatch(event)
        return record

    # ── Queries ───────────────────────────────────────────────────────────────

    def get(self, context_id: str) -> ExecutionContext:
        self._assert_running()
        with self._lock:
            return self._get_or_raise(context_id).context

    def get_record(self, context_id: str) -> ContextRecord:
        self._assert_running()
        with self._lock:
            return self._get_or_raise(context_id)

    def contains(self, context_id: str) -> bool:
        with self._lock:
            return context_id in self._records

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    def get_by_execution(self, execution_id: str) -> list[ExecutionContext]:
        self._assert_running()
        with self._lock:
            ids = self._by_execution.get(execution_id, [])
            return [self._records[cid].context for cid in ids if cid in self._records]

    def get_by_workflow(self, workflow_id: str) -> list[ExecutionContext]:
        self._assert_running()
        with self._lock:
            ids = self._by_workflow.get(workflow_id, [])
            return [self._records[cid].context for cid in ids if cid in self._records]

    def get_by_status(self, status: ContextStatus) -> list[ExecutionContext]:
        self._assert_running()
        with self._lock:
            ids = self._by_status.get(status, [])
            return [self._records[cid].context for cid in ids if cid in self._records]

    def get_history(self, context_id: str) -> ExecutionContextHistory:
        self._assert_running()
        with self._lock:
            return self._get_or_raise(context_id).history

    def all_context_ids(self) -> list[str]:
        with self._lock:
            return list(self._records.keys())

    # ── Statistics ────────────────────────────────────────────────────────────

    def record_build(self, build_stats: ContextBuildStatistics) -> None:
        self._statistics.record_build(build_stats)

    def statistics(self) -> ExecutionContextStatistics:
        return self._statistics

    # ── Listeners ─────────────────────────────────────────────────────────────

    def add_listener(
        self,
        fn: Callable[[ExecutionContextEvent], None],
    ) -> None:
        with self._lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

    def remove_listener(
        self,
        fn: Callable[[ExecutionContextEvent], None],
    ) -> None:
        with self._lock:
            self._listeners = [f for f in self._listeners if f != fn]

    def _dispatch(self, event: ExecutionContextEvent) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception:
                _log.warning("Context event listener raised — continuing.")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_or_raise(self, context_id: str) -> ContextRecord:
        record = self._records.get(context_id)
        if record is None:
            raise ContextNotFoundError(context_id)
        return record
