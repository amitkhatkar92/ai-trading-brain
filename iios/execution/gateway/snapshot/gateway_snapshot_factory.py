"""iios/execution/gateway/snapshot/gateway_snapshot_factory.py
==================================================
GatewaySnapshotFactory — all-static factory helpers for
Execution Gateway Snapshot objects.

C6 Execution Intelligence — Phase 5, Module 5
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from .constants import (
    DEFAULT_MAX_CACHE_SIZE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SNAPSHOTS,
    DispatchStatus,
    GatewayState,
    GatewayStatus,
    QueueStatus,
)
from .execution_gateway_snapshot import ExecutionGatewaySnapshot
from .gateway_snapshot_builder import GatewaySnapshotBuilder
from .gateway_snapshot_bundle import GatewaySnapshotBundle, make_bundle_from_snapshots
from .gateway_snapshot_metadata import GatewaySnapshotMetadata, make_audit_metadata
from .gateway_snapshot_store import GatewaySnapshotStore


class GatewaySnapshotFactory:
    """All-static factory for Gateway Snapshot objects."""

    # ── Snapshot ──────────────────────────────────────────────────────────────

    @staticmethod
    def create_snapshot(
        *,
        gateway_id:    str,
        execution_id:  str,
        order_id:      str,
        portfolio_id:  str,
        strategy_id:   str,
        gateway_state: GatewayState    = GatewayState.READY,
        lifecycle_state: str           = "RUNNING",
        gateway_status: GatewayStatus  = GatewayStatus.HEALTHY,
        dispatch_status: DispatchStatus = DispatchStatus.PENDING,
        queue_status:   QueueStatus    = QueueStatus.EMPTY,
        position_id:    Optional[str]  = None,
        workflow_id:    Optional[str]  = None,
        decision_id:    Optional[str]  = None,
        selected_broker_id:       Optional[str] = None,
        selected_broker_name:     Optional[str] = None,
        routing_policy_id:        Optional[str] = None,
        routing_decision_outcome: Optional[str] = None,
        gateway_session_id: Optional[str]       = None,
        retry_count:    int   = 0,
        failure_reason: Optional[str]  = None,
        processing_duration_ms: float  = 0.0,
        broker_capability_summary: Tuple[str, ...] = (),
        gateway_statistics: Optional[Dict[str, Any]] = None,
        gateway_metadata:   Optional[Dict[str, Any]] = None,
        audit_metadata:     Optional[Dict[str, Any]] = None,
        snapshot_version:   int = 1,
    ) -> ExecutionGatewaySnapshot:
        """Create a fully configured ExecutionGatewaySnapshot."""
        builder = GatewaySnapshotBuilder()
        (
            builder
            .set_identifiers(
                gateway_id=gateway_id,
                execution_id=execution_id,
                order_id=order_id,
                portfolio_id=portfolio_id,
                strategy_id=strategy_id,
                position_id=position_id,
                workflow_id=workflow_id,
                decision_id=decision_id,
            )
            .set_snapshot_version(snapshot_version)
            .set_gateway_state(
                gateway_state=gateway_state,
                lifecycle_state=lifecycle_state,
                gateway_status=gateway_status,
            )
            .set_routing(
                selected_broker_id=selected_broker_id,
                selected_broker_name=selected_broker_name,
                routing_policy_id=routing_policy_id,
                routing_decision_outcome=routing_decision_outcome,
            )
            .set_broker_capabilities(broker_capability_summary)
            .set_session(gateway_session_id=gateway_session_id)
            .set_dispatch(dispatch_status=dispatch_status, queue_status=queue_status)
            .set_retry(retry_count=retry_count, failure_reason=failure_reason)
            .set_processing_duration(processing_duration_ms)
            .set_statistics(gateway_statistics or {})
            .set_metadata(
                gateway_metadata=gateway_metadata,
                audit_metadata=audit_metadata,
            )
        )
        return builder.build()

    @staticmethod
    def create_snapshot_from_routing_decision(
        *,
        routing_decision: Any,     # duck-typed RoutingDecision
        gateway_id:    str,
        execution_id:  str,
        order_id:      str,
        portfolio_id:  str,
        strategy_id:   str,
        gateway_state: GatewayState   = GatewayState.ROUTING,
        lifecycle_state: str          = "RUNNING",
        gateway_status: GatewayStatus = GatewayStatus.HEALTHY,
        dispatch_status: DispatchStatus = DispatchStatus.PENDING,
        queue_status:   QueueStatus   = QueueStatus.EMPTY,
        **kwargs: Any,
    ) -> ExecutionGatewaySnapshot:
        """Create a snapshot pre-populated from a RoutingDecision."""
        builder = GatewaySnapshotBuilder()
        (
            builder
            .set_identifiers(
                gateway_id=gateway_id,
                execution_id=execution_id,
                order_id=order_id,
                portfolio_id=portfolio_id,
                strategy_id=strategy_id,
            )
            .set_gateway_state(
                gateway_state=gateway_state,
                lifecycle_state=lifecycle_state,
                gateway_status=gateway_status,
            )
            .set_routing_from_decision(routing_decision)
            .set_dispatch(dispatch_status=dispatch_status, queue_status=queue_status)
        )
        return builder.build()

    # ── Metadata ──────────────────────────────────────────────────────────────

    @staticmethod
    def create_metadata(
        snapshot_id:   str,
        *,
        source_system: str = "iios:execution:gateway",
        created_by:    str = "iios:system",
        environment:   str = "PROD",
        tags:          Optional[Tuple[str, ...]] = None,
        notes:         str = "",
    ) -> GatewaySnapshotMetadata:
        return make_audit_metadata(
            snapshot_id=snapshot_id,
            source_system=source_system,
            created_by=created_by,
            environment=environment,
            tags=tags,
            notes=notes,
        )

    # ── Bundle ────────────────────────────────────────────────────────────────

    @staticmethod
    def create_bundle(
        snapshots:   List[ExecutionGatewaySnapshot],
        bundle_name: str = "",
        *,
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> GatewaySnapshotBundle:
        return make_bundle_from_snapshots(snapshots, bundle_name, metadata=metadata)

    # ── Store ─────────────────────────────────────────────────────────────────

    @staticmethod
    def create_store(
        max_snapshots:  int = DEFAULT_MAX_SNAPSHOTS,
        max_history:    int = DEFAULT_MAX_HISTORY,
        max_cache_size: int = DEFAULT_MAX_CACHE_SIZE,
    ) -> GatewaySnapshotStore:
        return GatewaySnapshotStore(
            max_snapshots=max_snapshots,
            max_history=max_history,
            max_cache_size=max_cache_size,
        )

    # ── Builder ───────────────────────────────────────────────────────────────

    @staticmethod
    def create_builder() -> GatewaySnapshotBuilder:
        return GatewaySnapshotBuilder()
