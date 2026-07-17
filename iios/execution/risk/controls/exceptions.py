"""iios/execution/risk/controls/exceptions.py
==================================================
Exception hierarchy for the IIOS Execution Risk Controls Framework.

Error Codes
-----------
ERC-000  ExecutionControlError           — base
ERC-001  ControlNotRunningError          — engine/manager not started
ERC-002  PolicyEvaluationError           — policy raised during evaluate()
ERC-003  PolicyNotFoundError             — no policy registered for type
ERC-004  ControlValidationError          — request or context invalid
ERC-005  OverrideError                   — override workflow failed
ERC-006  EmergencyActionError            — emergency action failed
ERC-007  ControlFrameworkError           — internal framework error
ERC-008  ControlRegistrationError        — policy registration failed

C6 Execution Intelligence — Phase 4, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError


class ExecutionControlError(IIOSError):
    """Base for all Execution Risk Controls errors."""
    DEFAULT_CODE = "ERC-000"


class ControlNotRunningError(ExecutionControlError):
    """The engine or manager is not in the RUNNING state."""
    DEFAULT_CODE = "ERC-001"

    def __init__(
        self,
        *,
        code:           str = "ERC-001",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            "RiskControlManager is not running; call start() before use",
            code=code, context=context, correlation_id=correlation_id,
        )


class PolicyEvaluationError(ExecutionControlError):
    """A control policy raised during evaluate()."""
    DEFAULT_CODE = "ERC-002"

    def __init__(
        self,
        message: str,
        *,
        policy_type:    str = "",
        code:           str = "ERC-002",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code,
            context=context or {"policy_type": policy_type},
            correlation_id=correlation_id,
        )
        self.policy_type = policy_type


class PolicyNotFoundError(ExecutionControlError):
    """No policy is registered for the requested PolicyType."""
    DEFAULT_CODE = "ERC-003"

    def __init__(
        self,
        policy_type: str,
        *,
        code:           str = "ERC-003",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"No policy registered for type '{policy_type}'",
            code=code,
            context=context or {"policy_type": policy_type},
            correlation_id=correlation_id,
        )
        self.policy_type = policy_type


class ControlValidationError(ExecutionControlError):
    """Request, context, or decision failed validation."""
    DEFAULT_CODE = "ERC-004"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "ERC-004",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code, context=context, correlation_id=correlation_id,
        )


class OverrideError(ExecutionControlError):
    """Override workflow failed."""
    DEFAULT_CODE = "ERC-005"

    def __init__(
        self,
        message: str,
        *,
        override_id:    str = "",
        code:           str = "ERC-005",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code,
            context=context or {"override_id": override_id},
            correlation_id=correlation_id,
        )
        self.override_id = override_id


class EmergencyActionError(ExecutionControlError):
    """Emergency action workflow failed."""
    DEFAULT_CODE = "ERC-006"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "ERC-006",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code, context=context, correlation_id=correlation_id,
        )


class ControlFrameworkError(ExecutionControlError):
    """Internal framework error."""
    DEFAULT_CODE = "ERC-007"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "ERC-007",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code, context=context, correlation_id=correlation_id,
        )


class ControlRegistrationError(ExecutionControlError):
    """Policy registration failed."""
    DEFAULT_CODE = "ERC-008"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "ERC-008",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code, context=context, correlation_id=correlation_id,
        )
