"""iios/execution/gateway/routing/routing_validation.py
==================================================
RoutingValidationResult and RoutingValidator.

Validates routing contexts, requests, policies, candidates,
and decisions.  All validation is stateless.

C6 Execution Intelligence — Phase 5, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import RoutingValidationError
from .routing_candidate import RoutingCandidate
from .routing_context import RoutingContext
from .routing_policy import RoutingPolicyBase
from .routing_request import RoutingRequest
from .routing_response import RoutingDecision


@dataclass(frozen=True)
class RoutingValidationResult:
    """Immutable result of a validation pass."""

    is_valid: bool
    errors:   Tuple[str, ...]  = field(default_factory=tuple)
    warnings: Tuple[str, ...]  = field(default_factory=tuple)

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors":   list(self.errors),
            "warnings": list(self.warnings),
        }


class RoutingValidator:
    """
    Stateless validator for Routing Framework objects.

    All methods return a RoutingValidationResult — they never raise.
    Use raise_if_invalid() to convert a failed result to an exception.
    """

    # ── Context ───────────────────────────────────────────────────────────────

    def validate_context(self, context: RoutingContext) -> RoutingValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []

        if not context.routing_id:
            errors.append("routing_id must not be empty")
        if not context.execution_id:
            errors.append("execution_id must not be empty")
        if not context.order_id:
            errors.append("order_id must not be empty")
        if not context.portfolio_id:
            errors.append("portfolio_id must not be empty")
        if not context.strategy_id:
            errors.append("strategy_id must not be empty")
        if not context.symbol:
            errors.append("symbol must not be empty")
        if not context.exchange:
            errors.append("exchange must not be empty")
        if not context.side:
            errors.append("side must not be empty")
        if not context.order_type:
            errors.append("order_type must not be empty")
        if not context.product:
            errors.append("product must not be empty")
        if not context.asset_class:
            errors.append("asset_class must not be empty")
        if context.quantity <= 0:
            errors.append("quantity must be positive")
        if context.price < 0:
            errors.append("price must be non-negative")
        if context.priority < 0:
            errors.append("priority must be non-negative")
        if context.submitted_at <= 0:
            errors.append("submitted_at must be a positive Unix timestamp")

        return RoutingValidationResult(
            is_valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    # ── Request ───────────────────────────────────────────────────────────────

    def validate_request(
        self,
        request:    RoutingRequest,
        candidates: Optional[List[RoutingCandidate]] = None,
    ) -> RoutingValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []

        if not request.request_id:
            errors.append("request_id must not be empty")

        ctx_result = self.validate_context(request.context)
        errors.extend(ctx_result.errors)
        warnings.extend(ctx_result.warnings)

        if candidates is not None and len(candidates) == 0:
            warnings.append("no routing candidates are registered")

        return RoutingValidationResult(
            is_valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    # ── Policy ────────────────────────────────────────────────────────────────

    def validate_policy(self, policy: RoutingPolicyBase) -> RoutingValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []

        if not policy.policy_id:
            errors.append("policy_id must not be empty")
        if not policy.policy_name:
            warnings.append("policy_name is empty")
        if not hasattr(policy, "policy_type"):
            errors.append("policy must define policy_type")

        return RoutingValidationResult(
            is_valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    # ── Candidate ─────────────────────────────────────────────────────────────

    def validate_candidate(self, candidate: RoutingCandidate) -> RoutingValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []

        if not candidate.broker_id:
            errors.append("broker_id must not be empty")
        if not candidate.broker_name:
            warnings.append("broker_name is empty")
        if not 0.0 <= candidate.health_score <= 1.0:
            errors.append("health_score must be in [0.0, 1.0]")
        if candidate.weight < 0.0:
            errors.append("weight must be non-negative")

        return RoutingValidationResult(
            is_valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    # ── Decision ─────────────────────────────────────────────────────────────

    def validate_decision(self, decision: RoutingDecision) -> RoutingValidationResult:
        errors:   List[str] = []
        warnings: List[str] = []

        if not decision.decision_id:
            errors.append("decision_id must not be empty")
        if not decision.request_id:
            errors.append("request_id must not be empty")
        if not decision.routing_id:
            errors.append("routing_id must not be empty")
        if decision.is_routed and not decision.selected_broker_id:
            errors.append("is_routed is True but selected_broker_id is missing")
        if decision.routing_time_ms < 0:
            errors.append("routing_time_ms must be non-negative")
        if decision.candidates_evaluated < 0:
            errors.append("candidates_evaluated must be non-negative")
        if decision.candidates_available < 0:
            errors.append("candidates_available must be non-negative")

        return RoutingValidationResult(
            is_valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    # ── Raise helper ──────────────────────────────────────────────────────────

    def raise_if_invalid(
        self,
        result:  RoutingValidationResult,
        context: str = "",
    ) -> None:
        """Raise RoutingValidationError if result.is_valid is False."""
        if result.is_valid:
            return
        prefix = f"{context}: " if context else ""
        message = f"{prefix}Validation failed with {len(result.errors)} error(s)."
        raise RoutingValidationError(message, errors=result.errors)
