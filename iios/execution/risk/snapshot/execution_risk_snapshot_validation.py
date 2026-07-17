"""iios/execution/risk/snapshot/execution_risk_snapshot_validation.py
==================================================
SnapshotValidator — stateless validator for ExecutionRiskSnapshot.

C6 Execution Intelligence — Phase 4, Module 5
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Tuple

from .constants import (
    SNAPSHOT_VERSION,
    VALID_LIFECYCLE_STATES_FOR_SNAPSHOT,
    SnapshotStatus,
)
from .exceptions import SnapshotValidationError
from .execution_risk_snapshot import ExecutionRiskSnapshot


@dataclass(frozen=True)
class SnapshotValidationResult:
    """Result of a validation pass."""
    is_valid:     bool
    errors:       Tuple[str, ...]
    warnings:     Tuple[str, ...]
    validated_at: float = field(default_factory=time.time)

    def __bool__(self) -> bool:
        return self.is_valid


class SnapshotValidator:
    """
    Stateless validator for ExecutionRiskSnapshot.

    All ``validate_*`` methods return ``SnapshotValidationResult`` —
    they do NOT raise.  Use ``raise_if_invalid()`` to convert a failed
    result to a ``SnapshotValidationError``.
    """

    @staticmethod
    def validate_snapshot(snapshot: ExecutionRiskSnapshot) -> SnapshotValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []

        if not isinstance(snapshot, ExecutionRiskSnapshot):
            return SnapshotValidationResult(
                False, ("snapshot must be an ExecutionRiskSnapshot instance",), ()
            )

        # ── Identifier consistency ────────────────────────────────────────────
        if not snapshot.snapshot_id:
            errors.append("snapshot_id is empty")
        if not snapshot.risk_id:
            errors.append("risk_id is empty")
        if not snapshot.execution_id:
            warnings.append("execution_id is empty")

        # ── Version compatibility ─────────────────────────────────────────────
        if not snapshot.snapshot_version:
            errors.append("snapshot_version is empty")
        elif snapshot.snapshot_version != SNAPSHOT_VERSION:
            warnings.append(
                f"snapshot_version '{snapshot.snapshot_version}' "
                f"differs from current '{SNAPSHOT_VERSION}'"
            )

        # ── Lifecycle consistency ─────────────────────────────────────────────
        if snapshot.risk_state not in VALID_LIFECYCLE_STATES_FOR_SNAPSHOT:
            errors.append(
                f"risk_state '{snapshot.risk_state}' is not a terminal outcome state. "
                f"Expected one of: {sorted(VALID_LIFECYCLE_STATES_FOR_SNAPSHOT)}"
            )

        # ── Control consistency ───────────────────────────────────────────────
        if not snapshot.control_action:
            errors.append("control_action is empty")
        if not snapshot.final_action:
            errors.append("final_action is empty")
        if not snapshot.policy_used:
            warnings.append("policy_used is empty")

        # Override consistency
        if snapshot.override_status and snapshot.override_metadata is None:
            errors.append("override_status=True but override_metadata is absent")
        if snapshot.override_status and not snapshot.was_overridden:
            errors.append("override_status=True but was_overridden property is False")

        # Emergency consistency
        if snapshot.emergency_status and snapshot.final_action != "EMERGENCY_STOP":
            warnings.append(
                "emergency_status=True but final_action is not EMERGENCY_STOP"
            )

        # ── Snapshot completeness ─────────────────────────────────────────────
        if snapshot.snapshot_timestamp <= 0:
            errors.append("snapshot_timestamp must be a positive Unix timestamp")
        if snapshot.evaluation_duration_ms < 0:
            errors.append("evaluation_duration_ms must be non-negative")

        # ── Rule consistency ──────────────────────────────────────────────────
        all_blocks = {r.rule_id for r in snapshot.blocks}
        all_triggered = {r.rule_id for r in snapshot.triggered_rules}
        for block in snapshot.blocks:
            if block.rule_id not in all_triggered:
                warnings.append(
                    f"block rule '{block.rule_id}' not in triggered_rules"
                )

        # ── Metadata consistency ──────────────────────────────────────────────
        if not snapshot.audit_metadata:
            errors.append("audit_metadata is missing")
        if not snapshot.risk_metadata:
            errors.append("risk_metadata is missing")

        # ── Timestamp consistency ─────────────────────────────────────────────
        if (snapshot.audit_metadata
                and snapshot.audit_metadata.created_at > time.time() + 60):
            warnings.append("audit_metadata.created_at is in the future")

        return SnapshotValidationResult(
            is_valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    @staticmethod
    def validate_completeness(snapshot: ExecutionRiskSnapshot) -> SnapshotValidationResult:
        """Strict completeness check — all meaningful fields must be non-empty."""
        errors:   List[str] = []
        warnings: List[str] = []

        required_non_empty = (
            ("snapshot_id",      snapshot.snapshot_id),
            ("risk_id",          snapshot.risk_id),
            ("risk_category",    snapshot.risk_category),
            ("risk_state",       snapshot.risk_state),
            ("control_action",   snapshot.control_action),
            ("final_action",     snapshot.final_action),
            ("framework_version", snapshot.framework_version),
        )
        for name, value in required_non_empty:
            if not value:
                errors.append(f"'{name}' is required but empty")

        return SnapshotValidationResult(
            is_valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    @staticmethod
    def raise_if_invalid(
        result:  SnapshotValidationResult,
        context: str = "",
        *,
        snapshot_id: str = "",
    ) -> None:
        if not result.is_valid:
            msg = "; ".join(result.errors)
            if context:
                msg = f"[{context}] {msg}"
            raise SnapshotValidationError(msg, snapshot_id=snapshot_id)
