"""iios/execution/gateway/engine/gateway_snapshot.py
==================================================
GatewayEngineSnapshot and GatewayRequestSummary — point-in-time
snapshots of the Execution Gateway Engine state.

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import RequestStatus, VERSION
from .gateway_statistics import GatewayEngineStatistics


# ── GatewayRequestSummary ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class GatewayRequestSummary:
    """
    Lightweight, serialisable summary of a single engine gateway request.

    Included in ``GatewayEngineSnapshot.recent_requests``.
    """

    request_id:           str
    lifecycle_request_id: str
    status:               str     # RequestStatus.value
    execution_id:         str
    portfolio_id:         str
    strategy_id:          str
    order_id:             str
    symbol:               str
    queue_type:           str
    priority:             int
    retry_count:          int
    dispatch_outcome:     Optional[str]
    created_at:           float
    lifecycle_elapsed_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":           self.request_id,
            "lifecycle_request_id": self.lifecycle_request_id,
            "status":               self.status,
            "execution_id":         self.execution_id,
            "portfolio_id":         self.portfolio_id,
            "strategy_id":          self.strategy_id,
            "order_id":             self.order_id,
            "symbol":               self.symbol,
            "queue_type":           self.queue_type,
            "priority":             self.priority,
            "retry_count":          self.retry_count,
            "dispatch_outcome":     self.dispatch_outcome,
            "created_at":           self.created_at,
            "lifecycle_elapsed_ms": self.lifecycle_elapsed_ms,
        }


# ── GatewayEngineSnapshot ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class GatewayEngineSnapshot:
    """
    Immutable point-in-time snapshot of the Execution Gateway Engine.

    Produced by ``ExecutionGatewayEngine.snapshot()`` and
    ``GatewayManager.snapshot()``.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    snapshot_id:   str
    engine_state:  str    # EngineState.value

    # ── Counts ────────────────────────────────────────────────────────────────
    total_requests:      int
    pending_count:       int
    queued_count:        int
    dispatching_count:   int
    completed_count:     int
    failed_count:        int
    cancelled_count:     int
    retrying_count:      int
    active_session_count: int

    # ── Queue sizes ───────────────────────────────────────────────────────────
    queue_sizes: Dict[str, int]

    # ── Recent activity ───────────────────────────────────────────────────────
    recent_requests: Tuple[GatewayRequestSummary, ...]

    # ── Statistics ────────────────────────────────────────────────────────────
    statistics: GatewayEngineStatistics

    # ── Timing ────────────────────────────────────────────────────────────────
    taken_at: float
    version:  str = VERSION

    # ── Metadata ──────────────────────────────────────────────────────────────
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def total_active(self) -> int:
        return self.pending_count + self.queued_count + self.dispatching_count + self.retrying_count

    @property
    def total_ended(self) -> int:
        return self.completed_count + self.failed_count + self.cancelled_count

    @property
    def completion_rate(self) -> float:
        ended = self.total_ended
        return self.completed_count / ended if ended else 0.0

    @property
    def failure_rate(self) -> float:
        ended = self.total_ended
        return self.failed_count / ended if ended else 0.0

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":         self.snapshot_id,
            "engine_state":        self.engine_state,
            "total_requests":      self.total_requests,
            "pending_count":       self.pending_count,
            "queued_count":        self.queued_count,
            "dispatching_count":   self.dispatching_count,
            "completed_count":     self.completed_count,
            "failed_count":        self.failed_count,
            "cancelled_count":     self.cancelled_count,
            "retrying_count":      self.retrying_count,
            "active_session_count": self.active_session_count,
            "total_active":        self.total_active,
            "total_ended":         self.total_ended,
            "queue_sizes":         dict(self.queue_sizes),
            "recent_requests":     [r.to_dict() for r in self.recent_requests],
            "statistics":          self.statistics.to_dict(),
            "taken_at":            self.taken_at,
            "version":             self.version,
            "metadata":            dict(self.metadata),
        }
