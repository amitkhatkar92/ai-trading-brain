"""iios/execution/risk/controls/risk_control_validation.py
==================================================
Validation for the Controls Framework.

C6 Execution Intelligence — Phase 4, Module 4
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from .constants import ControlAction, PolicyType
from .exceptions import ControlValidationError
from .risk_control_context import ControlContext
from .risk_control_decision import OverrideInfo, RiskControlDecision
from .risk_control_request import ControlRequest


@dataclass(frozen=True)
class ControlValidationResult:
    """Result of a validation run."""
    is_valid:     bool
    errors:       Tuple[str, ...]
    warnings:     Tuple[str, ...]
    validated_at: float = field(default_factory=time.time)

    def __bool__(self) -> bool:
        return self.is_valid


class RiskControlValidator:
    """
    Stateless validator for the Controls Framework.

    All methods return ``ControlValidationResult`` — they do not raise.
    Use ``raise_if_invalid()`` to convert a failed result into an exception.
    """

    @staticmethod
    def validate_request(request: ControlRequest) -> ControlValidationResult:
        errors: List[str]   = []
        warnings: List[str] = []

        if not isinstance(request, ControlRequest):
            errors.append("request must be a ControlRequest instance")
            return ControlValidationResult(False, tuple(errors), tuple(warnings))

        if not request.rule_results:
            warnings.append("rule_results is empty — decision will default to ALLOW")

        if not request.evaluation_id:
            warnings.append("evaluation_id is empty")

        if not isinstance(request.policy_type, PolicyType):
            errors.append(f"policy_type must be a PolicyType enum; got {type(request.policy_type)}")

        if not isinstance(request.context, ControlContext):
            errors.append("context must be a ControlContext instance")

        return ControlValidationResult(
            is_valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    @staticmethod
    def validate_decision(decision: RiskControlDecision) -> ControlValidationResult:
        errors: List[str]   = []
        warnings: List[str] = []

        if not isinstance(decision, RiskControlDecision):
            errors.append("decision must be a RiskControlDecision instance")
            return ControlValidationResult(False, tuple(errors), tuple(warnings))

        if not isinstance(decision.action, ControlAction):
            errors.append(f"action must be a ControlAction enum; got {type(decision.action)}")

        if decision.elapsed_ms < 0:
            errors.append("elapsed_ms must be non-negative")

        if not decision.decision_id:
            errors.append("decision_id is empty")

        if decision.was_overridden and decision.override_info is None:
            errors.append("was_overridden is True but override_info is None")

        return ControlValidationResult(
            is_valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    @staticmethod
    def validate_override(
        override_info: OverrideInfo,
        decision:      RiskControlDecision,
    ) -> ControlValidationResult:
        errors: List[str]   = []
        warnings: List[str] = []

        if not override_info.approver:
            errors.append("override_info.approver is required")

        if not override_info.reason:
            errors.append("override_info.reason is required")

        if not override_info.override_id:
            errors.append("override_info.override_id is required")

        if override_info.original_action not in (
            ControlAction.BLOCK,
            ControlAction.REQUIRE_OVERRIDE,
            ControlAction.CANCEL,
            ControlAction.PAUSE,
        ):
            errors.append(
                f"original_action '{override_info.original_action}' "
                f"is not eligible for override"
            )

        if override_info.new_action not in (
            ControlAction.ALLOW,
            ControlAction.ALLOW_WITH_WARNING,
        ):
            errors.append(
                f"new_action '{override_info.new_action}' must be "
                "ALLOW or ALLOW_WITH_WARNING"
            )

        if decision.action == ControlAction.EMERGENCY_STOP:
            errors.append("EMERGENCY_STOP decisions cannot be overridden")

        if not override_info.affected_rule_ids:
            warnings.append("affected_rule_ids is empty — override scope undefined")

        return ControlValidationResult(
            is_valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    @staticmethod
    def validate_context(context: ControlContext) -> ControlValidationResult:
        errors: List[str]   = []
        warnings: List[str] = []

        if not isinstance(context, ControlContext):
            errors.append("context must be a ControlContext instance")
            return ControlValidationResult(False, tuple(errors), tuple(warnings))

        if not context.context_id:
            errors.append("context_id is empty")

        if context.age_ms > 60_000:
            warnings.append(f"context is {context.age_ms:.0f}ms old — may be stale")

        return ControlValidationResult(
            is_valid=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    @staticmethod
    def raise_if_invalid(
        result:  ControlValidationResult,
        context: str = "",
    ) -> None:
        if not result.is_valid:
            msg = "; ".join(result.errors)
            if context:
                msg = f"[{context}] {msg}"
            raise ControlValidationError(msg)
