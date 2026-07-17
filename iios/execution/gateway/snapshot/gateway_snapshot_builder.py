"""iios/execution/gateway/snapshot/gateway_snapshot_builder.py
==================================================
GatewaySnapshotBuilder — constructs ExecutionGatewaySnapshot from
validated gateway inputs.

The builder:
  • Accepts primitives and gateway objects via setter methods.
  • Validates completeness at build() time.
  • Returns an immutable ExecutionGatewaySnapshot.
  • Performs NO routing, NO broker communication, NO business logic.
  • May be reset and reused.

C6 Execution Intelligence — Phase 5, Module 5
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from .constants import (
    VERSION,
    DispatchStatus,
    GatewayState,
    GatewayStatus,
    QueueStatus,
)
from .exceptions import SnapshotBuildError
from .execution_gateway_snapshot import ExecutionGatewaySnapshot
from .gateway_snapshot_metadata import GatewaySnapshotMetadata
from .gateway_snapshot_validation import GatewaySnapshotValidator


class GatewaySnapshotBuilder:
    """
    Fluent builder for ExecutionGatewaySnapshot objects.

    All setter methods return ``self`` for chaining.
    Call ``build()`` to produce the snapshot.
    Call ``reset()`` to reuse the same builder instance.
    """

    def __init__(
        self,
        *,
        validator: Optional[GatewaySnapshotValidator] = None,
    ) -> None:
        self._validator = validator or GatewaySnapshotValidator()
        self._reset_state()

    # ── Internal reset ────────────────────────────────────────────────────────

    def _reset_state(self) -> None:
        # Identity
        self._snapshot_version:   int   = 1

        # Correlation IDs
        self._gateway_id:    Optional[str] = None
        self._execution_id:  Optional[str] = None
        self._order_id:      Optional[str] = None
        self._position_id:   Optional[str] = None
        self._portfolio_id:  Optional[str] = None
        self._workflow_id:   Optional[str] = None
        self._decision_id:   Optional[str] = None
        self._strategy_id:   Optional[str] = None

        # Gateway state
        self._gateway_state:   GatewayState  = GatewayState.UNKNOWN
        self._lifecycle_state: str           = "UNKNOWN"
        self._gateway_status:  GatewayStatus = GatewayStatus.UNKNOWN

        # Routing
        self._selected_broker_id:       Optional[str] = None
        self._selected_broker_name:     Optional[str] = None
        self._routing_policy_id:        Optional[str] = None
        self._routing_decision_outcome: Optional[str] = None

        # Broker
        self._broker_capability_summary: Tuple[str, ...] = ()

        # Session / queue
        self._gateway_session_id: Optional[str]  = None
        self._dispatch_status:    DispatchStatus  = DispatchStatus.PENDING
        self._queue_status:       QueueStatus     = QueueStatus.EMPTY
        self._retry_count:        int             = 0
        self._failure_reason:     Optional[str]   = None

        # Performance
        self._processing_duration_ms: float = 0.0

        # Serialised state
        self._gateway_statistics: Dict[str, Any] = {}
        self._gateway_metadata:   Dict[str, Any] = {}
        self._audit_metadata:     Dict[str, Any] = {}

    # ── Setter methods ────────────────────────────────────────────────────────

    def set_identifiers(
        self,
        *,
        gateway_id:   str,
        execution_id: str,
        order_id:     str,
        portfolio_id: str,
        strategy_id:  str,
        position_id:  Optional[str] = None,
        workflow_id:  Optional[str] = None,
        decision_id:  Optional[str] = None,
    ) -> "GatewaySnapshotBuilder":
        self._gateway_id   = gateway_id
        self._execution_id = execution_id
        self._order_id     = order_id
        self._portfolio_id = portfolio_id
        self._strategy_id  = strategy_id
        self._position_id  = position_id
        self._workflow_id  = workflow_id
        self._decision_id  = decision_id
        return self

    def set_snapshot_version(self, version: int) -> "GatewaySnapshotBuilder":
        if version < 1:
            raise SnapshotBuildError("snapshot_version must be ≥ 1")
        self._snapshot_version = version
        return self

    def set_gateway_state(
        self,
        *,
        gateway_state:   GatewayState,
        lifecycle_state: str,
        gateway_status:  GatewayStatus,
    ) -> "GatewaySnapshotBuilder":
        self._gateway_state   = gateway_state
        self._lifecycle_state = lifecycle_state
        self._gateway_status  = gateway_status
        return self

    def set_routing(
        self,
        *,
        selected_broker_id:       Optional[str] = None,
        selected_broker_name:     Optional[str] = None,
        routing_policy_id:        Optional[str] = None,
        routing_decision_outcome: Optional[str] = None,
    ) -> "GatewaySnapshotBuilder":
        self._selected_broker_id       = selected_broker_id
        self._selected_broker_name     = selected_broker_name
        self._routing_policy_id        = routing_policy_id
        self._routing_decision_outcome = routing_decision_outcome
        return self

    def set_routing_from_decision(self, decision: Any) -> "GatewaySnapshotBuilder":
        """
        Extract routing info from a RoutingDecision-like object.

        Uses duck typing — no direct dependency on the Routing Framework.
        """
        self._selected_broker_id   = getattr(decision, "selected_broker_id", None)
        self._selected_broker_name = getattr(decision, "selected_broker_name", None)
        self._routing_policy_id    = getattr(decision, "policy_id", None)
        outcome = getattr(decision, "outcome", None)
        if outcome is not None:
            self._routing_decision_outcome = (
                outcome.value if hasattr(outcome, "value") else str(outcome)
            )
        return self

    def set_broker_capabilities(
        self,
        capability_names: Any,  # accepts frozenset, list, tuple, or any iterable of str
    ) -> "GatewaySnapshotBuilder":
        self._broker_capability_summary = tuple(sorted(str(c) for c in capability_names))
        return self

    def set_session(
        self,
        *,
        gateway_session_id: Optional[str] = None,
    ) -> "GatewaySnapshotBuilder":
        self._gateway_session_id = gateway_session_id
        return self

    def set_dispatch(
        self,
        *,
        dispatch_status: DispatchStatus,
        queue_status:    QueueStatus,
    ) -> "GatewaySnapshotBuilder":
        self._dispatch_status = dispatch_status
        self._queue_status    = queue_status
        return self

    def set_retry(
        self,
        *,
        retry_count:    int           = 0,
        failure_reason: Optional[str] = None,
    ) -> "GatewaySnapshotBuilder":
        if retry_count < 0:
            raise SnapshotBuildError("retry_count must be non-negative")
        self._retry_count    = retry_count
        self._failure_reason = failure_reason
        return self

    def set_processing_duration(self, ms: float) -> "GatewaySnapshotBuilder":
        self._processing_duration_ms = max(0.0, ms)
        return self

    def set_statistics(self, stats: Dict[str, Any]) -> "GatewaySnapshotBuilder":
        self._gateway_statistics = dict(stats)
        return self

    def set_gateway_metadata(self, metadata: Dict[str, Any]) -> "GatewaySnapshotBuilder":
        self._gateway_metadata = dict(metadata)
        return self

    def set_audit_metadata(
        self,
        metadata: Any,  # accepts GatewaySnapshotMetadata or dict
    ) -> "GatewaySnapshotBuilder":
        if isinstance(metadata, GatewaySnapshotMetadata):
            self._audit_metadata = metadata.to_dict()
        else:
            self._audit_metadata = dict(metadata)
        return self

    def set_metadata(
        self,
        *,
        gateway_metadata: Optional[Dict[str, Any]] = None,
        audit_metadata:   Any = None,
    ) -> "GatewaySnapshotBuilder":
        if gateway_metadata is not None:
            self.set_gateway_metadata(gateway_metadata)
        if audit_metadata is not None:
            self.set_audit_metadata(audit_metadata)
        return self

    # ── Build ─────────────────────────────────────────────────────────────────

    def build(self) -> ExecutionGatewaySnapshot:
        """
        Validate required fields and construct the snapshot.

        Raises
        ------
        SnapshotBuildError — if any required field is missing.
        SnapshotValidationError — if the constructed snapshot fails validation.
        """
        self._assert_required()

        snapshot = ExecutionGatewaySnapshot(
            snapshot_id=str(uuid.uuid4()),
            snapshot_version=self._snapshot_version,
            gateway_id=self._gateway_id,           # type: ignore[arg-type]
            execution_id=self._execution_id,        # type: ignore[arg-type]
            order_id=self._order_id,                # type: ignore[arg-type]
            position_id=self._position_id,
            portfolio_id=self._portfolio_id,        # type: ignore[arg-type]
            workflow_id=self._workflow_id,
            decision_id=self._decision_id,
            strategy_id=self._strategy_id,          # type: ignore[arg-type]
            gateway_state=self._gateway_state,
            lifecycle_state=self._lifecycle_state,
            gateway_status=self._gateway_status,
            selected_broker_id=self._selected_broker_id,
            selected_broker_name=self._selected_broker_name,
            routing_policy_id=self._routing_policy_id,
            routing_decision_outcome=self._routing_decision_outcome,
            broker_capability_summary=self._broker_capability_summary,
            gateway_session_id=self._gateway_session_id,
            dispatch_status=self._dispatch_status,
            queue_status=self._queue_status,
            retry_count=self._retry_count,
            failure_reason=self._failure_reason,
            processing_duration_ms=self._processing_duration_ms,
            gateway_statistics=dict(self._gateway_statistics),
            gateway_metadata=dict(self._gateway_metadata),
            audit_metadata=dict(self._audit_metadata),
            framework_version=VERSION,
            created_at=time.time(),
        )

        # Run structural validator (warnings are non-fatal)
        result = self._validator.validate_snapshot(snapshot)
        self._validator.raise_if_invalid(result, context="GatewaySnapshotBuilder.build")

        return snapshot

    def reset(self) -> "GatewaySnapshotBuilder":
        """Reset all fields so the builder can be reused."""
        self._reset_state()
        return self

    # ── Required-field guard ──────────────────────────────────────────────────

    def _assert_required(self) -> None:
        missing = []
        if not self._gateway_id:
            missing.append("gateway_id")
        if not self._execution_id:
            missing.append("execution_id")
        if not self._order_id:
            missing.append("order_id")
        if not self._portfolio_id:
            missing.append("portfolio_id")
        if not self._strategy_id:
            missing.append("strategy_id")
        if missing:
            raise SnapshotBuildError(
                f"Required field(s) not set: {', '.join(missing)}"
            )
