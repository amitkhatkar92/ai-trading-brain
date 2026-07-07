"""
iios/observation/validators/validation_constants.py
====================================================
Enumerations, numeric limits, and string constants for the
Observation Validation & Quality Engine.
"""
from __future__ import annotations

from enum import Enum
from typing import Final

__all__ = [
    # Enumerations
    "ValidationSeverity",
    "RuleCategory",
    "ValidationStage",
    "GovernanceAction",
    "ValidationMode",
    "QuarantineReason",
    # Numeric constants
    "MIN_PASSING_SCORE",
    "DEFAULT_RULE_WEIGHT",
    "QUARANTINE_TTL_SECONDS",
    "MAX_RULES_PER_STAGE",
    "DUPLICATE_WINDOW_SECONDS",
    "DEFAULT_TRUST_SCORE",
    "DEFAULT_VALIDATION_TIMEOUT_S",
    "MAX_VALIDATION_HISTORY",
    "MAX_QUARANTINE_SIZE",
    "MIN_QUALITY_THRESHOLD",
    "MAX_CONTENT_SIZE_BYTES",
    "FUTURE_TOLERANCE_SECONDS",
    # String constants
    "VALIDATION_NAMESPACE",
    "SYSTEM_VALIDATOR",
]


# ── Severity ──────────────────────────────────────────────────────────────────

class ValidationSeverity(str, Enum):
    """How serious a rule violation is."""
    CRITICAL = "critical"  # hard fail — observation must be rejected
    HIGH     = "high"      # fail in STRICT mode
    MEDIUM   = "medium"    # warning — escalate in STRICT mode
    LOW      = "low"       # advisory — never fails
    INFO     = "info"      # informational note only


# ── Rule categories ───────────────────────────────────────────────────────────

class RuleCategory(str, Enum):
    """Semantic category of a validation rule."""
    SCHEMA       = "schema"
    FIELD        = "field"
    TYPE         = "type"
    RANGE        = "range"
    DOMAIN       = "domain"
    TIMESTAMP    = "timestamp"
    SOURCE       = "source"
    IDENTIFIER   = "identifier"
    DUPLICATE    = "duplicate"
    RELATIONSHIP = "relationship"
    ONTOLOGY     = "ontology"
    BUSINESS     = "business"


# ── Pipeline stages ───────────────────────────────────────────────────────────

class ValidationStage(str, Enum):
    """Ordered stages in the validation pipeline."""
    PRE           = "pre"
    NORMALISATION = "normalisation"
    ENRICHMENT    = "enrichment"
    BUSINESS      = "business"
    POST          = "post"

    @property
    def order(self) -> int:
        return {
            "pre": 0, "normalisation": 1, "enrichment": 2,
            "business": 3, "post": 4,
        }[self.value]


# ── Governance actions ────────────────────────────────────────────────────────

class GovernanceAction(str, Enum):
    """Decision taken by the governance layer."""
    APPROVE    = "approve"    # passes — proceed to next pipeline stage
    REJECT     = "reject"     # hard fail — discard immediately
    QUARANTINE = "quarantine" # hold for review
    ESCALATE   = "escalate"   # route to human reviewer
    FLAG       = "flag"       # mark for monitoring; continue processing
    SUPPRESS   = "suppress"   # silently drop (e.g. exact duplicate)


# ── Validation modes ──────────────────────────────────────────────────────────

class ValidationMode(str, Enum):
    """How strictly violations are treated."""
    STRICT   = "strict"    # fail on CRITICAL + HIGH; warning on MEDIUM
    LENIENT  = "lenient"   # fail only on CRITICAL violations
    ADVISORY = "advisory"  # never fail; emit warnings only


# ── Quarantine reasons ────────────────────────────────────────────────────────

class QuarantineReason(str, Enum):
    """Why an observation was placed in quarantine."""
    DUPLICATE        = "duplicate"
    LOW_QUALITY      = "low_quality"
    POLICY_VIOLATION = "policy_violation"
    MANUAL_HOLD      = "manual_hold"
    CONFLICT         = "conflict"
    SUSPICIOUS       = "suspicious"
    PENDING_REVIEW   = "pending_review"


# ── Numeric constants ─────────────────────────────────────────────────────────

MIN_PASSING_SCORE:            Final[float] = 0.60
DEFAULT_RULE_WEIGHT:          Final[float] = 1.0
QUARANTINE_TTL_SECONDS:       Final[float] = 86_400.0
MAX_RULES_PER_STAGE:          Final[int]   = 100
DUPLICATE_WINDOW_SECONDS:     Final[float] = 300.0
DEFAULT_TRUST_SCORE:          Final[float] = 0.75
DEFAULT_VALIDATION_TIMEOUT_S: Final[float] = 5.0
MAX_VALIDATION_HISTORY:       Final[int]   = 1_000
MAX_QUARANTINE_SIZE:          Final[int]   = 10_000
MIN_QUALITY_THRESHOLD:        Final[float] = 0.30
MAX_CONTENT_SIZE_BYTES:       Final[int]   = 1_048_576   # 1 MB
FUTURE_TOLERANCE_SECONDS:     Final[float] = 60.0         # allow up to 60 s clock skew

# ── String constants ──────────────────────────────────────────────────────────

VALIDATION_NAMESPACE: Final[str] = "iios.validation"
SYSTEM_VALIDATOR:     Final[str] = "iios:validator:system"
