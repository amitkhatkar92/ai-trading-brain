"""
iios/observation/validators/validation_exceptions.py
=====================================================
Exception hierarchy for the Observation Validation & Quality Engine.

All exceptions derive from ValidationError → ObservationError.
Each carries a machine-readable ``code`` for structured logging.
"""
from __future__ import annotations

from ..observation_exceptions import ObservationError

__all__ = [
    "ValidationError",
    "ValidationRuleError",
    "ValidationPipelineError",
    "ValidationRegistryError",
    "ValidationTimeoutError",
    "ValidationQuarantineError",
    "ValidationGovernanceError",
    "DuplicateObservationError",
    "ConflictingObservationError",
    "ValidationNotInitializedError",
    "QualityError",
    "QualityAssessmentError",
    "QualityEngineError",
    "QualityThresholdError",
]


class ValidationError(ObservationError):
    """Base for all validation & quality engine errors."""
    def __init__(self, message: str, code: str = "VAL-000") -> None:
        super().__init__(message, code=code)


class ValidationRuleError(ValidationError):
    """A validation rule failed to execute (not a violation — a runtime error)."""
    def __init__(self, message: str, rule_name: str = "", code: str = "VAL-010") -> None:
        super().__init__(message, code=code)
        self.rule_name = rule_name


class ValidationPipelineError(ValidationError):
    """The validation pipeline encountered an unrecoverable error."""
    def __init__(self, message: str, stage: str = "", code: str = "VAL-020") -> None:
        super().__init__(message, code=code)
        self.stage = stage


class ValidationRegistryError(ValidationError):
    """Rule registry operation failed (e.g. duplicate name, missing rule)."""
    def __init__(self, message: str, code: str = "VAL-030") -> None:
        super().__init__(message, code=code)


class ValidationTimeoutError(ValidationError):
    """Validation did not complete within the allowed time budget."""
    def __init__(self, message: str, timeout_s: float = 0.0, code: str = "VAL-040") -> None:
        super().__init__(message, code=code)
        self.timeout_s = timeout_s


class ValidationQuarantineError(ValidationError):
    """An observation could not be added to the quarantine queue (e.g. queue full)."""
    def __init__(self, message: str, obs_id: str = "", code: str = "VAL-050") -> None:
        super().__init__(message, code=code)
        self.obs_id = obs_id


class ValidationGovernanceError(ValidationError):
    """Governance policy enforcement encountered an error."""
    def __init__(self, message: str, code: str = "VAL-060") -> None:
        super().__init__(message, code=code)


class DuplicateObservationError(ValidationError):
    """An exact or near-duplicate observation was detected."""
    def __init__(
        self,
        message:         str,
        original_id:     str = "",
        duplicate_hash:  str = "",
        code:            str = "VAL-070",
    ) -> None:
        super().__init__(message, code=code)
        self.original_id    = original_id
        self.duplicate_hash = duplicate_hash


class ConflictingObservationError(ValidationError):
    """A conflicting observation with the same identity but different content was found."""
    def __init__(self, message: str, conflicting_id: str = "", code: str = "VAL-080") -> None:
        super().__init__(message, code=code)
        self.conflicting_id = conflicting_id


class ValidationNotInitializedError(ValidationError):
    """Validation engine or manager was used before being initialised."""
    def __init__(self, message: str = "Validation engine not initialised", code: str = "VAL-090") -> None:
        super().__init__(message, code=code)


# ── Quality exceptions ────────────────────────────────────────────────────────

class QualityError(ValidationError):
    """Base for quality engine errors."""
    def __init__(self, message: str, code: str = "QUA-000") -> None:
        super().__init__(message, code=code)


class QualityAssessmentError(QualityError):
    """A quality dimension assessor encountered an error."""
    def __init__(self, message: str, dimension: str = "", code: str = "QUA-010") -> None:
        super().__init__(message, code=code)
        self.dimension = dimension


class QualityEngineError(QualityError):
    """Quality engine internal error."""
    def __init__(self, message: str, code: str = "QUA-020") -> None:
        super().__init__(message, code=code)


class QualityThresholdError(QualityError):
    """An observation fell below the minimum quality threshold and was rejected."""
    def __init__(
        self,
        message:   str,
        oqi:       float = 0.0,
        threshold: float = 0.0,
        code:      str   = "QUA-030",
    ) -> None:
        super().__init__(message, code=code)
        self.oqi       = oqi
        self.threshold = threshold
