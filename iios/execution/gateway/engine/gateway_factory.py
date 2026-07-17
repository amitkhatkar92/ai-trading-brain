"""iios/execution/gateway/engine/gateway_factory.py
==================================================
GatewayEngineFactory — stateless factory for Execution Gateway Engine
domain objects.

Creates:
  EngineGatewayContext  — via create_context()
  EngineGatewayRequest  — via create_request()
  GatewaySession        — via create_session()
  GatewayEngineSnapshot — via create_snapshot()
  GatewayResponse       — via create_response()

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from .constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_SESSION_TIMEOUT_SECS,
    VERSION,
    EngineState,
    QueueType,
    RequestStatus,
)
from .gateway_context import EngineGatewayContext
from .gateway_request import EngineGatewayRequest
from .gateway_response import GatewayResponse
from .gateway_session import GatewaySession
from .gateway_snapshot import GatewayEngineSnapshot, GatewayRequestSummary
from .gateway_statistics import GatewayEngineStatistics


class GatewayEngineFactory:
    """
    Stateless factory for Execution Gateway Engine domain objects.

    All methods are static; no instance state is maintained.
    """

    # ── EngineGatewayContext ──────────────────────────────────────────────────

    @staticmethod
    def create_context(
        execution_id: str,
        order_id:     str,
        portfolio_id: str,
        strategy_id:  str,
        **kwargs: Any,
    ) -> EngineGatewayContext:
        """
        Create an ``EngineGatewayContext`` with an auto-generated ``request_id``
        unless one is supplied as a keyword argument.
        """
        request_id = kwargs.pop("request_id", None) or str(uuid.uuid4())
        return EngineGatewayContext(
            request_id=request_id,
            execution_id=execution_id,
            order_id=order_id,
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            **kwargs,
        )

    # ── EngineGatewayRequest ──────────────────────────────────────────────────

    @staticmethod
    def create_request(
        context:     EngineGatewayContext,
        *,
        session_id:  str        = "",
        max_retries: int        = DEFAULT_MAX_RETRIES,
        queue_type:  QueueType  = QueueType.FIFO,
    ) -> EngineGatewayRequest:
        """Create a new ``EngineGatewayRequest`` from a context."""
        return EngineGatewayRequest(
            context=context,
            session_id=session_id,
            max_retries=max_retries,
            queue_type=queue_type,
        )

    # ── GatewaySession ────────────────────────────────────────────────────────

    @staticmethod
    def create_session(
        portfolio_id: str,
        strategy_id:  str,
        execution_id: str,
        *,
        session_id:   Optional[str]            = None,
        timeout_secs: float                    = DEFAULT_SESSION_TIMEOUT_SECS,
        metadata:     Optional[Dict[str, Any]] = None,
    ) -> GatewaySession:
        """Create a new active ``GatewaySession``."""
        return GatewaySession(
            session_id=session_id or str(uuid.uuid4()),
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            execution_id=execution_id,
            timeout_secs=timeout_secs,
            metadata=metadata,
        )

    # ── GatewayEngineSnapshot ─────────────────────────────────────────────────

    @staticmethod
    def create_snapshot(
        engine_state:    EngineState,
        requests:        List[EngineGatewayRequest],
        queue_sizes:     Dict[str, int],
        statistics:      GatewayEngineStatistics,
        active_sessions: int,
        *,
        metadata:    Optional[Dict[str, Any]] = None,
        max_recent:  int                      = 20,
    ) -> GatewayEngineSnapshot:
        """Build an immutable ``GatewayEngineSnapshot``."""
        now = time.time()

        pending_count     = sum(1 for r in requests if r.status == RequestStatus.PENDING)
        queued_count      = sum(1 for r in requests if r.status == RequestStatus.QUEUED)
        dispatching_count = sum(1 for r in requests if r.status == RequestStatus.DISPATCHING)
        completed_count   = sum(1 for r in requests if r.status == RequestStatus.COMPLETED)
        failed_count      = sum(1 for r in requests if r.status == RequestStatus.FAILED)
        cancelled_count   = sum(1 for r in requests if r.status == RequestStatus.CANCELLED)
        retrying_count    = sum(1 for r in requests if r.status == RequestStatus.RETRYING)

        recent = sorted(requests, key=lambda r: r.created_at, reverse=True)[:max_recent]
        recent_summaries = tuple(
            GatewayRequestSummary(
                request_id=r.request_id,
                lifecycle_request_id=r.lifecycle_request_id,
                status=r.status.value,
                execution_id=r.execution_id,
                portfolio_id=r.portfolio_id,
                strategy_id=r.strategy_id,
                order_id=r.order_id,
                symbol=r.symbol,
                queue_type=r.queue_type.value,
                priority=r.priority,
                retry_count=r.retry_count,
                dispatch_outcome=(
                    r.dispatch_outcome.value if r.dispatch_outcome else None
                ),
                created_at=r.created_at,
                lifecycle_elapsed_ms=max(0.0, (now - r.created_at) * 1_000.0),
            )
            for r in recent
        )

        return GatewayEngineSnapshot(
            snapshot_id=str(uuid.uuid4()),
            engine_state=engine_state.value,
            total_requests=len(requests),
            pending_count=pending_count,
            queued_count=queued_count,
            dispatching_count=dispatching_count,
            completed_count=completed_count,
            failed_count=failed_count,
            cancelled_count=cancelled_count,
            retrying_count=retrying_count,
            active_session_count=active_sessions,
            queue_sizes=queue_sizes,
            recent_requests=recent_summaries,
            statistics=statistics.copy(),
            taken_at=now,
            metadata=metadata or {},
        )

    # ── GatewayResponse ───────────────────────────────────────────────────────

    @staticmethod
    def create_response(
        request:       EngineGatewayRequest,
        *,
        is_success:    bool,
        error_code:    str                      = "",
        error_message: str                      = "",
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> GatewayResponse:
        """
        Build a ``GatewayResponse`` from a completed (or failed)
        ``EngineGatewayRequest``.
        """
        end_time   = time.time()
        elapsed_ms = max(0.0, (end_time - request.created_at) * 1_000.0)

        status  = RequestStatus.COMPLETED if is_success else RequestStatus.FAILED
        outcome = request.dispatch_outcome.value if request.dispatch_outcome else None

        return GatewayResponse(
            response_id=str(uuid.uuid4()),
            request_id=request.request_id,
            lifecycle_request_id=request.lifecycle_request_id,
            session_id=request.session_id,
            status=status.value,
            outcome=outcome,
            dispatch_result=dict(request.dispatch_result),
            error_code=error_code or request.error_code,
            error_message=error_message or request.error_message,
            portfolio_id=request.portfolio_id,
            strategy_id=request.strategy_id,
            execution_id=request.execution_id,
            order_id=request.order_id,
            symbol=request.symbol,
            created_at=request.created_at,
            elapsed_ms=elapsed_ms,
            metadata=metadata or {},
        )
