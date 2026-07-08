"""
iios/intelligence/forecast/hypothesis_exceptions.py
===================================================
Exception hierarchy for the Hypothesis & Forecast Engine.
Error-code prefix: HFE-
"""
from __future__ import annotations


class HypothesisForecastError(Exception):
    """Base exception for all Hypothesis & Forecast errors.  Code: HFE-000"""
    code = "HFE-000"

    def __init__(self, message: str = "", code: str | None = None) -> None:
        self.code = code or self.__class__.code
        super().__init__(f"[{self.code}] {message}")


# ── Hypothesis errors (HFE-01x) ───────────────────────────────────────────────

class HypothesisError(HypothesisForecastError):
    """Base for hypothesis lifecycle errors.  Code: HFE-010"""
    code = "HFE-010"


class HypothesisNotFoundError(HypothesisError):
    """Hypothesis ID not in registry.  Code: HFE-011"""
    code = "HFE-011"

    def __init__(self, hypothesis_id: str) -> None:
        super().__init__(f"Hypothesis not found: {hypothesis_id!r}")


class HypothesisAlreadyExistsError(HypothesisError):
    """Duplicate hypothesis registration.  Code: HFE-012"""
    code = "HFE-012"

    def __init__(self, hypothesis_id: str) -> None:
        super().__init__(f"Hypothesis already exists: {hypothesis_id!r}")


class HypothesisStateError(HypothesisError):
    """Operation not permitted in current hypothesis state.  Code: HFE-013"""
    code = "HFE-013"

    def __init__(self, hypothesis_id: str, current: str, expected: str) -> None:
        super().__init__(
            f"Hypothesis {hypothesis_id!r} is {current!r}; expected {expected!r}"
        )


class HypothesisExpiredError(HypothesisError):
    """Hypothesis exceeded its TTL.  Code: HFE-014"""
    code = "HFE-014"

    def __init__(self, hypothesis_id: str) -> None:
        super().__init__(f"Hypothesis {hypothesis_id!r} has expired")


# ── Forecast errors (HFE-02x) ─────────────────────────────────────────────────

class ForecastError(HypothesisForecastError):
    """Base for forecast errors.  Code: HFE-020"""
    code = "HFE-020"


class ForecastNotFoundError(ForecastError):
    """Forecast ID not in registry.  Code: HFE-021"""
    code = "HFE-021"

    def __init__(self, forecast_id: str) -> None:
        super().__init__(f"Forecast not found: {forecast_id!r}")


class ForecastModelError(ForecastError):
    """Forecast model failed.  Code: HFE-022"""
    code = "HFE-022"

    def __init__(self, detail: str) -> None:
        super().__init__(f"Forecast model error: {detail}")


class InsufficientDataError(ForecastError):
    """Not enough input data to generate a forecast.  Code: HFE-023"""
    code = "HFE-023"

    def __init__(self, required: int, available: int) -> None:
        super().__init__(
            f"Insufficient data: need {required}, have {available}"
        )


class ForecastExpiredError(ForecastError):
    """Forecast has exceeded its TTL.  Code: HFE-024"""
    code = "HFE-024"

    def __init__(self, forecast_id: str) -> None:
        super().__init__(f"Forecast {forecast_id!r} has expired")


# ── Scenario errors (HFE-03x) ─────────────────────────────────────────────────

class ScenarioError(HypothesisForecastError):
    """Base for scenario analysis errors.  Code: HFE-030"""
    code = "HFE-030"


class ScenarioNotFoundError(ScenarioError):
    """Scenario ID not in registry.  Code: HFE-031"""
    code = "HFE-031"

    def __init__(self, scenario_id: str) -> None:
        super().__init__(f"Scenario not found: {scenario_id!r}")


class ScenarioValidationError(ScenarioError):
    """Scenario failed validation.  Code: HFE-032"""
    code = "HFE-032"

    def __init__(self, scenario_id: str, reason: str) -> None:
        super().__init__(
            f"Scenario {scenario_id!r} validation failed: {reason}"
        )


class InsufficientScenariosError(ScenarioError):
    """Not enough scenarios for comparison.  Code: HFE-033"""
    code = "HFE-033"

    def __init__(self, required: int, available: int) -> None:
        super().__init__(
            f"Insufficient scenarios: need {required}, have {available}"
        )


# ── Probability errors (HFE-04x) ──────────────────────────────────────────────

class ProbabilityError(HypothesisForecastError):
    """Base for probability calculation errors.  Code: HFE-040"""
    code = "HFE-040"


class ProbabilityOutOfRangeError(ProbabilityError):
    """Probability value not in [0, 1].  Code: HFE-041"""
    code = "HFE-041"

    def __init__(self, value: float) -> None:
        super().__init__(f"Probability {value!r} is out of range [0, 1]")


class DistributionError(ProbabilityError):
    """Probability distribution is invalid.  Code: HFE-042"""
    code = "HFE-042"

    def __init__(self, detail: str) -> None:
        super().__init__(f"Distribution error: {detail}")


# ── Evaluation errors (HFE-05x) ───────────────────────────────────────────────

class EvaluationError(HypothesisForecastError):
    """Base for evaluation errors.  Code: HFE-050"""
    code = "HFE-050"


class NoForecastToEvaluateError(EvaluationError):
    """No forecast found for evaluation.  Code: HFE-051"""
    code = "HFE-051"

    def __init__(self, forecast_id: str) -> None:
        super().__init__(f"No forecast to evaluate: {forecast_id!r}")


class EvaluationMetricError(EvaluationError):
    """Metric calculation failed.  Code: HFE-052"""
    code = "HFE-052"

    def __init__(self, metric: str, detail: str) -> None:
        super().__init__(f"Metric {metric!r} calculation failed: {detail}")


# ── Engine errors (HFE-06x) ────────────────────────────────────────────────────

class ForecastEngineError(HypothesisForecastError):
    """Base for top-level engine errors.  Code: HFE-060"""
    code = "HFE-060"


class ForecastEngineNotInitializedError(ForecastEngineError):
    """Engine used before initialize().  Code: HFE-061"""
    code = "HFE-061"

    def __init__(self) -> None:
        super().__init__(
            "Hypothesis engine not initialized; call initialize() first"
        )


class ForecastEngineAlreadyRunningError(ForecastEngineError):
    """Engine.initialize() called while already running.  Code: HFE-062"""
    code = "HFE-062"

    def __init__(self) -> None:
        super().__init__("Hypothesis engine is already running")
