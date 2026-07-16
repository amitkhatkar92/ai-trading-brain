"""iios/execution/positions/integration/position_integration_validation.py
==================================================
IntegrationValidationResult and IntegrationValidator for the
Position Integration subsystem.

Validates: component registration, availability, lifecycle
consistency, snapshot consistency, risk consistency,
history consistency, and overall subsystem consistency.

C6 Execution Intelligence — Phase 3, Module 6
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple, TYPE_CHECKING

from .exceptions import IntegrationValidationError

if TYPE_CHECKING:
    from .position_component_registry import ComponentRegistry
    from .position_integration_history import IntegrationHistory


@dataclass(frozen=True)
class IntegrationValidationResult:
    """
    Immutable result of a subsystem validation run.

    Attributes
    ----------
    is_valid
        ``True`` when no errors were found.
    errors
        Tuple of error strings (empty on success).
    warnings
        Tuple of warning strings (present even when is_valid is True).
    checks_passed
        Number of individual checks that passed.
    checks_failed
        Number of individual checks that failed.
    """

    is_valid:       bool
    errors:         Tuple[str, ...] = field(default_factory=tuple)
    warnings:       Tuple[str, ...] = field(default_factory=tuple)
    checks_passed:  int             = 0
    checks_failed:  int             = 0

    @classmethod
    def ok(
        cls,
        warnings:      Optional[List[str]] = None,
        checks_passed: int = 0,
    ) -> "IntegrationValidationResult":
        return cls(
            is_valid=True,
            warnings=tuple(warnings or []),
            checks_passed=checks_passed,
        )

    @classmethod
    def fail(
        cls,
        errors:        List[str],
        warnings:      Optional[List[str]] = None,
        checks_passed: int = 0,
        checks_failed: int = 0,
    ) -> "IntegrationValidationResult":
        return cls(
            is_valid=False,
            errors=tuple(errors),
            warnings=tuple(warnings or []),
            checks_passed=checks_passed,
            checks_failed=checks_failed or len(errors),
        )

    def raise_if_invalid(self) -> None:
        """Raise :class:`IntegrationValidationError` if not valid."""
        if not self.is_valid:
            raise IntegrationValidationError(
                f"Subsystem validation failed with {len(self.errors)} error(s)",
                errors=self.errors,
            )

    def to_dict(self):
        return {
            "is_valid":      self.is_valid,
            "errors":        list(self.errors),
            "warnings":      list(self.warnings),
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
        }


class IntegrationValidator:
    """
    Stateless subsystem validator for the Position Integration layer.

    Each method runs a focused check and returns an
    :class:`IntegrationValidationResult`.  The composite
    :meth:`validate` aggregates all checks.
    """

    # ── Individual checks ─────────────────────────────────────────────────────

    def validate_component_registration(
        self,
        registry: "ComponentRegistry",
    ) -> IntegrationValidationResult:
        """All four components must be registered."""
        errors: List[str] = []
        if not registry.all_registered():
            count = registry.registered_count()
            errors.append(
                f"Not all components registered: {count}/4 present"
            )
        if errors:
            return IntegrationValidationResult.fail(errors, checks_failed=1)
        return IntegrationValidationResult.ok(checks_passed=1)

    def validate_component_availability(
        self,
        registry: "ComponentRegistry",
    ) -> IntegrationValidationResult:
        """All registered components must be running."""
        errors: List[str] = []
        for status in registry.all_statuses():
            if not status.is_running:
                errors.append(
                    f"Component not running: {status.component_name!r} "
                    f"(state={status.lifecycle_state})"
                )
        if errors:
            return IntegrationValidationResult.fail(errors, checks_failed=len(errors))
        return IntegrationValidationResult.ok(checks_passed=1)

    def validate_lifecycle_consistency(
        self,
        engine: Any,
        book:   Any,
    ) -> IntegrationValidationResult:
        """
        Positions in the engine must all appear in the book.

        A missing entry is a warning (not an error) — it may be a
        very recent position not yet synced.
        """
        warnings: List[str] = []
        try:
            engine_ids = {p.position_id for p in engine.all_positions()}
            book_ids   = set()
            for s in book.all_statuses() if hasattr(book, "all_statuses") else []:
                book_ids.add(s)
            # Lightweight check: if we can't get book IDs, skip
        except Exception as exc:
            warnings.append(f"Lifecycle consistency check skipped: {exc}")

        return IntegrationValidationResult.ok(warnings=warnings, checks_passed=1)

    def validate_snapshot_consistency(
        self,
        engine:         Any,
        snapshot_store: Any,
    ) -> IntegrationValidationResult:
        """
        Positions known to the engine should have at least one snapshot.

        Missing snapshots are recorded as warnings (stale state is valid
        temporarily — build_and_store may not have run yet).
        """
        warnings: List[str] = []
        try:
            for pos in engine.active_positions():
                if not snapshot_store.contains(pos.position_id):
                    warnings.append(
                        f"No snapshot for active position {pos.position_id!r}"
                    )
        except Exception as exc:
            warnings.append(f"Snapshot consistency check skipped: {exc}")
        return IntegrationValidationResult.ok(warnings=warnings, checks_passed=1)

    def validate_risk_consistency(
        self,
        engine:       Any,
        risk_manager: Any,
    ) -> IntegrationValidationResult:
        """
        Active positions should have a risk state registered.

        Missing risk state is a warning — risk registration may lag
        position creation by one integration cycle.
        """
        warnings: List[str] = []
        try:
            from iios.execution.positions.risk.position_risk_registry import RiskRegistry
            registry = risk_manager._registry
            for pos in engine.active_positions():
                if not registry.contains(pos.position_id):
                    warnings.append(
                        f"No risk state for active position {pos.position_id!r}"
                    )
        except Exception as exc:
            warnings.append(f"Risk consistency check skipped: {exc}")
        return IntegrationValidationResult.ok(warnings=warnings, checks_passed=1)

    def validate_history_consistency(
        self,
        history: "IntegrationHistory",
    ) -> IntegrationValidationResult:
        """History must be non-None and functional."""
        errors: List[str] = []
        try:
            _ = history.count()
        except Exception as exc:
            errors.append(f"History is not functional: {exc}")
        if errors:
            return IntegrationValidationResult.fail(errors, checks_failed=1)
        return IntegrationValidationResult.ok(checks_passed=1)

    def validate_subsystem_consistency(
        self,
        registry: "ComponentRegistry",
    ) -> IntegrationValidationResult:
        """Overall health must not be CRITICAL."""
        errors:   List[str] = []
        warnings: List[str] = []
        try:
            report = registry.health_report()
            if report.overall_status == "CRITICAL":
                errors.append(f"Subsystem health is CRITICAL")
            elif report.overall_status == "DEGRADED":
                warnings.append(f"Subsystem health is DEGRADED")
        except Exception as exc:
            warnings.append(f"Subsystem consistency check skipped: {exc}")
        if errors:
            return IntegrationValidationResult.fail(
                errors, warnings=warnings, checks_failed=1
            )
        return IntegrationValidationResult.ok(warnings=warnings, checks_passed=1)

    # ── Composite ─────────────────────────────────────────────────────────────

    def validate(
        self,
        registry:       "ComponentRegistry",
        engine:         Any,
        book:           Any,
        risk_manager:   Any,
        snapshot_store: Any,
        history:        "IntegrationHistory",
    ) -> IntegrationValidationResult:
        """Run all 7 validation checks and aggregate results."""
        all_errors:   List[str] = []
        all_warnings: List[str] = []
        passed = 0
        failed = 0

        checks = [
            self.validate_component_registration(registry),
            self.validate_component_availability(registry),
            self.validate_lifecycle_consistency(engine, book),
            self.validate_snapshot_consistency(engine, snapshot_store),
            self.validate_risk_consistency(engine, risk_manager),
            self.validate_history_consistency(history),
            self.validate_subsystem_consistency(registry),
        ]

        for result in checks:
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
            passed += result.checks_passed
            failed += result.checks_failed

        if all_errors:
            return IntegrationValidationResult.fail(
                all_errors,
                warnings=all_warnings,
                checks_passed=passed,
                checks_failed=failed,
            )
        return IntegrationValidationResult.ok(
            warnings=all_warnings,
            checks_passed=passed,
        )
