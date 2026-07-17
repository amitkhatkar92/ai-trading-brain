"""iios/execution/gateway/snapshot/gateway_snapshot_validation.py
==================================================
GatewaySnapshotValidationResult and GatewaySnapshotValidator.

Validates snapshots for completeness, consistency, and
framework compliance.  All validation is stateless.

C6 Execution Intelligence — Phase 5, Module 5
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    TERMINAL_GATEWAY_STATES,
    VERSION,
    DispatchStatus,
    GatewayState,
    GatewayStatus,
    QueueStatus,
)
from .exceptions import SnapshotValidationError
from .execution_gateway_snapshot import ExecutionGatewaySnapshot


@dataclass(frozen=True)
class GatewaySnapshotValidationResult:
    """Immutable result of a snapshot validation pass."""

    is_valid: bool
    errors:   Tuple[str, ...] = field(default_factory=tuple)
    warnings: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors":   list(self.errors),
            "warnings": list(self.warnings),
        }


class GatewaySnapshotValidator:
    """
    Stateless validator for ExecutionGatewaySnapshot objects.

    All methods return a GatewaySnapshotValidationResult.
    Use raise_if_invalid() to convert a failed result into an exception.
    """

    # ── Primary snapshot validation ────────────────────────────────────────────

    def validate_snapshot(
        self,
        snapshot: ExecutionGatewaySnapshot,
    ) -> GatewaySnapshotValidationResult:
        """Run all validation checks on a snapshot."""
        errors:   List[str] = []
        warnings: List[str] = []

        # 1. Identifier consistency
        self._check_identifiers(snapshot, errors, warnings)

        # 2. Lifecycle consistency
        self._check_lifecycle(snapshot, errors, warnings)

        # 3. Routing consistency
        self._check_routing(snapshot, errors, warnings)

        # 4. Queue consistency
        self._check_queue(snapshot, errors, warnings)

        # 5. Snapshot completeness
        self._check_completeness(snapshot, errors, warnings)

        # 6. Version compatibility
        self._check_version(snapshot, errors, warnings)

        # 7. Timestamp consistency
        self._check_timestamps(snapshot, errors, warnings)

        return GatewaySnapshotValidationResult(
            is_valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    # ── Section checks ────────────────────────────────────────────────────────

    def _check_identifiers(
        self,
        snap:     ExecutionGatewaySnapshot,
        errors:   List[str],
        warnings: List[str],
    ) -> None:
        if not snap.snapshot_id:
            errors.append("snapshot_id must not be empty")
        if snap.snapshot_version < 1:
            errors.append("snapshot_version must be ≥ 1")
        if not snap.gateway_id:
            errors.append("gateway_id must not be empty")
        if not snap.execution_id:
            errors.append("execution_id must not be empty")
        if not snap.order_id:
            errors.append("order_id must not be empty")
        if not snap.portfolio_id:
            errors.append("portfolio_id must not be empty")
        if not snap.strategy_id:
            errors.append("strategy_id must not be empty")

    def _check_lifecycle(
        self,
        snap:     ExecutionGatewaySnapshot,
        errors:   List[str],
        warnings: List[str],
    ) -> None:
        if not snap.lifecycle_state:
            errors.append("lifecycle_state must not be empty")
        if snap.gateway_state == GatewayState.UNKNOWN:
            warnings.append("gateway_state is UNKNOWN")
        if snap.gateway_status == GatewayStatus.UNKNOWN:
            warnings.append("gateway_status is UNKNOWN")

    def _check_routing(
        self,
        snap:     ExecutionGatewaySnapshot,
        errors:   List[str],
        warnings: List[str],
    ) -> None:
        # If gateway completed, should have a broker selected
        if snap.gateway_state == GatewayState.COMPLETED:
            if not snap.selected_broker_id:
                warnings.append(
                    "gateway_state is COMPLETED but selected_broker_id is not set"
                )
            if snap.dispatch_status not in (
                DispatchStatus.DISPATCHED,
                DispatchStatus.ACKNOWLEDGED,
                DispatchStatus.COMPLETED,
            ):
                warnings.append(
                    "gateway_state is COMPLETED but dispatch_status indicates "
                    f"incomplete dispatch: {snap.dispatch_status.value}"
                )

        # Routing outcome consistency
        if snap.selected_broker_id and not snap.routing_decision_outcome:
            warnings.append(
                "selected_broker_id is set but routing_decision_outcome is missing"
            )

    def _check_queue(
        self,
        snap:     ExecutionGatewaySnapshot,
        errors:   List[str],
        warnings: List[str],
    ) -> None:
        # FULL or BLOCKED queue with successful dispatch is suspicious
        if snap.queue_status in (QueueStatus.FULL, QueueStatus.BLOCKED):
            if snap.dispatch_status in (
                DispatchStatus.DISPATCHED,
                DispatchStatus.ACKNOWLEDGED,
                DispatchStatus.COMPLETED,
            ):
                warnings.append(
                    f"queue_status is {snap.queue_status.value} but "
                    f"dispatch_status shows successful dispatch"
                )

    def _check_completeness(
        self,
        snap:     ExecutionGatewaySnapshot,
        errors:   List[str],
        warnings: List[str],
    ) -> None:
        if snap.retry_count < 0:
            errors.append("retry_count must be non-negative")
        if snap.processing_duration_ms < 0:
            errors.append("processing_duration_ms must be non-negative")
        if snap.failure_reason and snap.gateway_state not in (
            GatewayState.FAILED,
            GatewayState.RECOVERING,
        ):
            warnings.append(
                "failure_reason is set but gateway_state does not indicate failure"
            )
        if snap.has_failure and snap.gateway_state not in (
            GatewayState.FAILED,
            GatewayState.RECOVERING,
        ):
            warnings.append(
                "failure_reason is set but gateway_state is not FAILED or RECOVERING"
            )

    def _check_version(
        self,
        snap:     ExecutionGatewaySnapshot,
        errors:   List[str],
        warnings: List[str],
    ) -> None:
        if not snap.framework_version:
            errors.append("framework_version must not be empty")

    def _check_timestamps(
        self,
        snap:     ExecutionGatewaySnapshot,
        errors:   List[str],
        warnings: List[str],
    ) -> None:
        if snap.created_at <= 0:
            errors.append("created_at must be a positive Unix timestamp")
        now = time.time()
        if snap.created_at > now + 60:
            warnings.append(
                "created_at is more than 60 seconds in the future"
            )

    # ── Raise helper ──────────────────────────────────────────────────────────

    def raise_if_invalid(
        self,
        result:  GatewaySnapshotValidationResult,
        context: str = "",
    ) -> None:
        """Raise SnapshotValidationError if result.is_valid is False."""
        if result.is_valid:
            return
        prefix = f"{context}: " if context else ""
        message = (
            f"{prefix}Snapshot validation failed "
            f"with {len(result.errors)} error(s)."
        )
        raise SnapshotValidationError(message, errors=result.errors)
