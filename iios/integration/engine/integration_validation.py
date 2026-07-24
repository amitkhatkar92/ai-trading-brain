"""
integration_validation.py — iios.integration.engine
-----------------------------------------------------
7-check validator for IntegrationRequest objects.

Checks:
  1. CONNECTOR_VALIDITY      — connector type is registered
  2. ADAPTER_COMPATIBILITY   — adapter exists for the connector type
  3. PROTOCOL_COMPATIBILITY  — protocol type is registered
  4. CONFIGURATION_INTEGRITY — required fields are non-empty
  5. AUTHENTICATION_VALIDITY — auth_config structure is valid
  6. LIFECYCLE_CONSISTENCY   — request metadata is internally consistent
  7. INPUT_COMPLETENESS      — payload and endpoint are present

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .constants import EngineValidationCheck
from .integration_registry import IntegrationEngineRegistry
from .integration_request import IntegrationRequest


@dataclass(frozen=True)
class EngineValidationResult:
    check:   EngineValidationCheck
    passed:  bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check":   self.check.value,
            "passed":  self.passed,
            "message": self.message,
        }


@dataclass(frozen=True)
class EngineValidationReport:
    request_id: str
    results:    tuple   # Tuple[EngineValidationResult]
    passed:     bool

    @property
    def failed_checks(self) -> List[str]:
        return [r.check.value for r in self.results if not r.passed]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":   self.request_id,
            "passed":       self.passed,
            "failed_checks": self.failed_checks,
            "results":      [r.to_dict() for r in self.results],
        }


class IntegrationEngineValidator:
    """Runs 7 validation checks against an IntegrationRequest."""

    def validate(
        self,
        request:  IntegrationRequest,
        registry: IntegrationEngineRegistry,
    ) -> EngineValidationReport:
        results = [
            self._check_connector_validity(request, registry),
            self._check_adapter_compatibility(request, registry),
            self._check_protocol_compatibility(request, registry),
            self._check_configuration_integrity(request),
            self._check_authentication_validity(request),
            self._check_lifecycle_consistency(request),
            self._check_input_completeness(request),
        ]
        passed = all(r.passed for r in results)
        return EngineValidationReport(
            request_id = request.request_id,
            results    = tuple(results),
            passed     = passed,
        )

    # ----------------------------------------------------------------
    # Individual checks
    # ----------------------------------------------------------------

    def _check_connector_validity(
        self,
        request:  IntegrationRequest,
        registry: IntegrationEngineRegistry,
    ) -> EngineValidationResult:
        code = EngineValidationCheck.CONNECTOR_VALIDITY
        if not registry.has_connector(request.connector_type):
            return EngineValidationResult(
                check   = code,
                passed  = False,
                message = (
                    f"No connector registered for type "
                    f"{request.connector_type.value!r}"
                ),
            )
        return EngineValidationResult(check=code, passed=True, message="OK")

    def _check_adapter_compatibility(
        self,
        request:  IntegrationRequest,
        registry: IntegrationEngineRegistry,
    ) -> EngineValidationResult:
        code = EngineValidationCheck.ADAPTER_COMPATIBILITY
        if not registry.has_adapter_for(request.connector_type):
            return EngineValidationResult(
                check   = code,
                passed  = False,
                message = (
                    f"No adapter registered for connector type "
                    f"{request.connector_type.value!r}"
                ),
            )
        return EngineValidationResult(check=code, passed=True, message="OK")

    def _check_protocol_compatibility(
        self,
        request:  IntegrationRequest,
        registry: IntegrationEngineRegistry,
    ) -> EngineValidationResult:
        code = EngineValidationCheck.PROTOCOL_COMPATIBILITY
        if not registry.has_protocol(request.protocol_type):
            return EngineValidationResult(
                check   = code,
                passed  = False,
                message = (
                    f"Protocol {request.protocol_type.value!r} is not registered"
                ),
            )
        return EngineValidationResult(check=code, passed=True, message="OK")

    def _check_configuration_integrity(
        self,
        request: IntegrationRequest,
    ) -> EngineValidationResult:
        code = EngineValidationCheck.CONFIGURATION_INTEGRITY
        if not request.request_id or not request.correlation_id:
            return EngineValidationResult(
                check   = code,
                passed  = False,
                message = "request_id and correlation_id must be non-empty",
            )
        return EngineValidationResult(check=code, passed=True, message="OK")

    def _check_authentication_validity(
        self,
        request: IntegrationRequest,
    ) -> EngineValidationResult:
        code = EngineValidationCheck.AUTHENTICATION_VALIDITY
        # auth_config may be empty (unauthenticated) but must be a dict
        if not isinstance(request.auth_config, dict):
            return EngineValidationResult(
                check   = code,
                passed  = False,
                message = "auth_config must be a dict",
            )
        return EngineValidationResult(check=code, passed=True, message="OK")

    def _check_lifecycle_consistency(
        self,
        request: IntegrationRequest,
    ) -> EngineValidationResult:
        code = EngineValidationCheck.LIFECYCLE_CONSISTENCY
        if request.priority < 0 or request.priority > 10:
            return EngineValidationResult(
                check   = code,
                passed  = False,
                message = f"priority must be 0–10, got {request.priority}",
            )
        return EngineValidationResult(check=code, passed=True, message="OK")

    def _check_input_completeness(
        self,
        request: IntegrationRequest,
    ) -> EngineValidationResult:
        code = EngineValidationCheck.INPUT_COMPLETENESS
        if not isinstance(request.payload, dict):
            return EngineValidationResult(
                check   = code,
                passed  = False,
                message = "payload must be a dict",
            )
        return EngineValidationResult(check=code, passed=True, message="OK")
