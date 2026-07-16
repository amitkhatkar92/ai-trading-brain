"""iios/execution/positions/snapshot/position_snapshot_validation.py
==================================================
SnapshotValidationResult — immutable validation outcome.
SnapshotValidator         — validates ``PositionSnapshot`` completeness
                            and internal consistency.

Validation checks
-----------------
1. Identifier consistency   — required IDs are present and non-empty
2. Lifecycle consistency    — lifecycle_state is a known PositionState value
3. Risk consistency         — risk_state is a known RiskLevel value or empty
4. PnL consistency          — PnL values parse as valid Decimals
5. Quantity consistency     — quantities parse as non-negative Decimals
6. Version compatibility    — snapshot schema version matches expected
7. Snapshot completeness    — required fields are populated

C6 Execution Intelligence — Phase 3, Module 5
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple

from .constants import VERSION, SnapshotStatus
from .exceptions import SnapshotValidationError
from .position_snapshot import PositionSnapshot


# ── Valid state/risk strings ──────────────────────────────────────────────────

_VALID_LIFECYCLE_STATES = frozenset({
    "CREATED", "OPENING", "OPEN", "PARTIALLY_CLOSED",
    "CLOSING", "CLOSED", "SUSPENDED", "RECOVERING",
    "RECOVERED", "ARCHIVED",
})

_VALID_RISK_STATES = frozenset({
    "NORMAL", "WATCH", "WARNING", "CRITICAL",
    "LIQUIDATION_PENDING", "LIQUIDATED", "RECOVERING", "RECOVERED",
    "",   # empty is allowed (no risk tracking for this position)
})


@dataclass(frozen=True)
class SnapshotValidationResult:
    """Immutable result of a snapshot validation run."""

    is_valid: bool
    errors:   Tuple[str, ...]
    warnings: Tuple[str, ...] = ()

    @classmethod
    def ok(cls, warnings: Optional[List[str]] = None) -> "SnapshotValidationResult":
        return cls(is_valid=True, errors=(), warnings=tuple(warnings or []))

    @classmethod
    def fail(
        cls,
        errors:   List[str],
        warnings: Optional[List[str]] = None,
    ) -> "SnapshotValidationResult":
        return cls(
            is_valid=False,
            errors=tuple(errors),
            warnings=tuple(warnings or []),
        )

    def raise_if_invalid(self) -> None:
        if not self.is_valid:
            raise SnapshotValidationError(
                "; ".join(self.errors),
                errors=self.errors,
            )


class SnapshotValidator:
    """
    Pure validation service for ``PositionSnapshot`` objects.
    No state. No lifecycle.
    """

    # ── Individual checks ─────────────────────────────────────────────────────

    def validate_identifier_consistency(
        self,
        snap: PositionSnapshot,
    ) -> SnapshotValidationResult:
        errors: List[str] = []
        if not snap.snapshot_id:
            errors.append("snapshot_id must not be empty")
        if not snap.position_id:
            errors.append("position_id must not be empty")
        if not snap.instrument:
            errors.append("instrument must not be empty")
        if snap.snapshot_version < 1:
            errors.append(f"snapshot_version must be >= 1, got {snap.snapshot_version}")
        return SnapshotValidationResult.fail(errors) if errors else SnapshotValidationResult.ok()

    def validate_lifecycle_consistency(
        self,
        snap: PositionSnapshot,
    ) -> SnapshotValidationResult:
        errors: List[str] = []
        if snap.lifecycle_state not in _VALID_LIFECYCLE_STATES:
            errors.append(
                f"lifecycle_state '{snap.lifecycle_state}' is not a valid PositionState"
            )
        return SnapshotValidationResult.fail(errors) if errors else SnapshotValidationResult.ok()

    def validate_risk_consistency(
        self,
        snap: PositionSnapshot,
    ) -> SnapshotValidationResult:
        errors: List[str] = []
        if snap.risk_state not in _VALID_RISK_STATES:
            errors.append(
                f"risk_state '{snap.risk_state}' is not a valid RiskLevel"
            )
        return SnapshotValidationResult.fail(errors) if errors else SnapshotValidationResult.ok()

    def validate_pnl_consistency(
        self,
        snap: PositionSnapshot,
    ) -> SnapshotValidationResult:
        errors: List[str] = []
        warnings: List[str] = []
        for field_name in ("realized_pnl", "unrealized_pnl"):
            raw = getattr(snap, field_name)
            try:
                Decimal(raw)
            except InvalidOperation:
                errors.append(f"{field_name} '{raw}' is not a valid Decimal")
        return (
            SnapshotValidationResult.fail(errors, warnings)
            if errors
            else SnapshotValidationResult.ok(warnings)
        )

    def validate_quantity_consistency(
        self,
        snap: PositionSnapshot,
    ) -> SnapshotValidationResult:
        errors: List[str] = []
        for field_name in ("current_quantity", "closed_quantity"):
            raw = getattr(snap, field_name)
            try:
                val = Decimal(raw)
                if val < Decimal("0"):
                    errors.append(f"{field_name} must be >= 0, got {raw}")
            except InvalidOperation:
                errors.append(f"{field_name} '{raw}' is not a valid Decimal")
        return SnapshotValidationResult.fail(errors) if errors else SnapshotValidationResult.ok()

    def validate_version_compatibility(
        self,
        snap: PositionSnapshot,
    ) -> SnapshotValidationResult:
        if snap.version != VERSION:
            return SnapshotValidationResult.ok(
                warnings=[
                    f"Snapshot schema version '{snap.version}' differs from "
                    f"current '{VERSION}'"
                ]
            )
        return SnapshotValidationResult.ok()

    def validate_completeness(
        self,
        snap: PositionSnapshot,
    ) -> SnapshotValidationResult:
        errors: List[str] = []
        warnings: List[str] = []
        if snap.snapshot_taken_at <= 0.0:
            errors.append("snapshot_taken_at must be a positive timestamp")
        if snap.position_created_at <= 0.0:
            warnings.append("position_created_at is zero; position may not have been seeded")
        if snap.execution_duration_s < 0.0:
            errors.append("execution_duration_s must be >= 0")
        return (
            SnapshotValidationResult.fail(errors, warnings)
            if errors
            else SnapshotValidationResult.ok(warnings)
        )

    # ── Composite check ───────────────────────────────────────────────────────

    def validate(self, snap: PositionSnapshot) -> SnapshotValidationResult:
        """Run all validation checks and aggregate results."""
        all_errors:   List[str] = []
        all_warnings: List[str] = []

        for result in (
            self.validate_identifier_consistency(snap),
            self.validate_lifecycle_consistency(snap),
            self.validate_risk_consistency(snap),
            self.validate_pnl_consistency(snap),
            self.validate_quantity_consistency(snap),
            self.validate_version_compatibility(snap),
            self.validate_completeness(snap),
        ):
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)

        if all_errors:
            return SnapshotValidationResult.fail(all_errors, all_warnings)
        return SnapshotValidationResult.ok(all_warnings)
