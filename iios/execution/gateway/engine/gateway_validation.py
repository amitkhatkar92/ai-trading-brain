"""iios/execution/gateway/engine/gateway_validation.py
==================================================
EngineGatewayValidator and EngineValidationResult — validation logic
for the Execution Gateway Engine.

Validates contexts, sessions, requests, and queue capacity.

C6 Execution Intelligence — Phase 5, Module 2
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import GatewayValidationFailedError
from .gateway_context import EngineGatewayContext
from .gateway_operation_queue import GatewayOperationQueue
from .gateway_request import EngineGatewayRequest
from .gateway_session import GatewaySession


# ── EngineValidationResult ────────────────────────────────────────────────────

@dataclass(frozen=True)
class EngineValidationResult:
    """
    Immutable result of an engine validation check.

    ``is_valid`` is True only when ``errors`` is empty.
    Warnings do not affect validity.
    """

    is_valid:     bool
    errors:       Tuple[str, ...]
    warnings:     Tuple[str, ...]
    validated_at: float

    def __bool__(self) -> bool:
        return self.is_valid

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid":     self.is_valid,
            "errors":       list(self.errors),
            "warnings":     list(self.warnings),
            "validated_at": self.validated_at,
        }


def _result(errors: List[str], warnings: List[str]) -> EngineValidationResult:
    return EngineValidationResult(
        is_valid=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        validated_at=time.time(),
    )


# ── EngineGatewayValidator ────────────────────────────────────────────────────

class EngineGatewayValidator:
    """
    Stateless validator for engine-level gateway objects.

    All methods return ``EngineValidationResult``; none raise exceptions
    directly.  Use ``raise_if_invalid()`` to turn a failed result into
    an exception.
    """

    # ── Context validation ────────────────────────────────────────────────────

    def validate_context(
        self,
        ctx: EngineGatewayContext,
    ) -> EngineValidationResult:
        """Validate required identifiers and basic attribute constraints."""
        errors:   List[str] = []
        warnings: List[str] = []

        if not ctx.request_id:
            errors.append("request_id must not be empty.")
        if not ctx.execution_id:
            errors.append("execution_id must not be empty.")
        if not ctx.order_id:
            errors.append("order_id must not be empty.")
        if not ctx.portfolio_id:
            errors.append("portfolio_id must not be empty.")
        if not ctx.strategy_id:
            errors.append("strategy_id must not be empty.")
        if ctx.quantity < 0.0:
            errors.append(f"quantity must be >= 0, got {ctx.quantity}.")
        if ctx.price < 0.0:
            errors.append(f"price must be >= 0, got {ctx.price}.")
        if ctx.priority < 0:
            errors.append(f"priority must be >= 0, got {ctx.priority}.")

        if not ctx.symbol:
            warnings.append("symbol is empty; downstream routing may be impaired.")
        if not ctx.side:
            warnings.append("side is empty; downstream execution may be impaired.")
        if ctx.quantity == 0.0:
            warnings.append("quantity is 0.0; this may indicate an incomplete request.")

        return _result(errors, warnings)

    # ── Risk snapshot validation ───────────────────────────────────────────────

    def validate_risk_data(
        self,
        ctx: EngineGatewayContext,
        *,
        require_passed: bool = False,
    ) -> EngineValidationResult:
        """
        Validate risk outcome data on the context.

        If ``require_passed`` is True, contexts without PASSED / WARNING
        risk outcome are treated as errors.
        """
        errors:   List[str] = []
        warnings: List[str] = []

        if require_passed and not ctx.has_risk_data:
            errors.append(
                "risk_outcome is required but not present. "
                "Ensure ExecutionRiskSnapshot is attached before submitting."
            )
        elif ctx.has_risk_data and ctx.risk_outcome in ("BLOCKED", "FAILED"):
            errors.append(
                f"Request carries a blocking risk outcome: '{ctx.risk_outcome}'. "
                "Only PASSED or WARNING requests may proceed."
            )
        elif not ctx.has_risk_data:
            warnings.append("No risk snapshot attached; processing without risk data.")

        return _result(errors, warnings)

    # ── Session validation ────────────────────────────────────────────────────

    def validate_session(
        self,
        session: GatewaySession,
    ) -> EngineValidationResult:
        """Validate that a session is active and not expired."""
        errors:   List[str] = []
        warnings: List[str] = []

        if session.is_expired:
            errors.append(
                f"Session '{session.session_id}' has expired. Create a new session."
            )
        elif session.is_closed:
            errors.append(
                f"Session '{session.session_id}' is closed and cannot accept requests."
            )

        return _result(errors, warnings)

    # ── Request validation ────────────────────────────────────────────────────

    def validate_request(
        self,
        request: EngineGatewayRequest,
    ) -> EngineValidationResult:
        """Validate an EngineGatewayRequest before dispatch."""
        errors:   List[str] = []
        warnings: List[str] = []

        ctx_result = self.validate_context(request.context)
        errors.extend(ctx_result.errors)
        warnings.extend(ctx_result.warnings)

        if not request.session_id:
            warnings.append("request has no session_id assigned.")

        return _result(errors, warnings)

    # ── Queue capacity validation ─────────────────────────────────────────────

    def validate_queue_capacity(
        self,
        queue: GatewayOperationQueue,
    ) -> EngineValidationResult:
        """Check that the main queues are not exhausted."""
        errors:   List[str] = []
        warnings: List[str] = []

        sizes = queue.sizes()
        for queue_type, size in sizes.items():
            if size > 4_000:
                warnings.append(f"{queue_type} queue size is high: {size}.")

        return _result(errors, warnings)

    # ── Raise helper ──────────────────────────────────────────────────────────

    def raise_if_invalid(
        self,
        result:       EngineValidationResult,
        context_name: str = "",
    ) -> None:
        """
        Raise ``GatewayValidationFailedError`` if ``result.is_valid`` is False.

        Noop when the result is valid.
        """
        if not result.is_valid:
            prefix = f"Validation failed for '{context_name}'. " if context_name else ""
            raise GatewayValidationFailedError(
                message=prefix + "See validation_errors for details.",
                errors=result.errors,
            )
