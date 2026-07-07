"""
iios/observation/validators/observation_validator.py
=====================================================
ObservationValidator — validates raw observations before they proceed
through the classification/enrichment pipeline.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from ..observation_constants import (
    DEFAULT_CONFIDENCE,
    SYSTEM_OBSERVER,
    ValidationOutcome,
)
from ..observation_exceptions import ObservationValidationError
from ..models.observation import Observation

__all__ = [
    "ValidationResult",
    "ObservationValidator",
    "get_observation_validator",
    "reset_observation_validator",
]

import threading

_LOG  = logging.getLogger("iios.observation.validator")
_lock = threading.Lock()
_validator: "ObservationValidator | None" = None


@dataclass
class ValidationResult:
    """Result of running an observation through the validator."""

    outcome:     ValidationOutcome  = ValidationOutcome.PASS
    violations:  list[str]          = field(default_factory=list)
    warnings:    list[str]          = field(default_factory=list)
    checked_at:  float              = field(default_factory=time.time)
    duration_ms: float              = 0.0

    @property
    def passed(self) -> bool:
        return self.outcome == ValidationOutcome.PASS

    @property
    def failed(self) -> bool:
        return self.outcome == ValidationOutcome.FAIL

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome":     self.outcome.value,
            "violations":  list(self.violations),
            "warnings":    list(self.warnings),
            "checked_at":  self.checked_at,
            "duration_ms": self.duration_ms,
        }


class ObservationValidator:
    """Validates structural and semantic correctness of observations.

    Checks performed:
    1. obs_id  — must be present
    2. content — must not be None
    3. obs_type — must not be UNKNOWN (warning, not failure)
    4. title   — should not be empty (warning)
    5. TTL     — must not already be expired
    6. confidence — must be within [0, 1]
    7. Deleted check — cannot reprocess a deleted observation
    """

    def validate(
        self,
        obs:    Observation,
        strict: bool = False,
    ) -> ValidationResult:
        t0 = time.perf_counter()
        violations: list[str] = []
        warnings:   list[str] = []

        # 1 — Identity
        if not obs.uid:
            violations.append("obs_id: uid is empty")

        # 2 — Content
        if obs.content is None:
            violations.append("content: payload is None — observation has no data")

        # 3 — Type
        from ..observation_constants import ObservationType
        if obs.obs_type == ObservationType.UNKNOWN:
            warnings.append("obs_type: UNKNOWN — classification will infer type")

        # 4 — Title
        if not obs.title:
            warnings.append("title: empty — observation is untitled")

        # 5 — TTL / expiry
        if obs.metadata.is_expired:
            violations.append("observation has already expired before ingestion")

        # 6 — Confidence range
        if not (0.0 <= obs.metadata.confidence <= 1.0):
            violations.append(
                f"confidence {obs.metadata.confidence!r} out of range [0.0, 1.0]"
            )

        # 7 — Deleted
        if obs.is_deleted:
            violations.append("observation is already deleted — cannot be reprocessed")

        outcome = ValidationOutcome.FAIL if violations else ValidationOutcome.PASS
        if not violations and warnings and strict:
            outcome = ValidationOutcome.WARNING

        duration_ms = (time.perf_counter() - t0) * 1_000.0
        result = ValidationResult(
            outcome     = outcome,
            violations  = violations,
            warnings    = warnings,
            duration_ms = duration_ms,
        )

        if strict and violations:
            raise ObservationValidationError(
                f"Observation '{obs.uid[:8]}' failed validation",
                violations = violations,
                code       = "OBS-003",
            )

        return result

    def validate_batch(
        self, observations: list[Observation]
    ) -> dict[str, ValidationResult]:
        return {obs.id: self.validate(obs) for obs in observations}


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_observation_validator() -> ObservationValidator:
    global _validator
    if _validator is None:
        with _lock:
            if _validator is None:
                _validator = ObservationValidator()
    return _validator


def reset_observation_validator() -> None:
    global _validator
    with _lock:
        _validator = None
