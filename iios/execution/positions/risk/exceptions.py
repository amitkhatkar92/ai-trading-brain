"""iios/execution/positions/risk/exceptions.py
==================================================
Exception hierarchy for the IIOS Position Risk State module.

Error Codes
-----------
PR4-000  PositionRiskError               — base
PR4-001  PositionRiskNotRunningError     — manager not started
PR4-002  RiskStateNotFoundError          — position not registered
PR4-003  DuplicateRiskStateError         — position already registered
PR4-004  PositionRiskValidationError     — consistency check failed
PR4-005  PositionRiskCapacityError       — registry at max capacity
PR4-006  InvalidRiskLevelError           — invalid risk level transition
PR4-007  RiskLimitsError                 — invalid risk limits configuration
PR4-008  RiskEvaluationError             — evaluation operation failed
PR4-009  RiskSnapshotError               — snapshot generation failed

C6 Execution Intelligence — Phase 3, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError

from .constants import RiskLevel


class PositionRiskError(IIOSError):
    """Base for all Position Risk State errors."""
    DEFAULT_CODE = "PR4-000"


class PositionRiskNotRunningError(PositionRiskError):
    """The risk manager or registry has not been started."""
    DEFAULT_CODE = "PR4-001"

    def __init__(
        self,
        *,
        code:           str = "PR4-001",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            "PositionRiskManager is not running",
            code=code, context=context, correlation_id=correlation_id,
        )


class RiskStateNotFoundError(PositionRiskError):
    """No risk state found for the given position_id."""
    DEFAULT_CODE = "PR4-002"

    def __init__(
        self,
        position_id: str,
        *,
        code:           str = "PR4-002",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Risk state not found for position '{position_id}'",
            code=code,
            context=context or {"position_id": position_id},
            correlation_id=correlation_id,
        )
        self.position_id = position_id


class DuplicateRiskStateError(PositionRiskError):
    """A risk state for this position_id already exists."""
    DEFAULT_CODE = "PR4-003"

    def __init__(
        self,
        position_id: str,
        *,
        code:           str = "PR4-003",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Risk state for position '{position_id}' already registered",
            code=code,
            context=context or {"position_id": position_id},
            correlation_id=correlation_id,
        )
        self.position_id = position_id


class PositionRiskValidationError(PositionRiskError):
    """A risk state consistency check failed."""
    DEFAULT_CODE = "PR4-004"

    def __init__(
        self,
        message: str,
        *,
        errors:         tuple = (),
        code:           str = "PR4-004",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)
        self.errors = errors


class PositionRiskCapacityError(PositionRiskError):
    """The risk registry is at maximum capacity."""
    DEFAULT_CODE = "PR4-005"

    def __init__(
        self,
        capacity: int,
        *,
        code:           str = "PR4-005",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"Risk registry at maximum capacity ({capacity})",
            code=code,
            context=context or {"capacity": capacity},
            correlation_id=correlation_id,
        )
        self.capacity = capacity


class InvalidRiskLevelError(PositionRiskError):
    """An invalid or unexpected risk level was encountered."""
    DEFAULT_CODE = "PR4-006"

    def __init__(
        self,
        message:  str,
        *,
        level:          Optional[RiskLevel] = None,
        code:           str = "PR4-006",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)
        self.level = level


class RiskLimitsError(PositionRiskError):
    """Risk limits configuration is invalid."""
    DEFAULT_CODE = "PR4-007"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "PR4-007",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)


class RiskEvaluationError(PositionRiskError):
    """A risk evaluation operation failed."""
    DEFAULT_CODE = "PR4-008"

    def __init__(
        self,
        message:     str,
        position_id: str = "",
        *,
        code:           str = "PR4-008",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code,
            context=context or {"position_id": position_id},
            correlation_id=correlation_id,
        )
        self.position_id = position_id


class RiskSnapshotError(PositionRiskError):
    """A risk snapshot generation failed."""
    DEFAULT_CODE = "PR4-009"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "PR4-009",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)
