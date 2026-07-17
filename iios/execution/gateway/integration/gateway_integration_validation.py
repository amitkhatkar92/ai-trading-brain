"""iios/execution/gateway/integration/gateway_integration_validation.py
==================================================
GatewayIntegrationValidationResult and GatewayIntegrationValidator —
stateless validation for the integration layer.

C6 Execution Intelligence — Phase 5, Module 6
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Tuple

from .exceptions import IntegrationRequestValidationError

if TYPE_CHECKING:
    from .gateway_component_registry import GatewayComponentRegistry
    from .gateway_integration_request import GatewayIntegrationRequest
    from .gateway_integration_context import GatewayIntegrationContext


@dataclass(frozen=True)
class GatewayIntegrationValidationResult:
    """Immutable validation outcome."""

    is_valid:  bool
    errors:    Tuple[str, ...]
    warnings:  Tuple[str, ...]

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def to_dict(self):
        return {
            "is_valid":    self.is_valid,
            "errors":      list(self.errors),
            "warnings":    list(self.warnings),
            "has_warnings": self.has_warnings,
        }


class GatewayIntegrationValidator:
    """
    Stateless validator for integration requests and contexts.

    All methods are pure (no side effects).  The caller is responsible
    for acting on the result.
    """

    def validate_request(
        self, request: "GatewayIntegrationRequest"
    ) -> GatewayIntegrationValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []
        self._check_request_identity(request, errors)
        self._check_context(request.context, errors, warnings)
        return GatewayIntegrationValidationResult(
            is_valid=len(errors) == 0,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def validate_context(
        self, context: "GatewayIntegrationContext"
    ) -> GatewayIntegrationValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []
        self._check_context(context, errors, warnings)
        return GatewayIntegrationValidationResult(
            is_valid=len(errors) == 0,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def validate_component_availability(
        self, registry: "GatewayComponentRegistry"
    ) -> GatewayIntegrationValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []
        self._check_components(registry, errors, warnings)
        return GatewayIntegrationValidationResult(
            is_valid=len(errors) == 0,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def raise_if_invalid(
        self,
        result: GatewayIntegrationValidationResult,
        context: str = "",
    ) -> None:
        if not result.is_valid:
            msg = "Integration validation failed."
            if context:
                msg = f"{context}: {msg}"
            raise IntegrationRequestValidationError(msg, errors=result.errors)

    # ── Internal checks ───────────────────────────────────────────────────────

    def _check_request_identity(self, request, errors: List[str]) -> None:
        if not request.request_id:
            errors.append("request_id is required.")
        if not request.integration_id:
            errors.append("integration_id is required.")

    def _check_context(self, ctx, errors: List[str], warnings: List[str]) -> None:
        for field_name in ("execution_id", "order_id", "portfolio_id", "strategy_id"):
            if not getattr(ctx, field_name, ""):
                errors.append(f"context.{field_name} is required.")

        if ctx.quantity < 0:
            errors.append("context.quantity must be >= 0.")
        if ctx.price < 0:
            errors.append("context.price must be >= 0.")

        if not ctx.symbol:
            warnings.append("context.symbol is empty — routing may be impaired.")
        if ctx.quantity == 0:
            warnings.append("context.quantity is zero.")
        if ctx.side.upper() not in ("BUY", "SELL"):
            warnings.append(f"context.side '{ctx.side}' is not BUY or SELL.")

    def _check_components(self, registry, errors: List[str], warnings: List[str]) -> None:
        try:
            if registry.lifecycle is None:
                errors.append("Lifecycle component is not registered.")
        except Exception:
            errors.append("Lifecycle component is not accessible.")

        try:
            if registry.engine is None:
                errors.append("Engine component is not registered.")
        except Exception:
            errors.append("Engine component is not accessible.")

        try:
            if registry.routing_engine is None:
                errors.append("RoutingEngine component is not registered.")
        except Exception:
            errors.append("RoutingEngine component is not accessible.")

        try:
            if registry.broker_manager is None:
                errors.append("BrokerManager component is not registered.")
        except Exception:
            errors.append("BrokerManager component is not accessible.")

        try:
            if registry.snapshot_store is None:
                errors.append("SnapshotStore component is not registered.")
        except Exception:
            errors.append("SnapshotStore component is not accessible.")
