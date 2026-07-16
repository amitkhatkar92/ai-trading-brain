"""iios/execution/oms/integration/oms_integration_validation.py
==================================================
OMSValidator — validates cross-component OMS state and consistency.

C6 Execution Intelligence — Phase 2, Module 6
"""
from __future__ import annotations

import dataclasses
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.integration.constants import (
    REQUIRED_COMPONENTS,
    ComponentType,
    ValidationCode,
)
from iios.execution.oms.integration.exceptions import OMSValidationError


@dataclass(frozen=True)
class ValidationReport:
    """
    Immutable result of an OMS validation run.
    """
    report_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    is_valid:     bool  = True
    errors:       tuple[str, ...] = field(default_factory=tuple)
    warnings:     tuple[str, ...] = field(default_factory=tuple)
    codes:        tuple[ValidationCode, ...] = field(default_factory=tuple)
    validated_at: float = field(default_factory=time.time)
    elapsed_ms:   float = 0.0

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id":     self.report_id,
            "is_valid":      self.is_valid,
            "errors":        list(self.errors),
            "warnings":      list(self.warnings),
            "codes":         [c.value for c in self.codes],
            "error_count":   self.error_count,
            "warning_count": self.warning_count,
            "validated_at":  self.validated_at,
            "elapsed_ms":    round(self.elapsed_ms, 3),
        }


class OMSValidator:
    """
    Stateless validator for cross-component OMS consistency.

    All ``validate_*`` methods collect errors and return a
    ``ValidationReport`` rather than raising on first error.
    The public ``validate()`` method runs all checks.
    """

    def validate(self, registry: Any) -> ValidationReport:
        """
        Run all validation checks against the given component registry.

        Returns a ValidationReport (never raises unless the registry
        itself raises an unexpected exception).
        """
        t0     = time.time()
        errors:   list[str]           = []
        warnings: list[str]           = []
        codes:    list[ValidationCode] = []

        self._check_component_registration(registry, errors, warnings, codes)
        self._check_component_availability(registry, errors, warnings, codes)
        self._check_state_consistency(registry, errors, warnings, codes)

        is_valid  = len(errors) == 0
        elapsed   = (time.time() - t0) * 1000.0
        return ValidationReport(
            is_valid     = is_valid,
            errors       = tuple(errors),
            warnings     = tuple(warnings),
            codes        = tuple(codes),
            elapsed_ms   = elapsed,
        )

    def validate_snapshot(self, snapshot: Any) -> ValidationReport:
        """Validate an OMSSnapshot for internal consistency."""
        t0     = time.time()
        errors:   list[str]           = []
        warnings: list[str]           = []
        codes:    list[ValidationCode] = []

        try:
            # All five component snapshots must be present
            for attr in (
                "manager_snapshot", "book_snapshot",
                "router_snapshot", "queue_snapshot", "persistence_snapshot",
            ):
                if getattr(snapshot, attr, None) is None:
                    errors.append(f"Snapshot missing: {attr}")
                    codes.append(ValidationCode.SNAPSHOT_INCONSISTENCY)

            # Statistics must be present
            if snapshot.statistics is None:
                errors.append("Snapshot missing statistics")
                codes.append(ValidationCode.SNAPSHOT_INCONSISTENCY)

            # Component health count must equal required component count
            if len(snapshot.component_health) != len(REQUIRED_COMPONENTS):
                warnings.append(
                    f"Expected {len(REQUIRED_COMPONENTS)} component health entries, "
                    f"got {len(snapshot.component_health)}"
                )

        except Exception as exc:  # noqa: BLE001
            errors.append(f"Snapshot validation error: {exc}")
            codes.append(ValidationCode.SNAPSHOT_INCONSISTENCY)

        elapsed = (time.time() - t0) * 1000.0
        return ValidationReport(
            is_valid   = len(errors) == 0,
            errors     = tuple(errors),
            warnings   = tuple(warnings),
            codes      = tuple(codes),
            elapsed_ms = elapsed,
        )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_component_registration(
        self,
        registry: Any,
        errors:   list[str],
        warnings: list[str],
        codes:    list[ValidationCode],
    ) -> None:
        for ct in REQUIRED_COMPONENTS:
            if registry.get(ct) is None:
                errors.append(
                    f"{ValidationCode.COMPONENT_MISSING.value}: "
                    f"Component '{ct.value}' is not registered"
                )
                codes.append(ValidationCode.COMPONENT_MISSING)

    def _check_component_availability(
        self,
        registry: Any,
        errors:   list[str],
        warnings: list[str],
        codes:    list[ValidationCode],
    ) -> None:
        for ct in REQUIRED_COMPONENTS:
            component = registry.get(ct)
            if component is None:
                continue   # already caught in registration check
            try:
                from iios.investment.workflow.engine_lifecycle import EngineState
                state = component.lifecycle_state()
                if state != EngineState.RUNNING:
                    errors.append(
                        f"{ValidationCode.COMPONENT_NOT_RUNNING.value}: "
                        f"Component '{ct.value}' is in state '{state.value}'"
                    )
                    codes.append(ValidationCode.COMPONENT_NOT_RUNNING)
            except Exception:  # noqa: BLE001
                warnings.append(
                    f"Could not check lifecycle state for '{ct.value}'"
                )

    def _check_state_consistency(
        self,
        registry: Any,
        errors:   list[str],
        warnings: list[str],
        codes:    list[ValidationCode],
    ) -> None:
        # All components must be in a consistent running state
        running_count = 0
        for ct in REQUIRED_COMPONENTS:
            component = registry.get(ct)
            if component is None:
                continue
            try:
                from iios.investment.workflow.engine_lifecycle import EngineState
                if component.lifecycle_state() == EngineState.RUNNING:
                    running_count += 1
            except Exception:  # noqa: BLE001
                pass

        total = len(REQUIRED_COMPONENTS)
        if 0 < running_count < total:
            warnings.append(
                f"{ValidationCode.STATE_INCONSISTENCY.value}: "
                f"Only {running_count}/{total} components are running"
            )
            codes.append(ValidationCode.STATE_INCONSISTENCY)
