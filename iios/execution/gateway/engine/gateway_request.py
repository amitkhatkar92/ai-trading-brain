"""iios/execution/gateway/engine/gateway_request.py
==================================================
EngineGatewayRequest — mutable engine-level record tracking the full
lifecycle of a single request submitted to the Execution Gateway Engine.

Distinct from the M1 lifecycle GatewayRequest.  This record is owned
and mutated by the GatewayManager as the request progresses through
each workflow stage.

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

from .constants import (
    ACTIVE_REQUEST_STATUSES,
    TERMINAL_REQUEST_STATUSES,
    DispatchOutcome,
    QueueType,
    RequestStatus,
)
from .gateway_context import EngineGatewayContext


class EngineGatewayRequest:
    """
    Mutable engine-level request record.

    Tracks status, timing, dispatch outcome, retry metadata, and linking
    IDs for the M1 lifecycle and broker abstraction.

    Thread safety is provided by an internal RLock.
    """

    __slots__ = (
        # identity
        "_request_id",
        # context
        "_context",
        # state
        "_status",
        # cross-module links
        "_session_id",
        "_lifecycle_request_id",   # M1 GatewayRequest.gateway_id
        # queue
        "_queue_type",
        "_priority",
        # retry
        "_retry_count",
        "_max_retries",
        # timestamps
        "_created_at",
        "_updated_at",
        "_queued_at",
        "_dispatched_at",
        "_completed_at",
        # dispatch result
        "_dispatch_outcome",
        "_dispatch_result",
        # error
        "_error_code",
        "_error_message",
        # thread safety
        "_lock",
    )

    def __init__(
        self,
        context:      EngineGatewayContext,
        session_id:   str = "",
        max_retries:  int = 3,
        queue_type:   QueueType = QueueType.FIFO,
    ) -> None:
        self._request_id           = context.request_id
        self._context              = context
        self._status               = RequestStatus.PENDING
        self._session_id           = session_id
        self._lifecycle_request_id = ""
        self._queue_type           = queue_type
        self._priority             = context.priority
        self._retry_count          = 0
        self._max_retries          = max(0, max_retries)
        self._created_at           = time.time()
        self._updated_at           = self._created_at
        self._queued_at:    Optional[float] = None
        self._dispatched_at: Optional[float] = None
        self._completed_at: Optional[float] = None
        self._dispatch_outcome: Optional[DispatchOutcome] = None
        self._dispatch_result: Dict[str, Any] = {}
        self._error_code    = ""
        self._error_message = ""
        self._lock          = threading.RLock()

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def request_id(self) -> str:
        return self._request_id

    @property
    def context(self) -> EngineGatewayContext:
        return self._context

    # ── Convenience delegation from context ───────────────────────────────────

    @property
    def execution_id(self) -> str:
        return self._context.execution_id

    @property
    def order_id(self) -> str:
        return self._context.order_id

    @property
    def portfolio_id(self) -> str:
        return self._context.portfolio_id

    @property
    def strategy_id(self) -> str:
        return self._context.strategy_id

    @property
    def symbol(self) -> str:
        return self._context.symbol

    @property
    def side(self) -> str:
        return self._context.side

    # ── Mutable state ─────────────────────────────────────────────────────────

    @property
    def status(self) -> RequestStatus:
        with self._lock:
            return self._status

    def set_status(self, status: RequestStatus) -> None:
        with self._lock:
            self._status     = status
            self._updated_at = time.time()

    @property
    def session_id(self) -> str:
        with self._lock:
            return self._session_id

    def set_session_id(self, session_id: str) -> None:
        with self._lock:
            self._session_id = session_id
            self._updated_at = time.time()

    @property
    def lifecycle_request_id(self) -> str:
        with self._lock:
            return self._lifecycle_request_id

    def set_lifecycle_request_id(self, lc_id: str) -> None:
        with self._lock:
            self._lifecycle_request_id = lc_id
            self._updated_at           = time.time()

    @property
    def queue_type(self) -> QueueType:
        with self._lock:
            return self._queue_type

    def set_queue_type(self, queue_type: QueueType) -> None:
        with self._lock:
            self._queue_type = queue_type
            self._updated_at = time.time()

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def retry_count(self) -> int:
        with self._lock:
            return self._retry_count

    @property
    def max_retries(self) -> int:
        return self._max_retries

    def increment_retry(self) -> None:
        with self._lock:
            self._retry_count += 1
            self._updated_at   = time.time()

    # ── Timestamps ────────────────────────────────────────────────────────────

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        with self._lock:
            return self._updated_at

    @property
    def queued_at(self) -> Optional[float]:
        with self._lock:
            return self._queued_at

    def mark_queued(self) -> None:
        with self._lock:
            self._queued_at  = time.time()
            self._updated_at = self._queued_at

    @property
    def dispatched_at(self) -> Optional[float]:
        with self._lock:
            return self._dispatched_at

    def mark_dispatched(self) -> None:
        with self._lock:
            self._dispatched_at = time.time()
            self._updated_at    = self._dispatched_at

    @property
    def completed_at(self) -> Optional[float]:
        with self._lock:
            return self._completed_at

    def mark_completed(self) -> None:
        with self._lock:
            self._completed_at = time.time()
            self._updated_at   = self._completed_at

    # ── Dispatch result ───────────────────────────────────────────────────────

    @property
    def dispatch_outcome(self) -> Optional[DispatchOutcome]:
        with self._lock:
            return self._dispatch_outcome

    @property
    def dispatch_result(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._dispatch_result)

    def set_dispatch_result(
        self,
        outcome: DispatchOutcome,
        result:  Dict[str, Any],
    ) -> None:
        with self._lock:
            self._dispatch_outcome = outcome
            self._dispatch_result  = dict(result)
            self._updated_at       = time.time()

    # ── Error ─────────────────────────────────────────────────────────────────

    @property
    def error_code(self) -> str:
        with self._lock:
            return self._error_code

    @property
    def error_message(self) -> str:
        with self._lock:
            return self._error_message

    def set_error(self, code: str, message: str) -> None:
        with self._lock:
            self._error_code    = code
            self._error_message = message
            self._updated_at    = time.time()

    # ── Derived state helpers ─────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        return self._status in ACTIVE_REQUEST_STATUSES

    @property
    def is_terminal(self) -> bool:
        return self._status in TERMINAL_REQUEST_STATUSES

    @property
    def is_completed(self) -> bool:
        return self._status == RequestStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self._status == RequestStatus.FAILED

    @property
    def is_cancelled(self) -> bool:
        return self._status == RequestStatus.CANCELLED

    @property
    def can_retry(self) -> bool:
        with self._lock:
            return self._retry_count < self._max_retries

    @property
    def lifecycle_elapsed_ms(self) -> float:
        """Milliseconds from creation to now (or completion)."""
        with self._lock:
            end = self._completed_at or time.time()
            return max(0.0, (end - self._created_at) * 1_000.0)

    @property
    def queue_wait_ms(self) -> float:
        """Milliseconds spent in queue (queued_at → dispatched_at)."""
        with self._lock:
            if self._queued_at is None:
                return 0.0
            end = self._dispatched_at or time.time()
            return max(0.0, (end - self._queued_at) * 1_000.0)

    @property
    def dispatch_elapsed_ms(self) -> float:
        """Milliseconds from dispatch start to completion."""
        with self._lock:
            if self._dispatched_at is None:
                return 0.0
            end = self._completed_at or time.time()
            return max(0.0, (end - self._dispatched_at) * 1_000.0)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "request_id":           self._request_id,
                "status":               self._status.value,
                "session_id":           self._session_id,
                "lifecycle_request_id": self._lifecycle_request_id,
                "queue_type":           self._queue_type.value,
                "priority":             self._priority,
                "retry_count":          self._retry_count,
                "max_retries":          self._max_retries,
                "created_at":           self._created_at,
                "updated_at":           self._updated_at,
                "queued_at":            self._queued_at,
                "dispatched_at":        self._dispatched_at,
                "completed_at":         self._completed_at,
                "dispatch_outcome":     self._dispatch_outcome.value if self._dispatch_outcome else None,
                "dispatch_result":      dict(self._dispatch_result),
                "error_code":           self._error_code,
                "error_message":        self._error_message,
                "lifecycle_elapsed_ms": self.lifecycle_elapsed_ms,
                "context":              self._context.to_dict(),
            }

    def __repr__(self) -> str:
        return (
            f"EngineGatewayRequest("
            f"request_id={self._request_id!r}, "
            f"status={self._status.value!r}, "
            f"execution_id={self._context.execution_id!r})"
        )
