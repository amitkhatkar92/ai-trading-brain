"""
exceptions.py — iios.risk.assessment
======================================
Exception hierarchy for the Risk Assessment & Optimization Framework.

Error-code prefix: RA (Risk Assessment).

C11 Risk Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class RiskAssessmentError(IIOSError):
    """Base exception for the Risk Assessment Framework (RA-000)."""
    error_code: str = "RA-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class RiskAssessmentEngineNotRunningError(RiskAssessmentError):
    """Engine operation attempted before start() (RA-001)."""
    error_code = "RA-001"

    def __init__(self) -> None:
        super().__init__(
            "Risk assessment engine is not running — call start() first",
            code=self.error_code,
        )


class RiskAssessmentNotFoundError(RiskAssessmentError):
    """Referenced assessment not found in the registry (RA-002)."""
    error_code = "RA-002"

    def __init__(self, assessment_id: str) -> None:
        super().__init__(
            f"Assessment not found: {assessment_id!r}",
            code=self.error_code,
        )
        self.assessment_id = assessment_id


class RiskAssessmentValidationError(RiskAssessmentError):
    """Assessment request or result fails validation (RA-003)."""
    error_code = "RA-003"

    def __init__(
        self,
        message: str = "",
        *,
        failed_checks: tuple = (),
        assessment_id: str = "",
    ) -> None:
        detail = f" (assessment_id={assessment_id!r})" if assessment_id else ""
        super().__init__(
            f"Assessment validation failed{detail}: {message}",
            code=self.error_code,
        )
        self.failed_checks = failed_checks
        self.assessment_id = assessment_id


class RiskModelNotFoundError(RiskAssessmentError):
    """Referenced quantitative model not found in the model registry (RA-004)."""
    error_code = "RA-004"

    def __init__(self, model_id: str) -> None:
        super().__init__(
            f"Risk model not found: {model_id!r}",
            code=self.error_code,
        )
        self.model_id = model_id


class RiskCalculationError(RiskAssessmentError):
    """Error during a quantitative risk calculation (RA-005)."""
    error_code = "RA-005"

    def __init__(self, message: str = "", *, engine: str = "") -> None:
        detail = f" (engine={engine!r})" if engine else ""
        super().__init__(
            f"Risk calculation error{detail}: {message}",
            code=self.error_code,
        )
        self.engine = engine


class RiskAssessmentRegistryError(RiskAssessmentError):
    """Registry operation failed (RA-006)."""
    error_code = "RA-006"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Assessment registry error: {message}",
            code=self.error_code,
        )


class RiskAssessmentConfigurationError(RiskAssessmentError):
    """Invalid assessment configuration (RA-007)."""
    error_code = "RA-007"

    def __init__(self, message: str = "", *, field: str = "") -> None:
        detail = f" (field={field!r})" if field else ""
        super().__init__(
            f"Assessment configuration error{detail}: {message}",
            code=self.error_code,
        )
        self.field = field


class RiskOptimizationError(RiskAssessmentError):
    """Error during risk optimization (RA-008)."""
    error_code = "RA-008"

    def __init__(self, message: str = "", *, objective: str = "") -> None:
        detail = f" (objective={objective!r})" if objective else ""
        super().__init__(
            f"Risk optimization error{detail}: {message}",
            code=self.error_code,
        )
        self.objective = objective


class RiskStressTestError(RiskAssessmentError):
    """Error during stress test execution (RA-009)."""
    error_code = "RA-009"

    def __init__(self, message: str = "", *, scenario: str = "") -> None:
        detail = f" (scenario={scenario!r})" if scenario else ""
        super().__init__(
            f"Stress test error{detail}: {message}",
            code=self.error_code,
        )
        self.scenario = scenario


class RiskScenarioError(RiskAssessmentError):
    """Error during scenario analysis (RA-010)."""
    error_code = "RA-010"

    def __init__(self, message: str = "", *, scenario_type: str = "") -> None:
        detail = f" (scenario_type={scenario_type!r})" if scenario_type else ""
        super().__init__(
            f"Scenario analysis error{detail}: {message}",
            code=self.error_code,
        )
        self.scenario_type = scenario_type


class RiskForecastError(RiskAssessmentError):
    """Error during risk forecasting (RA-011)."""
    error_code = "RA-011"

    def __init__(self, message: str = "", *, horizon: str = "") -> None:
        detail = f" (horizon={horizon!r})" if horizon else ""
        super().__init__(
            f"Risk forecast error{detail}: {message}",
            code=self.error_code,
        )
        self.horizon = horizon


class RiskMitigationError(RiskAssessmentError):
    """Error during mitigation plan generation (RA-012)."""
    error_code = "RA-012"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Risk mitigation error: {message}",
            code=self.error_code,
        )


class RiskAssessmentCapacityError(RiskAssessmentError):
    """Registry capacity exhausted (RA-013)."""
    error_code = "RA-013"

    def __init__(self, max_capacity: int) -> None:
        super().__init__(
            f"Assessment registry capacity exhausted (max={max_capacity})",
            code=self.error_code,
        )
        self.max_capacity = max_capacity
