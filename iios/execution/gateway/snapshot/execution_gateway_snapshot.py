"""iios/execution/gateway/snapshot/execution_gateway_snapshot.py
==================================================
ExecutionGatewaySnapshot — the ONLY published representation
of the Execution Gateway subsystem.

Every downstream subsystem MUST consume this object instead of
internal Gateway Engine, Routing Framework, or Broker Abstraction
objects.

The snapshot is:
  • Immutable — all fields are set at creation and never changed.
  • Self-describing — carries all state needed for downstream use.
  • Serializable — fully convertible to / from dict.
  • Versioned — carries a monotonic snapshot_version per execution.
  • Auditable — carries audit_metadata for traceability.

C6 Execution Intelligence — Phase 5, Module 5
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import (
    ACTIVE_GATEWAY_STATES,
    SUCCESSFUL_DISPATCH_STATUSES,
    TERMINAL_GATEWAY_STATES,
    VERSION,
    DispatchStatus,
    GatewayState,
    GatewayStatus,
    QueueStatus,
)


@dataclass(frozen=True)
class ExecutionGatewaySnapshot:
    """
    Immutable, versioned point-in-time snapshot of the Execution Gateway.

    Fields
    ------
    snapshot_id:
        Globally unique ID for this snapshot instance.
    snapshot_version:
        Monotonic version for snapshots sharing the same execution_id.
        Starts at 1.
    gateway_id:
        The Execution Gateway instance that produced this snapshot.
    execution_id:
        Correlation ID linking this snapshot to an ExecutionRequest.
    order_id:
        Order being processed at snapshot time.
    position_id:
        Associated position, if any.
    portfolio_id:
        Owning portfolio.
    workflow_id:
        Execution workflow ID, if available.
    decision_id:
        DebateAndDecision approval ID, if available.
    strategy_id:
        Strategy that generated the execution request.
    gateway_state:
        High-level gateway processing state.
    lifecycle_state:
        Engine lifecycle state string (e.g. "RUNNING").
    gateway_status:
        Operational health of the gateway.
    selected_broker_id:
        Broker chosen by the routing engine; None before routing.
    selected_broker_name:
        Human-readable broker name.
    routing_policy_id:
        Policy applied during broker selection.
    routing_decision_outcome:
        RoutingOutcome value string (e.g. "ROUTED").
    broker_capability_summary:
        Sorted tuple of broker capability names available at routing.
    gateway_session_id:
        Active session with the selected broker, if any.
    dispatch_status:
        Current dispatch lifecycle status.
    queue_status:
        Gateway dispatch queue status at snapshot time.
    retry_count:
        Number of dispatch retries attempted.
    failure_reason:
        Human-readable failure description, if applicable.
    processing_duration_ms:
        Wall-time from execution start to snapshot creation.
    gateway_statistics:
        Serialized gateway statistics at snapshot time.
    gateway_metadata:
        Arbitrary key-value metadata about the gateway context.
    audit_metadata:
        Provenance and traceability metadata.
    framework_version:
        IIOS framework version that produced this snapshot.
    created_at:
        Unix timestamp when this snapshot was created.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    snapshot_id:      str
    snapshot_version: int

    # ── Correlation IDs ───────────────────────────────────────────────────────
    gateway_id:   str
    execution_id: str
    order_id:     str
    position_id:  Optional[str]
    portfolio_id: str
    workflow_id:  Optional[str]
    decision_id:  Optional[str]
    strategy_id:  str

    # ── Gateway state ─────────────────────────────────────────────────────────
    gateway_state:    GatewayState
    lifecycle_state:  str            # EngineState value string
    gateway_status:   GatewayStatus

    # ── Routing ───────────────────────────────────────────────────────────────
    selected_broker_id:       Optional[str]
    selected_broker_name:     Optional[str]
    routing_policy_id:        Optional[str]
    routing_decision_outcome: Optional[str]

    # ── Broker capability summary ─────────────────────────────────────────────
    broker_capability_summary: Tuple[str, ...]

    # ── Session / queue ───────────────────────────────────────────────────────
    gateway_session_id: Optional[str]
    dispatch_status:    DispatchStatus
    queue_status:       QueueStatus
    retry_count:        int
    failure_reason:     Optional[str]

    # ── Performance ───────────────────────────────────────────────────────────
    processing_duration_ms: float

    # ── Serialised state ──────────────────────────────────────────────────────
    gateway_statistics: Dict[str, Any]  = field(default_factory=dict, compare=False)
    gateway_metadata:   Dict[str, Any]  = field(default_factory=dict, compare=False)
    audit_metadata:     Dict[str, Any]  = field(default_factory=dict, compare=False)

    # ── Framework ─────────────────────────────────────────────────────────────
    framework_version: str  = VERSION
    created_at:        float = field(default_factory=time.time)

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def is_terminal(self) -> bool:
        """True when the gateway has reached COMPLETED or FAILED."""
        return self.gateway_state in TERMINAL_GATEWAY_STATES

    @property
    def is_active(self) -> bool:
        """True when the gateway is still processing."""
        return self.gateway_state in ACTIVE_GATEWAY_STATES

    @property
    def is_completed(self) -> bool:
        return self.gateway_state == GatewayState.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self.gateway_state == GatewayState.FAILED

    @property
    def is_routed(self) -> bool:
        """True when a broker has been selected."""
        return self.selected_broker_id is not None

    @property
    def is_dispatched(self) -> bool:
        return self.dispatch_status in SUCCESSFUL_DISPATCH_STATUSES

    @property
    def has_failure(self) -> bool:
        return bool(self.failure_reason)

    @property
    def has_retried(self) -> bool:
        return self.retry_count > 0

    @property
    def is_healthy(self) -> bool:
        return self.gateway_status == GatewayStatus.HEALTHY

    @property
    def estimated_size_bytes(self) -> int:
        """Rough estimate of serialised size in bytes."""
        try:
            return len(json.dumps(self.to_dict()).encode("utf-8"))
        except Exception:
            return 0

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":              self.snapshot_id,
            "snapshot_version":         self.snapshot_version,
            "gateway_id":               self.gateway_id,
            "execution_id":             self.execution_id,
            "order_id":                 self.order_id,
            "position_id":              self.position_id,
            "portfolio_id":             self.portfolio_id,
            "workflow_id":              self.workflow_id,
            "decision_id":              self.decision_id,
            "strategy_id":              self.strategy_id,
            "gateway_state":            self.gateway_state.value,
            "lifecycle_state":          self.lifecycle_state,
            "gateway_status":           self.gateway_status.value,
            "selected_broker_id":       self.selected_broker_id,
            "selected_broker_name":     self.selected_broker_name,
            "routing_policy_id":        self.routing_policy_id,
            "routing_decision_outcome": self.routing_decision_outcome,
            "broker_capability_summary": list(self.broker_capability_summary),
            "gateway_session_id":       self.gateway_session_id,
            "dispatch_status":          self.dispatch_status.value,
            "queue_status":             self.queue_status.value,
            "retry_count":              self.retry_count,
            "failure_reason":           self.failure_reason,
            "processing_duration_ms":   self.processing_duration_ms,
            "gateway_statistics":       dict(self.gateway_statistics),
            "gateway_metadata":         dict(self.gateway_metadata),
            "audit_metadata":           dict(self.audit_metadata),
            "framework_version":        self.framework_version,
            "created_at":               self.created_at,
            # Derived flags for convenience
            "is_terminal":              self.is_terminal,
            "is_routed":                self.is_routed,
            "is_dispatched":            self.is_dispatched,
        }

    def __repr__(self) -> str:
        return (
            f"ExecutionGatewaySnapshot("
            f"id={self.snapshot_id!r}, "
            f"v={self.snapshot_version}, "
            f"state={self.gateway_state.value!r}, "
            f"broker={self.selected_broker_id!r}"
            f")"
        )
