"""
iios/ontology/validator/validation_constants.py
================================================
Enumerations, type aliases, and numeric/string constants for the
IIOS Ontology Validation & Constraint Engine.

Error-code prefix: VAL-
"""

from __future__ import annotations

from enum import Enum
from typing import Final

__all__ = [
    # Enumerations
    "ValidationSeverity",
    "ValidationScope",
    "ConstraintType",
    "ValidationMode",
    "ValidationPhase",
    "ReferenceKind",
    # Numeric constants
    "MAX_VALIDATION_ERRORS",
    "MAX_BATCH_SIZE",
    "VALIDATION_TIMEOUT_MS",
    "MAX_HISTORY_PER_TARGET",
    "MAX_INHERITANCE_CHECK_DEPTH",
    "MAX_PARALLEL_VALIDATORS",
    # String constants
    "VALIDATOR_VERSION",
    "PASS_RESULT",
    "FAIL_RESULT",
    "WARN_RESULT",
    "SYSTEM_VALIDATOR_ACTOR",
    # Built-in constraint ID prefixes
    "BUILTIN_TYPE_PREFIX",
    "BUILTIN_PROP_PREFIX",
    "BUILTIN_REL_PREFIX",
    "BUILTIN_NS_PREFIX",
    "BUILTIN_HIER_PREFIX",
    "BUILTIN_REF_PREFIX",
]


# ── Severity ──────────────────────────────────────────────────────────────────

class ValidationSeverity(str, Enum):
    """Severity level of a validation result."""
    PASS     = "pass"      # Check passed — no issue
    INFO     = "info"      # Informational note
    WARNING  = "warning"   # Non-blocking concern
    ERROR    = "error"     # Policy violation — blocks write by default
    CRITICAL = "critical"  # Structural invariant broken — always blocks


# Ordering helper (higher = more severe)
_SEVERITY_ORDER: dict[str, int] = {
    ValidationSeverity.PASS:     0,
    ValidationSeverity.INFO:     1,
    ValidationSeverity.WARNING:  2,
    ValidationSeverity.ERROR:    3,
    ValidationSeverity.CRITICAL: 4,
}


def severity_ge(a: ValidationSeverity, b: ValidationSeverity) -> bool:
    """Return True if severity *a* is greater than or equal to *b*."""
    return _SEVERITY_ORDER[a] >= _SEVERITY_ORDER[b]


def max_severity(severities: list[ValidationSeverity]) -> ValidationSeverity:
    """Return the highest severity from a list (PASS if empty)."""
    if not severities:
        return ValidationSeverity.PASS
    return max(severities, key=lambda s: _SEVERITY_ORDER[s])


# ── Validation scope ──────────────────────────────────────────────────────────

class ValidationScope(str, Enum):
    """The structural unit being validated."""
    TYPE          = "type"           # OntologyTypeDef
    PROPERTY      = "property"       # OntologyProperty
    RELATIONSHIP  = "relationship"   # OntologyRelationshipDef
    NAMESPACE     = "namespace"      # OntologyNamespace
    DOCUMENT      = "document"       # OntologyDocument
    COMPILED      = "compiled"       # CompiledOntology
    HIERARCHY     = "hierarchy"      # Full inheritance tree
    REFERENCE     = "reference"      # Cross-document reference check
    RUNTIME_OBJ   = "runtime_object" # Application runtime object
    CROSS_ONTOLOGY= "cross_ontology" # Multi-ontology consistency
    CONSTRAINT    = "constraint"     # Constraint definition itself


# ── Constraint type ───────────────────────────────────────────────────────────

class ConstraintType(str, Enum):
    """Category of a constraint rule."""
    REQUIRED_FIELD   = "required_field"    # Non-null / non-empty fields
    DATA_TYPE        = "data_type"         # Python type matches ontology DataType
    TYPE_CHECK       = "type_check"        # Runtime type identity check
    CARDINALITY      = "cardinality"       # Relationship cardinality limits
    REFERENCE        = "reference"         # ref_uri / parent_uri resolution
    CIRCULAR         = "circular"          # Circular inheritance / reference
    INHERITANCE      = "inheritance"       # Inheritance rules (depth, mixin, etc.)
    NAMESPACE        = "namespace"         # Namespace URI / prefix rules
    URI_FORMAT       = "uri_format"        # URI well-formedness
    ALIAS            = "alias"             # Alias uniqueness / conflict
    DEPRECATION      = "deprecation"       # Deprecated type usage warnings
    BUSINESS_RULE    = "business_rule"     # Domain-specific invariants
    CUSTOM           = "custom"            # User-defined constraints


# ── Validation mode ───────────────────────────────────────────────────────────

class ValidationMode(str, Enum):
    """How strictly validation is applied."""
    STRICT       = "strict"        # Errors AND warnings block; all checks run
    STANDARD     = "standard"      # Errors block; warnings are reported only
    PERMISSIVE   = "permissive"    # Only CRITICALs block; rest reported
    WARNING_ONLY = "warning_only"  # Run all checks but never raise exceptions
    SCHEMA_ONLY  = "schema_only"   # Only structural / type checks
    RUNTIME_ONLY = "runtime_only"  # Only runtime-object checks


# ── Validation phase ──────────────────────────────────────────────────────────

class ValidationPhase(str, Enum):
    """Lifecycle phase at which validation is triggered."""
    PRE_REGISTRATION = "pre_registration"  # Before type is registered
    PRE_COMPILE      = "pre_compile"       # Before ontology compilation
    POST_COMPILE     = "post_compile"      # After compilation, before activation
    RUNTIME          = "runtime"           # During live object creation/storage
    BATCH            = "batch"             # Explicit batch validation run
    BACKGROUND       = "background"        # Async background revalidation
    ON_DEMAND        = "on_demand"         # User-triggered ad-hoc validation


# ── Reference kind ────────────────────────────────────────────────────────────

class ReferenceKind(str, Enum):
    """Kind of cross-object reference being validated."""
    PARENT_URI   = "parent_uri"     # Inheritance parent
    REF_PROPERTY = "ref_property"   # Property ref_uri
    REL_SOURCE   = "rel_source"     # Relationship source_type_uri
    REL_TARGET   = "rel_target"     # Relationship target_type_uri
    REL_INVERSE  = "rel_inverse"    # Relationship inverse_uri
    ALIAS        = "alias"          # Alias → canonical URI


# ── Numeric constants ─────────────────────────────────────────────────────────

MAX_VALIDATION_ERRORS:     Final[int]   = 256
MAX_BATCH_SIZE:            Final[int]   = 1_024
VALIDATION_TIMEOUT_MS:     Final[float] = 15_000.0
MAX_HISTORY_PER_TARGET:    Final[int]   = 32
MAX_INHERITANCE_CHECK_DEPTH: Final[int] = 64   # More permissive than MAX_INHERITANCE_DEPTH
MAX_PARALLEL_VALIDATORS:   Final[int]   = 8
WARM_RESULT_CACHE_SIZE:    Final[int]   = 512


# ── String constants ──────────────────────────────────────────────────────────

VALIDATOR_VERSION:        Final[str] = "1.0.0"
PASS_RESULT:              Final[str] = "pass"
FAIL_RESULT:              Final[str] = "fail"
WARN_RESULT:              Final[str] = "warn"
SYSTEM_VALIDATOR_ACTOR:   Final[str] = "iios:validator:system"


# ── Built-in constraint ID prefixes ──────────────────────────────────────────

BUILTIN_TYPE_PREFIX: Final[str] = "builtin.type"
BUILTIN_PROP_PREFIX: Final[str] = "builtin.prop"
BUILTIN_REL_PREFIX:  Final[str] = "builtin.rel"
BUILTIN_NS_PREFIX:   Final[str] = "builtin.ns"
BUILTIN_HIER_PREFIX: Final[str] = "builtin.hier"
BUILTIN_REF_PREFIX:  Final[str] = "builtin.ref"
