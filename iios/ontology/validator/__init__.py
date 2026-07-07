"""
iios/ontology/validator/__init__.py
=====================================
Public API for the IIOS Ontology Validation & Constraint Engine.

Primary entry points:
    get_validation_engine()    — master orchestrator (recommended)
    get_ontology_validator()   — core semantic validator
    get_constraint_manager()   — constraint lifecycle manager
    get_constraint_registry()  — raw constraint store
    get_constraint_engine()    — constraint evaluator
    get_validation_context()   — thread-local context

All singletons expose a matching ``reset_*()`` function for testing.
"""

from __future__ import annotations

# ── Constants ──────────────────────────────────────────────────────────────────
from .validation_constants import (
    BUILTIN_HIER_PREFIX,
    BUILTIN_NS_PREFIX,
    BUILTIN_PROP_PREFIX,
    BUILTIN_REF_PREFIX,
    BUILTIN_REL_PREFIX,
    BUILTIN_TYPE_PREFIX,
    MAX_BATCH_SIZE,
    MAX_HISTORY_PER_TARGET,
    MAX_INHERITANCE_CHECK_DEPTH,
    MAX_PARALLEL_VALIDATORS,
    MAX_VALIDATION_ERRORS,
    SYSTEM_VALIDATOR_ACTOR,
    VALIDATOR_VERSION,
    VALIDATION_TIMEOUT_MS,
    ConstraintType,
    ReferenceKind,
    ValidationMode,
    ValidationPhase,
    ValidationScope,
    ValidationSeverity,
    max_severity,
    severity_ge,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .validation_exceptions import (
    AliasConflictError,
    BrokenReferenceError,
    BusinessRuleViolationError,
    CardinalityViolationError,
    CircularReferenceError,
    ConstraintRegistryError,
    ConstraintViolationError,
    DataTypeConstraintError,
    DuplicateConstraintError,
    HierarchyValidationError,
    InheritanceDepthError,
    InvalidEndpointError,
    NamespaceConsistencyError,
    ReferentialIntegrityError,
    RequiredFieldError,
    SemanticValidationError,
    UnknownConstraintError,
    UnresolvableAliasError,
    ValidatorError,
    ValidationConfigError,
    ValidationEngineError,
    ValidationModeError,
    ValidationNotInitializedError,
    ValidationTimeoutError,
    VersionCompatibilityError,
    UriFormatError,
)

# ── Results & Reports ────────────────────────────────────────────────────────
from .validation_result import ValidationResult
from .validation_report import ValidationHistory, ValidationReport

# ── Context ───────────────────────────────────────────────────────────────────
from .validation_context import (
    DiagnosticLevel,
    ValidationContext,
    ValidationDiagnostic,
    get_validation_context,
    reset_validation_context,
)

# ── Constraint registry ───────────────────────────────────────────────────────
from .constraint_registry import (
    ConstraintDef,
    ConstraintRegistry,
    get_constraint_registry,
    reset_constraint_registry,
)

# ── Constraint engine ─────────────────────────────────────────────────────────
from .constraint_engine import (
    ConstraintEngine,
    get_constraint_engine,
    reset_constraint_engine,
)

# ── Constraint manager ────────────────────────────────────────────────────────
from .constraint_manager import (
    ConstraintManager,
    get_constraint_manager,
    reset_constraint_manager,
)

# ── Ontology validator ────────────────────────────────────────────────────────
from .ontology_validator import (
    OntologyValidator,
    get_ontology_validator,
    reset_ontology_validator,
)

# ── Validation engine (master) ────────────────────────────────────────────────
from .validation_engine import (
    ValidationEngine,
    get_validation_engine,
    reset_validation_engine,
)

__all__ = [
    # Constants
    "ValidationSeverity",
    "ValidationScope",
    "ConstraintType",
    "ValidationMode",
    "ValidationPhase",
    "ReferenceKind",
    "MAX_VALIDATION_ERRORS",
    "MAX_BATCH_SIZE",
    "VALIDATION_TIMEOUT_MS",
    "MAX_HISTORY_PER_TARGET",
    "MAX_INHERITANCE_CHECK_DEPTH",
    "MAX_PARALLEL_VALIDATORS",
    "VALIDATOR_VERSION",
    "SYSTEM_VALIDATOR_ACTOR",
    "BUILTIN_TYPE_PREFIX",
    "BUILTIN_PROP_PREFIX",
    "BUILTIN_REL_PREFIX",
    "BUILTIN_NS_PREFIX",
    "BUILTIN_HIER_PREFIX",
    "BUILTIN_REF_PREFIX",
    "max_severity",
    "severity_ge",
    # Exceptions
    "ValidatorError",
    "ConstraintViolationError",
    "RequiredFieldError",
    "DataTypeConstraintError",
    "CardinalityViolationError",
    "UriFormatError",
    "AliasConflictError",
    "BusinessRuleViolationError",
    "SemanticValidationError",
    "HierarchyValidationError",
    "InheritanceDepthError",
    "NamespaceConsistencyError",
    "VersionCompatibilityError",
    "ReferentialIntegrityError",
    "BrokenReferenceError",
    "CircularReferenceError",
    "InvalidEndpointError",
    "UnresolvableAliasError",
    "ValidationConfigError",
    "ValidationModeError",
    "ConstraintRegistryError",
    "DuplicateConstraintError",
    "UnknownConstraintError",
    "ValidationEngineError",
    "ValidationTimeoutError",
    "ValidationNotInitializedError",
    # Results & Reports
    "ValidationResult",
    "ValidationReport",
    "ValidationHistory",
    # Context
    "DiagnosticLevel",
    "ValidationContext",
    "ValidationDiagnostic",
    "get_validation_context",
    "reset_validation_context",
    # Constraint registry
    "ConstraintDef",
    "ConstraintRegistry",
    "get_constraint_registry",
    "reset_constraint_registry",
    # Constraint engine
    "ConstraintEngine",
    "get_constraint_engine",
    "reset_constraint_engine",
    # Constraint manager
    "ConstraintManager",
    "get_constraint_manager",
    "reset_constraint_manager",
    # Ontology validator
    "OntologyValidator",
    "get_ontology_validator",
    "reset_ontology_validator",
    # Validation engine
    "ValidationEngine",
    "get_validation_engine",
    "reset_validation_engine",
]
