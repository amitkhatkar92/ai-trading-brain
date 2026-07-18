"""iios/execution/monitoring/integration/monitoring_integration_validation.py
==================================================
IntegrationValidator — stateless validator for integration contexts
and requests.

C6 Execution Intelligence — Phase 6, Module 6
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class IntegrationValidationResult:
    """
    Mutable validation result accumulator.

    Fields
    ------
    is_valid:   True if no errors have been recorded.
    errors:     List of error messages.
    warnings:   List of warning messages (non-blocking).
    """

    is_valid:  bool       = True
    errors:    List[str]  = field(default_factory=list)
    warnings:  List[str]  = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors":   list(self.errors),
            "warnings": list(self.warnings),
        }


class IntegrationValidator:
    """
    Stateless validator for integration contexts and requests.

    All methods return an ``IntegrationValidationResult`` and never raise.
    """

    # ── Context validation ────────────────────────────────────────────────────

    def validate_context(self, context: Any) -> IntegrationValidationResult:
        """Validate a ``MonitoringIntegrationContext``."""
        result = IntegrationValidationResult()

        if not getattr(context, "session_id", ""):
            result.add_error("context.session_id must not be empty")

        if not getattr(context, "portfolio_id", ""):
            result.add_error("context.portfolio_id must not be empty")

        return result

    # ── Request validation ────────────────────────────────────────────────────

    def validate_request(self, request: Any) -> IntegrationValidationResult:
        """Validate a ``MonitoringIntegrationRequest``."""
        result = IntegrationValidationResult()

        if not getattr(request, "request_id", ""):
            result.add_error("request.request_id must not be empty")

        if not getattr(request, "session_id", ""):
            result.add_error("request.session_id must not be empty")

        if not getattr(request, "portfolio_id", ""):
            result.add_error("request.portfolio_id must not be empty")

        ctx = getattr(request, "context", None)
        if ctx is not None:
            ctx_result = self.validate_context(ctx)
            if not ctx_result.is_valid:
                for e in ctx_result.errors:
                    result.add_error(f"context: {e}")

        # Warn if no metrics provided (empty request is valid but unusual)
        metrics = getattr(request, "metrics", {})
        if not metrics:
            result.add_warning("request carries no pre-computed metrics")

        return result

    # ── Snapshot validation ───────────────────────────────────────────────────

    def validate_snapshot(self, snapshot: Any) -> IntegrationValidationResult:
        """Validate a ``MonitoringIntegrationSnapshot``."""
        result = IntegrationValidationResult()

        if not getattr(snapshot, "snapshot_id", ""):
            result.add_error("snapshot.snapshot_id must not be empty")

        if not getattr(snapshot, "session_id", ""):
            result.add_error("snapshot.session_id must not be empty")

        if not getattr(snapshot, "portfolio_id", ""):
            result.add_error("snapshot.portfolio_id must not be empty")

        version = getattr(snapshot, "snapshot_version", 0)
        if version < 1:
            result.add_error("snapshot.snapshot_version must be >= 1")

        return result

    # ── Subsystem readiness ───────────────────────────────────────────────────

    def validate_subsystem_readiness(
        self,
        lifecycle_running: bool,
        metrics_running:   bool,
        alerts_running:    bool,
    ) -> IntegrationValidationResult:
        """Verify all sub-components are running."""
        result = IntegrationValidationResult()

        if not lifecycle_running:
            result.add_error("MonitoringLifecycle is not running")
        if not metrics_running:
            result.add_error("MetricsEngine is not running")
        if not alerts_running:
            result.add_error("AlertManager is not running")

        return result
