"""
iios/knowledge/governance/quality_exceptions.py
================================================
Exception hierarchy for the Knowledge Quality Engine.
"""

from __future__ import annotations

from ..knowledge_exceptions import KnowledgeError

__all__ = [
    "QualityError",
    "QualityValidationError",
    "QualityScoreError",
    "QualityEngineError",
    "QualityMonitorError",
    "QualityThresholdError",
    "QualityViolationError",
    "QualityRegistryError",
]


class QualityError(KnowledgeError):
    """Base for all quality engine errors."""
    def __init__(self, message: str, code: str = "QE-000") -> None:
        super().__init__(message, code=code)


class QualityValidationError(QualityError):
    """Quality validation failed for a record."""
    def __init__(self, message: str, violations: list[str] | None = None,
                 code: str = "QE-001") -> None:
        super().__init__(message, code=code)
        self.violations: list[str] = violations or []


class QualityScoreError(QualityError):
    """KQI computation failed."""
    def __init__(self, message: str, code: str = "QE-002") -> None:
        super().__init__(message, code=code)


class QualityEngineError(QualityError):
    """Quality engine internal error."""
    def __init__(self, message: str, code: str = "QE-003") -> None:
        super().__init__(message, code=code)


class QualityMonitorError(QualityError):
    """Quality monitor error."""
    def __init__(self, message: str, code: str = "QE-004") -> None:
        super().__init__(message, code=code)


class QualityThresholdError(QualityError):
    """Record does not meet the minimum quality threshold."""
    def __init__(self, message: str, kqi: float = 0.0, threshold: float = 0.0,
                 code: str = "QE-005") -> None:
        super().__init__(message, code=code)
        self.kqi       = kqi
        self.threshold = threshold


class QualityViolationError(QualityError):
    """Critical quality violation was detected."""
    def __init__(self, message: str, code: str = "QE-006") -> None:
        super().__init__(message, code=code)


class QualityRegistryError(QualityError):
    """Quality registry lookup failed."""
    def __init__(self, message: str, code: str = "QE-007") -> None:
        super().__init__(message, code=code)
