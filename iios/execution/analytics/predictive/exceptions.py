"""
iios/execution/analytics/predictive/exceptions.py
=================================================
Exception hierarchy for the Institutional Predictive Intelligence Framework.

Error codes: PI-000 … PI-008

C8 Execution Analytics & Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Sequence

from iios.common.errors.exceptions import IIOSError


class PredictiveIntelligenceError(IIOSError):
    """Base class for all Predictive Intelligence errors.  Code: PI-000."""

    error_code: str = "PI-000"

    def __init__(self, message: str = "Predictive intelligence error.") -> None:
        super().__init__(message, code=self.error_code)


class PredictiveEngineNotRunningError(PredictiveIntelligenceError):
    """Engine is not running.  Code: PI-001."""

    error_code = "PI-001"

    def __init__(self) -> None:
        super().__init__(
            "PredictiveIntelligenceEngine is not running. Call start() first."
        )


class PredictionRequestNotFoundError(PredictiveIntelligenceError):
    """Prediction request not found.  Code: PI-002."""

    error_code = "PI-002"

    def __init__(self, request_id: str) -> None:
        self.request_id = request_id
        super().__init__(f"Prediction request not found: {request_id!r}")


class PredictionForecastError(PredictiveIntelligenceError):
    """Forecast generation failed.  Code: PI-003."""

    error_code = "PI-003"

    def __init__(
        self,
        message: str = "Forecast generation failed.",
        prediction_type: str = "",
    ) -> None:
        self.prediction_type = prediction_type
        super().__init__(message)


class PredictionValidationError(PredictiveIntelligenceError):
    """Prediction request validation failed.  Code: PI-004."""

    error_code = "PI-004"

    def __init__(
        self,
        errors: Sequence[str] = (),
        message: str = "Prediction validation failed.",
    ) -> None:
        self.errors: tuple[str, ...] = tuple(errors)
        full = f"{message}: {'; '.join(errors)}" if errors else message
        super().__init__(full)


class PredictionModelError(PredictiveIntelligenceError):
    """Forecast model error.  Code: PI-005."""

    error_code = "PI-005"

    def __init__(
        self,
        message: str = "Forecast model error.",
        model_id: str = "",
    ) -> None:
        self.model_id = model_id
        super().__init__(message)


class PredictionConfidenceError(PredictiveIntelligenceError):
    """Confidence scoring failed.  Code: PI-006."""

    error_code = "PI-006"

    def __init__(self, message: str = "Confidence scoring failed.") -> None:
        super().__init__(message)


class PredictionCapacityError(PredictiveIntelligenceError):
    """Capacity estimation failed.  Code: PI-007."""

    error_code = "PI-007"

    def __init__(self, message: str = "Capacity estimation failed.") -> None:
        super().__init__(message)


class PredictionRiskError(PredictiveIntelligenceError):
    """Risk estimation failed.  Code: PI-008."""

    error_code = "PI-008"

    def __init__(self, message: str = "Risk estimation failed.") -> None:
        super().__init__(message)
