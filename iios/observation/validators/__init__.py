"""
iios/observation/validators/__init__.py
=======================================
Public surface of the Observation Validation & Quality Engine.
"""
from __future__ import annotations

# ── Legacy simple validator (kept for backward compat) ────────────────────────
from .observation_validator import (
    ValidationResult,
    ObservationValidator,
    get_observation_validator,
    reset_observation_validator,
)

# ── Constants & Exceptions ────────────────────────────────────────────────────
from .validation_constants import (
    ValidationSeverity, RuleCategory, ValidationStage,
    GovernanceAction, ValidationMode, QuarantineReason,
    MIN_PASSING_SCORE, DEFAULT_RULE_WEIGHT, QUARANTINE_TTL_SECONDS,
    MAX_RULES_PER_STAGE, DUPLICATE_WINDOW_SECONDS, DEFAULT_TRUST_SCORE,
    VALIDATION_NAMESPACE, SYSTEM_VALIDATOR,
)
from .validation_exceptions import (
    ValidationError, ValidationRuleError, ValidationPipelineError,
    ValidationRegistryError, ValidationTimeoutError,
    ValidationQuarantineError, ValidationGovernanceError,
    DuplicateObservationError, ConflictingObservationError,
    ValidationNotInitializedError,
    QualityError, QualityAssessmentError, QualityEngineError, QualityThresholdError,
)

# ── Rules ─────────────────────────────────────────────────────────────────────
from .validation_rules import (
    RuleResult, ValidationRule,
    IdentityRule, ContentNotNullRule, DeletedRule, ExpiryRule,
    TypeNotUnknownRule, SchemaVersionRule, ConfidenceRangeRule,
    TimestampNotFutureRule, TimestampPositiveRule,
    TitleNotEmptyRule, SourceNotUnknownRule, InstrumentPresentRule, ContentSizeRule,
    PriorityValidRule, DomainValidRule, RelationshipIdsFormatRule,
    ChecksumIntegrityRule, DEFAULT_RULES,
)

# ── Registry ──────────────────────────────────────────────────────────────────
from .validation_registry import (
    RuleRegistry, get_rule_registry, reset_rule_registry,
)

# ── Context ───────────────────────────────────────────────────────────────────
from .validation_context import (
    ValidationContext, get_validation_context, reset_validation_context,
    validation_operation, current_obs_id, current_stage, current_run_id,
)

# ── Pipeline ──────────────────────────────────────────────────────────────────
from .validation_pipeline import (
    StageResult, PipelineResult, ValidationPipeline,
)

# ── Engine ────────────────────────────────────────────────────────────────────
from .validation_engine import (
    ValidationReport, ValidationEngine,
    get_validation_engine, reset_validation_engine,
)

# ── Manager (governance) ─────────────────────────────────────────────────────
from .validation_manager import (
    GovernanceDecision, QuarantineEntry, QuarantineQueue,
    DuplicateDetector, ValidationManager,
    get_validation_manager, reset_validation_manager,
)
