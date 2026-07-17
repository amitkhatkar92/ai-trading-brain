"""iios/execution/risk/engine/exceptions.py
==================================================
Exception hierarchy for the IIOS Execution Risk Engine.

Error Codes
-----------
ERM-000  ExecutionRiskEngineError          — base
ERM-001  RiskEngineNotRunningError         — engine is not started
ERM-002  EvaluationOperationError          — generic operation failure
ERM-003  EvaluationCreationError           — create evaluation failed
ERM-004  EvaluationExecutionError          — rule execution phase failed
ERM-005  EvaluationAggregationError        — aggregation phase failed
ERM-006  EvaluationFinalizationError       — finalisation phase failed
ERM-007  EvaluationNotFoundError           — evaluation_id does not exist
ERM-008  RuleRegistrationError             — rule registration failed
ERM-009  RiskEngineValidationError         — request validation failed
ERM-010  RiskEngineStateError              — engine in unexpected state

C6 Execution Intelligence — Phase 4, Module 2
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError


class ExecutionRiskEngineError(IIOSError):
    """Base for all Execution Risk Engine errors."""
    DEFAULT_CODE = "ERM-000"


class RiskEngineNotRunningError(ExecutionRiskEngineError):
    """The engine or manager is not in the RUNNING state."""
    DEFAULT_CODE = "ERM-001"

    def __init__(
        self,
        *,
        code:           str = "ERM-001",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            "RiskEngine is not running; call start() before use",
            code=code, context=context, correlation_id=correlation_id,
        )


class EvaluationOperationError(ExecutionRiskEngineError):
    """A risk evaluation operation failed for an unspecified reason."""
    DEFAULT_CODE = "ERM-002"

    def __init__(
        self,
        message:   str,
        *,
        operation:      str = "",
        code:           str = "ERM-002",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code,
            context=context or {"operation": operation},
            correlation_id=correlation_id,
        )
        self.operation = operation


class EvaluationCreationError(ExecutionRiskEngineError):
    """The CREATE_EVALUATION operation failed."""
    DEFAULT_CODE = "ERM-003"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "ERM-003",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)


class EvaluationExecutionError(ExecutionRiskEngineError):
    """The EVALUATE (rule execution) phase failed."""
    DEFAULT_CODE = "ERM-004"

    def __init__(
        self,
        message:     str,
        *,
        rule_name:      str = "",
        code:           str = "ERM-004",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code,
            context=context or {"rule_name": rule_name},
            correlation_id=correlation_id,
        )
        self.rule_name = rule_name


class EvaluationAggregationError(ExecutionRiskEngineError):
    """The AGGREGATE phase failed."""
    DEFAULT_CODE = "ERM-005"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "ERM-005",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)


class EvaluationFinalizationError(ExecutionRiskEngineError):
    """The FINALIZE phase failed."""
    DEFAULT_CODE = "ERM-006"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "ERM-006",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)


class EvaluationNotFoundError(ExecutionRiskEngineError):
    """No evaluation found for the given identifier."""
    DEFAULT_CODE = "ERM-007"

    def __init__(
        self,
        evaluation_id: str,
        *,
        code:           str = "ERM-007",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Risk evaluation '{evaluation_id}' not found",
            code=code,
            context=context or {"evaluation_id": evaluation_id},
            correlation_id=correlation_id,
        )
        self.evaluation_id = evaluation_id


class RuleRegistrationError(ExecutionRiskEngineError):
    """A risk rule could not be registered."""
    DEFAULT_CODE = "ERM-008"

    def __init__(
        self,
        message:  str,
        *,
        rule_name:      str = "",
        code:           str = "ERM-008",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code,
            context=context or {"rule_name": rule_name},
            correlation_id=correlation_id,
        )
        self.rule_name = rule_name


class RiskEngineValidationError(ExecutionRiskEngineError):
    """A request failed engine-level validation."""
    DEFAULT_CODE = "ERM-009"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "ERM-009",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)


class RiskEngineStateError(ExecutionRiskEngineError):
    """The engine is in an unexpected state."""
    DEFAULT_CODE = "ERM-010"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "ERM-010",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)
