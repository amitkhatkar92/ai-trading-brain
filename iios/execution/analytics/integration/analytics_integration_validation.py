"""
analytics_integration_validation.py — iios.execution.analytics.integration
===========================================================================
Validation engine for the Execution Analytics Integration subsystem.

Runs the seven checks mandated by the specification and returns a structured
:class:`IntegrationValidationResult`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    INTEGRATION_VERSION,
    IntegrationValidationCode,
)


# ---------------------------------------------------------------------------
# Result object
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ValidationCheckResult:
    """
    Outcome of a single validation check.

    Fields
    ------
    code :     :class:`IntegrationValidationCode` that identifies the check.
    passed :   ``True`` when the check passed.
    message :  Human-readable diagnosis.  Empty on pass.
    """
    code:    IntegrationValidationCode
    passed:  bool
    message: str = ""


@dataclass(frozen=True)
class IntegrationValidationResult:
    """
    Aggregate result of all seven integration validation checks.

    Fields
    ------
    is_valid :        ``True`` when all checks passed.
    checks :          Tuple of per-check results.
    failed_checks :   Tuple of codes for checks that did not pass.
    error_messages :  Tuple of messages from failed checks.
    framework_version : Framework version string.
    """
    is_valid:        bool
    checks:          Tuple[ValidationCheckResult, ...]
    failed_checks:   Tuple[IntegrationValidationCode, ...]
    error_messages:  Tuple[str, ...]
    framework_version: str = INTEGRATION_VERSION

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        return len(self.failed_checks)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------
class AnalyticsIntegrationValidator:
    """
    Validates the seven integration consistency and readiness checks.

    The validator is stateless — call :meth:`validate` with the current
    component running-state dictionary and request parameters.

    Check catalogue
    ---------------
    1. LIFECYCLE_CONSISTENCY   — M1 lifecycle component is running.
    2. ENGINE_CONSISTENCY      — M2 analytics engine is running.
    3. PERFORMANCE_CONSISTENCY — M3 performance engine is running (when
                                 ``include_performance=True``).
    4. PREDICTION_CONSISTENCY  — M4 predictive engine is running (when
                                 ``include_predictions=True``).
    5. SNAPSHOT_CONSISTENCY    — M5 snapshot factory and store are running.
    6. INTEGRATION_CONSISTENCY — Integration manager is in a valid state.
    7. SUBSYSTEM_READINESS     — Request fields are structurally valid.
    """

    def validate(
        self,
        *,
        lifecycle_running:     bool,
        engine_running:        bool,
        performance_running:   bool,
        predictive_running:    bool,
        snapshot_running:      bool,
        integration_running:   bool,
        request_valid:         bool = True,
        include_performance:   bool = True,
        include_predictions:   bool = True,
        request_error:         str = "",
        extra_context:         Optional[Dict[str, Any]] = None,
    ) -> IntegrationValidationResult:
        """
        Run all seven validation checks and return a structured result.

        Parameters
        ----------
        lifecycle_running :     M1 component lifecycle state.
        engine_running :        M2 component lifecycle state.
        performance_running :   M3 component lifecycle state.
        predictive_running :    M4 component lifecycle state.
        snapshot_running :      M5 component lifecycle state.
        integration_running :   Integration manager lifecycle state.
        request_valid :         Whether the current request is structurally valid.
        include_performance :   Whether the request asks for performance analytics.
        include_predictions :   Whether the request asks for predictions.
        request_error :         Error description from request validation (if any).
        extra_context :         Supplementary context (unused; for future extension).
        """
        checks: List[ValidationCheckResult] = []

        # 1. Lifecycle consistency
        checks.append(self._check(
            IntegrationValidationCode.LIFECYCLE_CONSISTENCY,
            lifecycle_running,
            "M1 analytics lifecycle component is not running",
        ))

        # 2. Engine consistency
        checks.append(self._check(
            IntegrationValidationCode.ENGINE_CONSISTENCY,
            engine_running,
            "M2 analytics engine component is not running",
        ))

        # 3. Performance consistency (only required when requested)
        perf_ok = performance_running or not include_performance
        checks.append(self._check(
            IntegrationValidationCode.PERFORMANCE_CONSISTENCY,
            perf_ok,
            "M3 performance analytics engine is not running "
            "(required because include_performance=True)",
        ))

        # 4. Prediction consistency (only required when requested)
        pred_ok = predictive_running or not include_predictions
        checks.append(self._check(
            IntegrationValidationCode.PREDICTION_CONSISTENCY,
            pred_ok,
            "M4 predictive intelligence engine is not running "
            "(required because include_predictions=True)",
        ))

        # 5. Snapshot consistency
        checks.append(self._check(
            IntegrationValidationCode.SNAPSHOT_CONSISTENCY,
            snapshot_running,
            "M5 analytics snapshot factory/store is not running",
        ))

        # 6. Integration consistency
        checks.append(self._check(
            IntegrationValidationCode.INTEGRATION_CONSISTENCY,
            integration_running,
            "Integration manager is not in a running state",
        ))

        # 7. Subsystem readiness (request structural validity)
        checks.append(self._check(
            IntegrationValidationCode.SUBSYSTEM_READINESS,
            request_valid,
            request_error or "Request failed structural validation",
        ))

        checks_tuple = tuple(checks)
        failed = tuple(c.code for c in checks if not c.passed)
        errors = tuple(c.message for c in checks if not c.passed and c.message)

        return IntegrationValidationResult(
            is_valid      = len(failed) == 0,
            checks        = checks_tuple,
            failed_checks = failed,
            error_messages = errors,
        )

    def validate_request_only(
        self,
        *,
        execution_session_id: str,
        priority: int,
    ) -> Tuple[bool, str]:
        """
        Quick structural check of request fields.

        Returns ``(True, "")`` on pass, ``(False, message)`` on failure.
        """
        if not isinstance(execution_session_id, str) or not execution_session_id.strip():
            return False, "execution_session_id must be a non-empty string"
        if not (1 <= priority <= 10):
            return False, f"priority must be in [1, 10], got {priority}"
        return True, ""

    @staticmethod
    def _check(
        code: IntegrationValidationCode,
        condition: bool,
        failure_message: str,
    ) -> ValidationCheckResult:
        return ValidationCheckResult(
            code    = code,
            passed  = condition,
            message = "" if condition else failure_message,
        )
