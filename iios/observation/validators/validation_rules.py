"""
iios/observation/validators/validation_rules.py
================================================
Built-in validation rules for the Observation Validation Engine.

Architecture
------------
Every rule is a subclass of ``ValidationRule`` and implements
``evaluate(obs) -> RuleResult``.

Rules are grouped by:
  - ``RuleCategory``   — semantic domain (SCHEMA, FIELD, TYPE, …)
  - ``ValidationStage`` — which pipeline stage runs the rule

Severity determines whether a violation causes REJECT or WARNING.

Built-in rules
--------------
PRE stage (structure & identity):
  IdentityRule, ContentNotNullRule, DeletedRule, ExpiryRule

NORMALISATION stage (format & type):
  TypeNotUnknownRule, SchemaVersionRule, ConfidenceRangeRule,
  TimestampNotFutureRule, TimestampPositiveRule

ENRICHMENT stage (context & completeness):
  TitleNotEmptyRule, SourceNotUnknownRule, InstrumentPresentRule,
  ContentSizeRule

BUSINESS stage (semantic):
  PriorityValidRule, DomainValidRule, RelationshipIdsFormatRule

POST stage (integrity):
  ChecksumIntegrityRule
"""
from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from ..observation_constants import (
    OBSERVATION_SCHEMA_VERSION,
    ObservationDomain,
    ObservationPriority,
    ObservationSource,
    ObservationType,
)
from ..models.observation import Observation
from .validation_constants import (
    DEFAULT_RULE_WEIGHT,
    FUTURE_TOLERANCE_SECONDS,
    MAX_CONTENT_SIZE_BYTES,
    RuleCategory,
    ValidationSeverity,
    ValidationStage,
)

__all__ = [
    "RuleResult",
    "ValidationRule",
    # PRE
    "IdentityRule",
    "ContentNotNullRule",
    "DeletedRule",
    "ExpiryRule",
    # NORMALISATION
    "TypeNotUnknownRule",
    "SchemaVersionRule",
    "ConfidenceRangeRule",
    "TimestampNotFutureRule",
    "TimestampPositiveRule",
    # ENRICHMENT
    "TitleNotEmptyRule",
    "SourceNotUnknownRule",
    "InstrumentPresentRule",
    "ContentSizeRule",
    # BUSINESS
    "PriorityValidRule",
    "DomainValidRule",
    "RelationshipIdsFormatRule",
    # POST
    "ChecksumIntegrityRule",
    # Helpers
    "DEFAULT_RULES",
]


# ── Result ────────────────────────────────────────────────────────────────────

@dataclass
class RuleResult:
    """Outcome of a single rule evaluation."""
    rule_name:   str
    category:    RuleCategory
    stage:       ValidationStage
    severity:    ValidationSeverity
    passed:      bool
    message:     str             = ""
    detail:      str             = ""
    duration_ms: float           = 0.0

    @property
    def is_violation(self) -> bool:
        return not self.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule":       self.rule_name,
            "category":   self.category.value,
            "stage":      self.stage.value,
            "severity":   self.severity.value,
            "passed":     self.passed,
            "message":    self.message,
            "detail":     self.detail,
            "duration_ms": round(self.duration_ms, 3),
        }


# ── Abstract base ─────────────────────────────────────────────────────────────

class ValidationRule(ABC):
    """Base class for all validation rules."""

    name:     str
    category: RuleCategory
    stage:    ValidationStage
    severity: ValidationSeverity
    weight:   float
    enabled:  bool
    description: str

    def __init__(
        self,
        name:        str,
        category:    RuleCategory,
        stage:       ValidationStage,
        severity:    ValidationSeverity    = ValidationSeverity.HIGH,
        weight:      float                  = DEFAULT_RULE_WEIGHT,
        enabled:     bool                   = True,
        description: str                    = "",
    ) -> None:
        self.name        = name
        self.category    = category
        self.stage       = stage
        self.severity    = severity
        self.weight      = weight
        self.enabled     = enabled
        self.description = description

    def evaluate(self, obs: Observation) -> RuleResult:
        """Evaluate rule against *obs*.  Wraps ``_check`` with timing."""
        t0 = time.perf_counter()
        passed, message, detail = self._check(obs)
        duration_ms = (time.perf_counter() - t0) * 1_000.0
        return RuleResult(
            rule_name   = self.name,
            category    = self.category,
            stage       = self.stage,
            severity    = self.severity,
            passed      = passed,
            message     = message,
            detail      = detail,
            duration_ms = duration_ms,
        )

    @abstractmethod
    def _check(self, obs: Observation) -> tuple[bool, str, str]:
        """Return ``(passed, message, detail)``."""

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name!r} severity={self.severity.value!r}>"


# ── PRE stage ─────────────────────────────────────────────────────────────────

class IdentityRule(ValidationRule):
    """Observation must have a non-empty uid."""
    def __init__(self) -> None:
        super().__init__(
            name="identity.uid_present",
            category=RuleCategory.IDENTIFIER,
            stage=ValidationStage.PRE,
            severity=ValidationSeverity.CRITICAL,
            description="obs_id.uid must be a non-empty string",
        )

    def _check(self, obs: Observation) -> tuple[bool, str, str]:
        if not obs.uid:
            return False, "Identity missing: obs_id.uid is empty", ""
        return True, "Identity present", ""


class ContentNotNullRule(ValidationRule):
    """Observation content must not be None."""
    def __init__(self) -> None:
        super().__init__(
            name="content.not_null",
            category=RuleCategory.FIELD,
            stage=ValidationStage.PRE,
            severity=ValidationSeverity.CRITICAL,
            description="content payload must not be None",
        )

    def _check(self, obs: Observation) -> tuple[bool, str, str]:
        if obs.content is None:
            return False, "content is None — observation has no payload", ""
        return True, "Content present", ""


class DeletedRule(ValidationRule):
    """A soft-deleted observation must not be re-processed."""
    def __init__(self) -> None:
        super().__init__(
            name="lifecycle.not_deleted",
            category=RuleCategory.FIELD,
            stage=ValidationStage.PRE,
            severity=ValidationSeverity.CRITICAL,
            description="Soft-deleted observations cannot be re-processed",
        )

    def _check(self, obs: Observation) -> tuple[bool, str, str]:
        if obs.is_deleted:
            return False, "Observation is soft-deleted — cannot be reprocessed", ""
        return True, "Not deleted", ""


class ExpiryRule(ValidationRule):
    """Observation must not already be expired on ingestion."""
    def __init__(self) -> None:
        super().__init__(
            name="lifecycle.not_expired",
            category=RuleCategory.TIMESTAMP,
            stage=ValidationStage.PRE,
            severity=ValidationSeverity.CRITICAL,
            description="Observation must not have expired before entering pipeline",
        )

    def _check(self, obs: Observation) -> tuple[bool, str, str]:
        if obs.metadata.is_expired:
            return False, "Observation has already expired", (
                f"expires_at={obs.metadata.expires_at}, now={time.time():.1f}"
            )
        return True, "Not expired", ""


# ── NORMALISATION stage ───────────────────────────────────────────────────────

class TypeNotUnknownRule(ValidationRule):
    """obs_type should not be UNKNOWN (warning, not failure by default)."""
    def __init__(self) -> None:
        super().__init__(
            name="type.not_unknown",
            category=RuleCategory.TYPE,
            stage=ValidationStage.NORMALISATION,
            severity=ValidationSeverity.MEDIUM,
            description="obs_type should be a known type for correct routing",
        )

    def _check(self, obs: Observation) -> tuple[bool, str, str]:
        if obs.obs_type == ObservationType.UNKNOWN:
            return False, "obs_type is UNKNOWN — classification will infer type", ""
        return True, f"obs_type={obs.obs_type.value}", ""


class SchemaVersionRule(ValidationRule):
    """Schema version must be present."""
    def __init__(self) -> None:
        super().__init__(
            name="schema.version_present",
            category=RuleCategory.SCHEMA,
            stage=ValidationStage.NORMALISATION,
            severity=ValidationSeverity.LOW,
            description="schema_version must be set",
        )

    def _check(self, obs: Observation) -> tuple[bool, str, str]:
        if not obs.schema_version:
            return False, "schema_version is empty", ""
        return True, f"schema_version={obs.schema_version}", ""


class ConfidenceRangeRule(ValidationRule):
    """Confidence must be in [0.0, 1.0]."""
    def __init__(self) -> None:
        super().__init__(
            name="range.confidence",
            category=RuleCategory.RANGE,
            stage=ValidationStage.NORMALISATION,
            severity=ValidationSeverity.HIGH,
            description="metadata.confidence must be in [0.0, 1.0]",
        )

    def _check(self, obs: Observation) -> tuple[bool, str, str]:
        c = obs.metadata.confidence
        if not (0.0 <= c <= 1.0):
            return False, f"confidence={c!r} out of [0.0, 1.0]", ""
        return True, f"confidence={c:.3f}", ""


class TimestampNotFutureRule(ValidationRule):
    """created_at must not be in the future (allow small clock skew)."""
    def __init__(self) -> None:
        super().__init__(
            name="timestamp.not_future",
            category=RuleCategory.TIMESTAMP,
            stage=ValidationStage.NORMALISATION,
            severity=ValidationSeverity.MEDIUM,
            description=f"created_at must not be more than {FUTURE_TOLERANCE_SECONDS}s in the future",
        )

    def _check(self, obs: Observation) -> tuple[bool, str, str]:
        skew = obs.created_at - time.time()
        if skew > FUTURE_TOLERANCE_SECONDS:
            return False, f"created_at is {skew:.1f}s in the future", ""
        return True, "Timestamp not in future", ""


class TimestampPositiveRule(ValidationRule):
    """created_at must be a positive unix timestamp."""
    def __init__(self) -> None:
        super().__init__(
            name="timestamp.positive",
            category=RuleCategory.TIMESTAMP,
            stage=ValidationStage.NORMALISATION,
            severity=ValidationSeverity.HIGH,
            description="created_at must be a positive Unix timestamp",
        )

    def _check(self, obs: Observation) -> tuple[bool, str, str]:
        if obs.created_at <= 0:
            return False, f"created_at={obs.created_at!r} is not a valid timestamp", ""
        return True, f"created_at={obs.created_at:.3f}", ""


# ── ENRICHMENT stage ──────────────────────────────────────────────────────────

class TitleNotEmptyRule(ValidationRule):
    """Title should not be empty (advisory)."""
    def __init__(self) -> None:
        super().__init__(
            name="field.title_present",
            category=RuleCategory.FIELD,
            stage=ValidationStage.ENRICHMENT,
            severity=ValidationSeverity.LOW,
            description="title should not be empty",
        )

    def _check(self, obs: Observation) -> tuple[bool, str, str]:
        if not obs.title or not obs.title.strip():
            return False, "title is empty — observation is untitled", ""
        return True, "Title present", ""


class SourceNotUnknownRule(ValidationRule):
    """Source should not be UNKNOWN (advisory)."""
    def __init__(self) -> None:
        super().__init__(
            name="source.not_unknown",
            category=RuleCategory.SOURCE,
            stage=ValidationStage.ENRICHMENT,
            severity=ValidationSeverity.MEDIUM,
            description="source_info.source should not be UNKNOWN",
        )

    def _check(self, obs: Observation) -> tuple[bool, str, str]:
        if obs.source_info.source == ObservationSource.UNKNOWN:
            return False, "source_info.source is UNKNOWN — provenance unknown", ""
        return True, f"source={obs.source_info.source.value}", ""


class InstrumentPresentRule(ValidationRule):
    """MARKET_DATA observations should have an instrument symbol."""
    def __init__(self) -> None:
        super().__init__(
            name="domain.instrument_present",
            category=RuleCategory.DOMAIN,
            stage=ValidationStage.ENRICHMENT,
            severity=ValidationSeverity.LOW,
            description="Market data observations should have source_info.instrument set",
        )

    def _check(self, obs: Observation) -> tuple[bool, str, str]:
        if obs.obs_type == ObservationType.MARKET_DATA and not obs.source_info.instrument:
            return False, "MARKET_DATA observation has no instrument symbol", ""
        return True, "Instrument check passed", ""


class ContentSizeRule(ValidationRule):
    """Content must not exceed maximum allowed byte size."""
    def __init__(self, max_bytes: int = MAX_CONTENT_SIZE_BYTES) -> None:
        super().__init__(
            name="content.size_within_limit",
            category=RuleCategory.SCHEMA,
            stage=ValidationStage.ENRICHMENT,
            severity=ValidationSeverity.HIGH,
            description=f"Content must not exceed {max_bytes} bytes",
        )
        self._max_bytes = max_bytes

    def _check(self, obs: Observation) -> tuple[bool, str, str]:
        if obs.content is None:
            return True, "No content", ""
        size = len(str(obs.content).encode("utf-8", errors="replace"))
        if size > self._max_bytes:
            return False, f"Content size {size} bytes exceeds limit {self._max_bytes}", ""
        return True, f"Content size {size} bytes within limit", ""


# ── BUSINESS stage ────────────────────────────────────────────────────────────

class PriorityValidRule(ValidationRule):
    """Priority must be a valid ObservationPriority value."""
    def __init__(self) -> None:
        super().__init__(
            name="business.priority_valid",
            category=RuleCategory.BUSINESS,
            stage=ValidationStage.BUSINESS,
            severity=ValidationSeverity.LOW,
            description="metadata.priority must be a valid ObservationPriority",
        )
        self._valid = {p.value for p in ObservationPriority}

    def _check(self, obs: Observation) -> tuple[bool, str, str]:
        if obs.metadata.priority.value not in self._valid:
            return False, f"Invalid priority={obs.metadata.priority!r}", ""
        return True, f"priority={obs.metadata.priority.value}", ""


class DomainValidRule(ValidationRule):
    """Domain must be a valid ObservationDomain value."""
    def __init__(self) -> None:
        super().__init__(
            name="business.domain_valid",
            category=RuleCategory.DOMAIN,
            stage=ValidationStage.BUSINESS,
            severity=ValidationSeverity.LOW,
            description="metadata.domain must be a valid ObservationDomain",
        )
        self._valid = {d.value for d in ObservationDomain}

    def _check(self, obs: Observation) -> tuple[bool, str, str]:
        if obs.metadata.domain.value not in self._valid:
            return False, f"Invalid domain={obs.metadata.domain!r}", ""
        return True, f"domain={obs.metadata.domain.value}", ""


class RelationshipIdsFormatRule(ValidationRule):
    """related_obs_ids items should look like valid observation IDs."""
    def __init__(self) -> None:
        super().__init__(
            name="relationship.ids_format",
            category=RuleCategory.RELATIONSHIP,
            stage=ValidationStage.BUSINESS,
            severity=ValidationSeverity.LOW,
            description="related_obs_ids must contain non-empty strings",
        )

    def _check(self, obs: Observation) -> tuple[bool, str, str]:
        bad = [r for r in obs.related_obs_ids if not isinstance(r, str) or not r.strip()]
        if bad:
            return False, f"{len(bad)} related_obs_ids are empty or invalid", ""
        return True, f"{len(obs.related_obs_ids)} related ids checked", ""


# ── POST stage ────────────────────────────────────────────────────────────────

class ChecksumIntegrityRule(ValidationRule):
    """Recompute checksum and verify it matches the stored value."""
    def __init__(self) -> None:
        super().__init__(
            name="integrity.checksum",
            category=RuleCategory.SCHEMA,
            stage=ValidationStage.POST,
            severity=ValidationSeverity.HIGH,
            description="Recompute content checksum and compare to stored value",
        )

    def _check(self, obs: Observation) -> tuple[bool, str, str]:
        if obs.content is None or not obs.checksum:
            return True, "Skipped (no content or no checksum)", ""
        raw      = str(obs.content).encode("utf-8", errors="replace")
        computed = hashlib.md5(raw, usedforsecurity=False).hexdigest()
        if computed != obs.checksum:
            return False, "Checksum mismatch — content may have been tampered with", (
                f"stored={obs.checksum[:8]}…, computed={computed[:8]}…"
            )
        return True, "Checksum verified", ""


# ── Default rule set ──────────────────────────────────────────────────────────

def DEFAULT_RULES() -> list[ValidationRule]:
    """Return a fresh list of all built-in rules."""
    return [
        # PRE
        IdentityRule(),
        ContentNotNullRule(),
        DeletedRule(),
        ExpiryRule(),
        # NORMALISATION
        TypeNotUnknownRule(),
        SchemaVersionRule(),
        ConfidenceRangeRule(),
        TimestampNotFutureRule(),
        TimestampPositiveRule(),
        # ENRICHMENT
        TitleNotEmptyRule(),
        SourceNotUnknownRule(),
        InstrumentPresentRule(),
        ContentSizeRule(),
        # BUSINESS
        PriorityValidRule(),
        DomainValidRule(),
        RelationshipIdsFormatRule(),
        # POST
        ChecksumIntegrityRule(),
    ]
