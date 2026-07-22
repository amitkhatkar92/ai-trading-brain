"""
portfolio_integration_validation.py — iios.portfolio.integration
=================================================================
PortfolioIntegrationValidator — executes seven deterministic checks.

C10 Portfolio Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from .constants import (
    INTEGRATION_SYSTEM_ID,
    IntegrationValidationCode,
    IntegrationServiceType,
)
from .portfolio_integration_request import PortfolioIntegrationRequest

if TYPE_CHECKING:
    from .portfolio_component_registry import PortfolioComponentRegistry


# ---------------------------------------------------------------------------
# Result value objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IntegrationValidationCheckResult:
    """Outcome of a single integration validation check."""
    code:    str   # IntegrationValidationCode.value
    passed:  bool
    message: str


@dataclass(frozen=True)
class IntegrationValidationResult:
    """Aggregate outcome of all seven integration validation checks."""
    is_valid:       bool
    checks:         tuple   # Tuple[IntegrationValidationCheckResult, ...]
    failed_checks:  tuple
    passed_count:   int
    failed_count:   int
    error_messages: tuple
    duration_s:     float

    @classmethod
    def from_checks(
        cls,
        checks:     Tuple,
        duration_s: float,
    ) -> "IntegrationValidationResult":
        passed = tuple(c for c in checks if c.passed)
        failed = tuple(c for c in checks if not c.passed)
        return cls(
            is_valid       = len(failed) == 0,
            checks         = checks,
            failed_checks  = failed,
            passed_count   = len(passed),
            failed_count   = len(failed),
            error_messages = tuple(c.message for c in failed),
            duration_s     = duration_s,
        )

    @property
    def checks_count(self) -> int:
        return len(self.checks)


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class PortfolioIntegrationValidator:
    """
    Executes the seven canonical validation checks for integration requests.

    Checks
    ------
    1. LIFECYCLE_CONSISTENCY
    2. ENGINE_CONSISTENCY
    3. POLICY_CONSISTENCY
    4. OPTIMIZATION_CONSISTENCY
    5. SNAPSHOT_CONSISTENCY
    6. INTEGRATION_CONSISTENCY
    7. SUBSYSTEM_READINESS
    """

    _VALID_SERVICE_TYPES = frozenset(s.value for s in IntegrationServiceType)
    _VALID_LIFECYCLE_STATES = frozenset({
        "initialising", "running", "paused", "stopped", "error",
        "active", "inactive", "pending",
    })

    def validate(
        self,
        request: PortfolioIntegrationRequest,
        component_registry: "PortfolioComponentRegistry | None" = None,
    ) -> IntegrationValidationResult:
        start = time.perf_counter()
        checks = (
            self._check_lifecycle_consistency(request),
            self._check_engine_consistency(request),
            self._check_policy_consistency(request),
            self._check_optimization_consistency(request),
            self._check_snapshot_consistency(request),
            self._check_integration_consistency(request),
            self._check_subsystem_readiness(request, component_registry),
        )
        duration = time.perf_counter() - start
        return IntegrationValidationResult.from_checks(checks, duration)

    # ------------------------------------------------------------------
    # Check 1 — Lifecycle consistency
    # ------------------------------------------------------------------

    def _check_lifecycle_consistency(
        self, req: PortfolioIntegrationRequest
    ) -> IntegrationValidationCheckResult:
        code = IntegrationValidationCode.LIFECYCLE_CONSISTENCY.value
        if not req.portfolio_id:
            return _fail(code, "portfolio_id must not be empty")
        lifecycle_state = req.inputs.get("lifecycle_state", "running")
        if lifecycle_state and lifecycle_state.lower() not in self._VALID_LIFECYCLE_STATES:
            return _fail(
                code,
                f"lifecycle_state {lifecycle_state!r} is not a recognised value",
            )
        return _pass(code)

    # ------------------------------------------------------------------
    # Check 2 — Engine consistency
    # ------------------------------------------------------------------

    def _check_engine_consistency(
        self, req: PortfolioIntegrationRequest
    ) -> IntegrationValidationCheckResult:
        code = IntegrationValidationCode.ENGINE_CONSISTENCY.value
        if not req.request_id:
            return _fail(code, "request_id must not be empty")
        if req.priority < 1 or req.priority > 10:
            return _fail(code, f"priority must be between 1 and 10 (got {req.priority})")
        return _pass(code)

    # ------------------------------------------------------------------
    # Check 3 — Policy consistency
    # ------------------------------------------------------------------

    def _check_policy_consistency(
        self, req: PortfolioIntegrationRequest
    ) -> IntegrationValidationCheckResult:
        code = IntegrationValidationCode.POLICY_CONSISTENCY.value
        policy_data = req.inputs.get("policy_context")
        if policy_data is not None and not isinstance(policy_data, dict):
            return _fail(
                code,
                "inputs[policy_context] must be a dict when provided",
            )
        return _pass(code)

    # ------------------------------------------------------------------
    # Check 4 — Optimization consistency
    # ------------------------------------------------------------------

    def _check_optimization_consistency(
        self, req: PortfolioIntegrationRequest
    ) -> IntegrationValidationCheckResult:
        code = IntegrationValidationCode.OPTIMIZATION_CONSISTENCY.value
        opt_data = req.inputs.get("optimization_context")
        if opt_data is not None and not isinstance(opt_data, dict):
            return _fail(
                code,
                "inputs[optimization_context] must be a dict when provided",
            )
        return _pass(code)

    # ------------------------------------------------------------------
    # Check 5 — Snapshot consistency
    # ------------------------------------------------------------------

    def _check_snapshot_consistency(
        self, req: PortfolioIntegrationRequest
    ) -> IntegrationValidationCheckResult:
        code = IntegrationValidationCode.SNAPSHOT_CONSISTENCY.value
        snap_data = req.inputs.get("snapshot_context")
        if snap_data is not None and not isinstance(snap_data, dict):
            return _fail(
                code,
                "inputs[snapshot_context] must be a dict when provided",
            )
        return _pass(code)

    # ------------------------------------------------------------------
    # Check 6 — Integration consistency
    # ------------------------------------------------------------------

    def _check_integration_consistency(
        self, req: PortfolioIntegrationRequest
    ) -> IntegrationValidationCheckResult:
        code = IntegrationValidationCode.INTEGRATION_CONSISTENCY.value
        if req.service_type not in self._VALID_SERVICE_TYPES:
            return _fail(
                code,
                f"service_type {req.service_type!r} is not a recognised value",
            )
        if not req.framework_version:
            return _fail(code, "framework_version must not be empty")
        return _pass(code)

    # ------------------------------------------------------------------
    # Check 7 — Subsystem readiness
    # ------------------------------------------------------------------

    def _check_subsystem_readiness(
        self,
        req:                PortfolioIntegrationRequest,
        component_registry: "PortfolioComponentRegistry | None",
    ) -> IntegrationValidationCheckResult:
        code = IntegrationValidationCode.SUBSYSTEM_READINESS.value
        if component_registry is None:
            # No registry injected — skip readiness check
            return _pass(code)
        if not component_registry.is_ready():
            return _fail(
                code,
                "One or more required integration components are not running",
            )
        return _pass(code)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pass(code: str) -> IntegrationValidationCheckResult:
    return IntegrationValidationCheckResult(code=code, passed=True, message="")


def _fail(code: str, msg: str) -> IntegrationValidationCheckResult:
    return IntegrationValidationCheckResult(code=code, passed=False, message=msg)
