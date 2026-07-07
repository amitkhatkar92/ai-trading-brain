"""
iios/observation/collectors/collector_exceptions.py
====================================================
Exception hierarchy for the IIOS Observation Collection Framework.
All exceptions derive from CollectorError.
"""
from __future__ import annotations

from typing import Optional

__all__ = [
    "CollectorError",
    "CollectorConfigError",
    "CollectorAuthError",
    "CollectorConnectionError",
    "CollectorTimeoutError",
    "CollectorRetryExhaustedError",
    "CollectorCircuitOpenError",
    "CollectorRateLimitError",
    "CollectorValidationError",
    "CollectorScheduleError",
    "CollectorExecutionError",
    "CollectorNotFoundError",
    "CollectorAlreadyRegisteredError",
    "CollectorShutdownError",
    "CollectorNormalisationError",
    "CollectorCheckpointError",
]


class CollectorError(Exception):
    """Base class for all IIOS Collector Framework errors."""

    def __init__(
        self,
        message:        str,
        code:           str = "COL-000",
        collector_name: str = "",
    ) -> None:
        super().__init__(message)
        self.code           = code
        self.collector_name = collector_name


class CollectorConfigError(CollectorError):
    """Raised when collector configuration is invalid."""
    def __init__(self, message: str, collector_name: str = "") -> None:
        super().__init__(message, code="COL-010", collector_name=collector_name)


class CollectorAuthError(CollectorError):
    """Raised when authentication to a data source fails."""
    def __init__(self, message: str, collector_name: str = "") -> None:
        super().__init__(message, code="COL-020", collector_name=collector_name)


class CollectorConnectionError(CollectorError):
    """Raised when connection to a data source fails."""
    def __init__(self, message: str, collector_name: str = "") -> None:
        super().__init__(message, code="COL-030", collector_name=collector_name)


class CollectorTimeoutError(CollectorError):
    """Raised when a collection operation exceeds its timeout."""
    def __init__(
        self,
        message:        str,
        collector_name: str   = "",
        timeout_s:      float = 0.0,
    ) -> None:
        super().__init__(message, code="COL-040", collector_name=collector_name)
        self.timeout_s = timeout_s


class CollectorRetryExhaustedError(CollectorError):
    """Raised when all retry attempts have been exhausted."""
    def __init__(
        self,
        message:        str,
        collector_name: str = "",
        attempts:       int = 0,
    ) -> None:
        super().__init__(message, code="COL-050", collector_name=collector_name)
        self.attempts = attempts


class CollectorCircuitOpenError(CollectorError):
    """Raised when the circuit breaker is in OPEN state."""
    def __init__(self, message: str, collector_name: str = "") -> None:
        super().__init__(message, code="COL-060", collector_name=collector_name)


class CollectorRateLimitError(CollectorError):
    """Raised when the rate limit is exceeded."""
    def __init__(
        self,
        message:        str,
        collector_name: str   = "",
        retry_after_s:  float = 0.0,
    ) -> None:
        super().__init__(message, code="COL-070", collector_name=collector_name)
        self.retry_after_s = retry_after_s


class CollectorValidationError(CollectorError):
    """Raised when collected data fails validation."""
    def __init__(
        self,
        message:        str,
        collector_name: str           = "",
        violations:     list[str] | None = None,
    ) -> None:
        super().__init__(message, code="COL-080", collector_name=collector_name)
        self.violations: list[str] = violations or []


class CollectorScheduleError(CollectorError):
    """Raised for scheduling failures."""
    def __init__(self, message: str, collector_name: str = "") -> None:
        super().__init__(message, code="COL-090", collector_name=collector_name)


class CollectorExecutionError(CollectorError):
    """Raised for execution failures."""
    def __init__(
        self,
        message:        str,
        collector_name: str           = "",
        cause:          Exception | None = None,
    ) -> None:
        super().__init__(message, code="COL-100", collector_name=collector_name)
        self.cause = cause


class CollectorNotFoundError(CollectorError):
    """Raised when a collector is not found in the registry."""
    def __init__(self, name: str) -> None:
        super().__init__(f"Collector not found: {name!r}", code="COL-110")
        self.name = name


class CollectorAlreadyRegisteredError(CollectorError):
    """Raised when a collector name is registered twice without overwrite."""
    def __init__(self, name: str) -> None:
        super().__init__(f"Collector already registered: {name!r}", code="COL-120")
        self.name = name


class CollectorShutdownError(CollectorError):
    """Raised when an operation is attempted on a stopped collector."""
    def __init__(self, name: str) -> None:
        super().__init__(f"Collector is stopped: {name!r}", code="COL-130")


class CollectorNormalisationError(CollectorError):
    """Raised when normalisation of raw data fails."""
    def __init__(self, message: str, collector_name: str = "") -> None:
        super().__init__(message, code="COL-140", collector_name=collector_name)


class CollectorCheckpointError(CollectorError):
    """Raised when a checkpoint read/write fails."""
    def __init__(self, message: str, collector_name: str = "") -> None:
        super().__init__(message, code="COL-150", collector_name=collector_name)
