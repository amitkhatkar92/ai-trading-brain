"""
iios/execution/recovery/integration/recovery_integration_validation.py
======================================================================
IntegrationValidationResult and IntegrationValidator.

Validates integration requests and contexts before submission.

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .recovery_integration_request import IntegrationRequest
    from .recovery_integration_context import IntegrationContext
    from .recovery_component_registry import RecoveryComponentRegistry


@dataclass
class IntegrationValidationResult:
    """Mutable accumulator of integration validation findings."""

    is_valid: bool      = True
    errors:   List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def merge(self, other: "IntegrationValidationResult") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors":   list(self.errors),
            "warnings": list(self.warnings),
        }


class IntegrationValidator:
    """Validates integration requests and component readiness."""

    # ── Request validation ────────────────────────────────────────────────────

    def validate_request(
        self, request: Optional["IntegrationRequest"]
    ) -> IntegrationValidationResult:
        r = IntegrationValidationResult()
        if request is None:
            r.add_error("request must not be None")
            return r
        if not getattr(request, "request_id", ""):
            r.add_error("request_id is required")
        if not getattr(request, "execution_session_id", ""):
            r.add_error("execution_session_id is required")
        if not getattr(request, "subsystem_id", ""):
            r.add_error("subsystem_id is required")
        if not getattr(request, "failure_type", ""):
            r.add_error("failure_type is required")
        if not getattr(request, "failure_reason", ""):
            r.add_error("failure_reason is required")
        if not getattr(request, "recovery_reason", ""):
            r.add_error("recovery_reason is required")
        return r

    # ── Context validation ────────────────────────────────────────────────────

    def validate_context(
        self, context: Optional["IntegrationContext"]
    ) -> IntegrationValidationResult:
        r = IntegrationValidationResult()
        if context is None:
            r.add_error("context must not be None")
            return r
        if not getattr(context, "execution_session_id", ""):
            r.add_error("context execution_session_id is required")
        if not getattr(context, "subsystem_id", ""):
            r.add_error("context subsystem_id is required")
        if not getattr(context, "failure_type", ""):
            r.add_warning("context failure_type is empty")
        return r

    # ── Component readiness ───────────────────────────────────────────────────

    def validate_components(
        self, components: Optional["RecoveryComponentRegistry"]
    ) -> IntegrationValidationResult:
        r = IntegrationValidationResult()
        if components is None:
            r.add_error("components registry is None")
            return r
        if not components.is_all_running():
            statuses = components.component_statuses()
            stopped = [name for name, st in statuses.items() if st != "running"]
            r.add_warning(f"Components not running: {stopped}")
        return r
