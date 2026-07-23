"""
market_integration_validation.py — iios.market.integration
============================================================
Integration-level validation — 6 structural checks.

C12 Market Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import dataclasses
from typing import Callable, List, Optional, Tuple

from .constants import IntegrationValidationCode
from .exceptions import MarketIntegrationValidationError
from .market_integration_request import MarketIntegrationRequest


@dataclasses.dataclass(frozen=True)
class IntegrationCheckResult:
    """Result of a single integration validation check."""
    code:    IntegrationValidationCode
    passed:  bool
    message: str = ""


@dataclasses.dataclass(frozen=True)
class MarketIntegrationValidationResult:
    """Aggregate result of all validation checks."""
    is_valid:      bool
    failed_checks: Tuple[IntegrationCheckResult, ...]
    passed_checks: Tuple[IntegrationCheckResult, ...]
    request_id:    str = ""

    @property
    def failure_messages(self) -> List[str]:
        return [c.message for c in self.failed_checks if c.message]


class MarketIntegrationValidation:
    """
    Validates a :class:`~.market_integration_request.MarketIntegrationRequest`
    before it enters the processing pipeline.

    Checks
    ------
    1. API_CONSISTENCY        — required fields are non-empty
    2. LIFECYCLE_CONSISTENCY  — exchange is non-empty, integration_id is valid
    3. SUBSYSTEM_AVAILABILITY — engine is running (via is_running_fn)
    4. SNAPSHOT_INTEGRITY     — inputs dict is not None (structural gate only)
    5. INPUT_VALIDATION       — inputs are a valid mapping
    6. RESPONSE_VALIDATION    — request_type is a recognised type
    """

    def __init__(
        self,
        is_running_fn: Optional[Callable[[], bool]] = None,
    ) -> None:
        self._is_running_fn = is_running_fn or (lambda: True)

    def validate(
        self,
        request: MarketIntegrationRequest,
    ) -> MarketIntegrationValidationResult:
        checks = [
            self._check_api_consistency(request),
            self._check_lifecycle_consistency(request),
            self._check_subsystem_availability(),
            self._check_snapshot_integrity(request),
            self._check_input_validation(request),
            self._check_response_validation(request),
        ]
        failed = tuple(c for c in checks if not c.passed)
        passed = tuple(c for c in checks if c.passed)
        return MarketIntegrationValidationResult(
            is_valid      = len(failed) == 0,
            failed_checks = failed,
            passed_checks = passed,
            request_id    = request.request_id,
        )

    def validate_or_raise(self, request: MarketIntegrationRequest) -> None:
        result = self.validate(request)
        if not result.is_valid:
            raise MarketIntegrationValidationError(
                "; ".join(result.failure_messages),
                request_id     = request.request_id,
                failed_checks  = result.failed_checks,
            )

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_api_consistency(r: MarketIntegrationRequest) -> IntegrationCheckResult:
        ok = bool(r.request_id) and bool(r.integration_id)
        return IntegrationCheckResult(
            code    = IntegrationValidationCode.API_CONSISTENCY,
            passed  = ok,
            message = "" if ok else "request_id and integration_id are required",
        )

    @staticmethod
    def _check_lifecycle_consistency(r: MarketIntegrationRequest) -> IntegrationCheckResult:
        ok = bool(r.exchange)
        return IntegrationCheckResult(
            code    = IntegrationValidationCode.LIFECYCLE_CONSISTENCY,
            passed  = ok,
            message = "" if ok else "exchange must not be empty",
        )

    def _check_subsystem_availability(self) -> IntegrationCheckResult:
        ok = self._is_running_fn()
        return IntegrationCheckResult(
            code    = IntegrationValidationCode.SUBSYSTEM_AVAILABILITY,
            passed  = ok,
            message = "" if ok else "Integration engine is not running",
        )

    @staticmethod
    def _check_snapshot_integrity(r: MarketIntegrationRequest) -> IntegrationCheckResult:
        ok = r.inputs is not None
        return IntegrationCheckResult(
            code    = IntegrationValidationCode.SNAPSHOT_INTEGRITY,
            passed  = ok,
            message = "" if ok else "inputs must not be None",
        )

    @staticmethod
    def _check_input_validation(r: MarketIntegrationRequest) -> IntegrationCheckResult:
        ok = isinstance(r.inputs, dict)
        return IntegrationCheckResult(
            code    = IntegrationValidationCode.INPUT_VALIDATION,
            passed  = ok,
            message = "" if ok else "inputs must be a dictionary",
        )

    @staticmethod
    def _check_response_validation(r: MarketIntegrationRequest) -> IntegrationCheckResult:
        from .constants import IntegrationRequestType
        ok = isinstance(r.request_type, IntegrationRequestType)
        return IntegrationCheckResult(
            code    = IntegrationValidationCode.RESPONSE_VALIDATION,
            passed  = ok,
            message = "" if ok else
                f"request_type must be IntegrationRequestType (got {type(r.request_type)})",
        )
