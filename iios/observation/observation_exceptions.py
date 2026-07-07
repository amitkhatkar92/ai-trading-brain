"""
iios/observation/observation_exceptions.py
==========================================
Exception hierarchy for the IIOS Observation Engine.

All exceptions derive from ObservationError → IIOSError → Exception.
Each has a machine-readable ``code`` attribute for structured logging.
"""

from __future__ import annotations

__all__ = [
    "ObservationError",
    "ObservationNotFoundError",
    "ObservationAlreadyExistsError",
    "ObservationValidationError",
    "ObservationRejectedError",
    "ObservationStorageError",
    "ObservationCacheError",
    "ObservationQueryError",
    "ObservationIdentityError",
    "ObservationLifecycleError",
    "ObservationPipelineError",
    "ObservationCollectorError",
    "ObservationEnrichmentError",
    "ObservationClassificationError",
    "ObservationDuplicateError",
    "ObservationConflictError",
    "ObservationTimeoutError",
    "ObservationCapacityError",
    "ObservationEngineError",
    "ObservationEngineNotInitializedError",
    # Aliases
    "ObservationConfigError",
    "ObservationClassifierError",
    "ObservationEnricherError",
]


class ObservationError(Exception):
    """Base class for all IIOS Observation Engine errors."""

    def __init__(self, message: str, code: str = "OBS-000") -> None:
        super().__init__(message)
        self.code = code

    def __str__(self) -> str:
        return f"[{self.code}] {super().__str__()}"


class ObservationNotFoundError(ObservationError):
    """No observation matches the requested identifier."""
    def __init__(self, message: str, code: str = "OBS-001") -> None:
        super().__init__(message, code=code)


class ObservationAlreadyExistsError(ObservationError):
    """An observation with the same identity already exists."""
    def __init__(self, message: str, code: str = "OBS-002") -> None:
        super().__init__(message, code=code)


class ObservationValidationError(ObservationError):
    """Observation failed one or more validation checks."""

    def __init__(
        self,
        message: str,
        violations: list[str] | None = None,
        code: str = "OBS-003",
    ) -> None:
        super().__init__(message, code=code)
        self.violations: list[str] = violations or []


class ObservationRejectedError(ObservationError):
    """Observation was explicitly rejected by policy or validator."""
    def __init__(self, message: str, reason: str = "", code: str = "OBS-004") -> None:
        super().__init__(message, code=code)
        self.reason = reason


class ObservationStorageError(ObservationError):
    """Persistence layer encountered an error."""
    def __init__(self, message: str, code: str = "OBS-010") -> None:
        super().__init__(message, code=code)


class ObservationCacheError(ObservationError):
    """Cache layer encountered an error."""
    def __init__(self, message: str, code: str = "OBS-011") -> None:
        super().__init__(message, code=code)


class ObservationQueryError(ObservationError):
    """A query against the observation store failed."""
    def __init__(self, message: str, code: str = "OBS-012") -> None:
        super().__init__(message, code=code)


class ObservationIdentityError(ObservationError):
    """ObservationId construction or parsing failed."""
    def __init__(self, message: str, code: str = "OBS-020") -> None:
        super().__init__(message, code=code)


class ObservationLifecycleError(ObservationError):
    """An illegal lifecycle transition was attempted."""
    def __init__(self, message: str, code: str = "OBS-030") -> None:
        super().__init__(message, code=code)


class ObservationPipelineError(ObservationError):
    """The processing pipeline encountered an unrecoverable error."""
    def __init__(self, message: str, stage: str = "", code: str = "OBS-040") -> None:
        super().__init__(message, code=code)
        self.stage = stage


class ObservationCollectorError(ObservationError):
    """A data collector failed to acquire an observation."""
    def __init__(self, message: str, code: str = "OBS-050") -> None:
        super().__init__(message, code=code)


class ObservationEnrichmentError(ObservationError):
    """An enricher failed during processing."""
    def __init__(self, message: str, code: str = "OBS-060") -> None:
        super().__init__(message, code=code)


class ObservationClassificationError(ObservationError):
    """Classification of an observation failed."""
    def __init__(self, message: str, code: str = "OBS-070") -> None:
        super().__init__(message, code=code)


class ObservationDuplicateError(ObservationError):
    """Observation is a duplicate of an existing one."""
    def __init__(
        self,
        message:    str,
        existing_id: str = "",
        code:       str = "OBS-080",
    ) -> None:
        super().__init__(message, code=code)
        self.existing_id = existing_id


class ObservationConflictError(ObservationError):
    """Observation conflicts with existing data."""
    def __init__(self, message: str, code: str = "OBS-081") -> None:
        super().__init__(message, code=code)


class ObservationTimeoutError(ObservationError):
    """Operation timed out."""
    def __init__(self, message: str, code: str = "OBS-090") -> None:
        super().__init__(message, code=code)


class ObservationCapacityError(ObservationError):
    """Storage or processing capacity exceeded."""
    def __init__(self, message: str, code: str = "OBS-091") -> None:
        super().__init__(message, code=code)


class ObservationEngineError(ObservationError):
    """Top-level engine error."""
    def __init__(self, message: str, code: str = "OBS-100") -> None:
        super().__init__(message, code=code)


class ObservationEngineNotInitializedError(ObservationEngineError):
    """Engine used before ``initialize()`` was called."""
    def __init__(self, message: str = "ObservationEngine not initialized", code: str = "OBS-101") -> None:
        super().__init__(message, code=code)


# ── Convenience aliases ───────────────────────────────────────────────────────
ObservationConfigError    = ObservationError          # configuration errors
ObservationClassifierError = ObservationClassificationError   # classifier errors
ObservationEnricherError   = ObservationEnrichmentError       # enricher errors
