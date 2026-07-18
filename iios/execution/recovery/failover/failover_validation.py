"""
iios/execution/recovery/failover/failover_validation.py
=======================================================
FailoverValidator — stateless validation for all failover entities.

C7 Execution Recovery & Resilience — Phase 1, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence


@dataclass
class FailoverValidationResult:
    """Mutable validation result."""

    is_valid: bool      = True
    errors:   List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def merge(self, other: "FailoverValidationResult") -> None:
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


class FailoverValidator:
    """
    Stateless validator for Failover Framework entities.

    All methods return a FailoverValidationResult and never raise.
    """

    # ── Request ───────────────────────────────────────────────────────────────

    def validate_request(self, request: Any) -> FailoverValidationResult:
        result = FailoverValidationResult()
        if request is None:
            result.add_error("request must not be None")
            return result
        if not getattr(request, "request_id", ""):
            result.add_error("request.request_id is required")
        if not getattr(request, "failover_session_id", ""):
            result.add_error("request.failover_session_id is required")
        if not getattr(request, "execution_session_id", ""):
            result.add_error("request.execution_session_id is required")
        if not getattr(request, "subsystem_id", ""):
            result.add_error("request.subsystem_id is required")
        if getattr(request, "failover_type", None) is None:
            result.add_error("request.failover_type is required")
        if getattr(request, "primary_action", None) is None:
            result.add_error("request.primary_action is required")
        if not getattr(request, "source_decision_id", ""):
            result.add_error("request.source_decision_id is required")
        if getattr(request, "context", None) is None:
            result.add_error("request.context is required")
        return result

    # ── Plan ─────────────────────────────────────────────────────────────────

    def validate_plan(self, plan: Any) -> FailoverValidationResult:
        result = FailoverValidationResult()
        if plan is None:
            result.add_error("plan must not be None")
            return result
        if not getattr(plan, "plan_id", ""):
            result.add_error("plan.plan_id is required")
        if not getattr(plan, "name", ""):
            result.add_error("plan.name is required")
        if getattr(plan, "failover_type", None) is None:
            result.add_error("plan.failover_type is required")
        if getattr(plan, "primary_action", None) is None:
            result.add_error("plan.primary_action is required")
        phases = getattr(plan, "phases", None)
        if not phases:
            result.add_error("plan.phases must not be empty")
        max_ms = getattr(plan, "max_execution_time_ms", -1)
        if max_ms <= 0:
            result.add_error("plan.max_execution_time_ms must be > 0")
        return result

    # ── Context ───────────────────────────────────────────────────────────────

    def validate_context(self, context: Any) -> FailoverValidationResult:
        result = FailoverValidationResult()
        if context is None:
            result.add_error("context must not be None")
            return result
        if not getattr(context, "failover_session_id", ""):
            result.add_error("context.failover_session_id is required")
        if not getattr(context, "execution_session_id", ""):
            result.add_error("context.execution_session_id is required")
        if not getattr(context, "subsystem_id", ""):
            result.add_error("context.subsystem_id is required")
        if getattr(context, "failover_type", None) is None:
            result.add_error("context.failover_type is required")
        if getattr(context, "primary_action", None) is None:
            result.add_error("context.primary_action is required")
        return result

    # ── Response ──────────────────────────────────────────────────────────────

    def validate_response(self, response: Any) -> FailoverValidationResult:
        result = FailoverValidationResult()
        if response is None:
            result.add_error("response must not be None")
            return result
        if not getattr(response, "response_id", ""):
            result.add_error("response.response_id is required")
        if not getattr(response, "failover_session_id", ""):
            result.add_error("response.failover_session_id is required")
        if getattr(response, "result", None) is None:
            result.add_error("response.result is required")
        return result

    # ── Resource compatibility ────────────────────────────────────────────────

    def validate_resource_availability(self, context: Any) -> FailoverValidationResult:
        """Check whether required resources are available for the planned action."""
        result = FailoverValidationResult()
        if context is None:
            result.add_error("context must not be None")
            return result

        from .constants import FailoverAction
        action = getattr(context, "primary_action", None)

        if action == FailoverAction.SWITCH_BROKER and not getattr(context, "backup_broker_available", False):
            result.add_error("Backup broker is not available for SWITCH_BROKER")
        if action == FailoverAction.SWITCH_GATEWAY and not getattr(context, "backup_gateway_available", False):
            result.add_error("Backup gateway is not available for SWITCH_GATEWAY")
        if action == FailoverAction.ROLLBACK and not getattr(context, "rollback_available", False):
            result.add_error("Rollback state is not available for ROLLBACK")
        if action in (FailoverAction.RETRY,) and getattr(context, "is_retry_exhausted", False):
            result.add_error("Retry is exhausted; cannot RETRY")

        return result
