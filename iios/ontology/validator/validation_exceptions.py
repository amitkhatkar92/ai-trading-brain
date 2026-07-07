"""
iios/ontology/validator/validation_exceptions.py
=================================================
Exception hierarchy for the IIOS Ontology Validation & Constraint Engine.

All exceptions derive from ValidatorError → Exception.
Each carries a machine-readable ``code`` attribute (prefix VAL-).

Code ranges:
  VAL-000  Base
  VAL-010  Constraint violations
  VAL-020  Semantic validation errors
  VAL-030  Referential integrity errors
  VAL-040  Configuration / policy errors
  VAL-050  Constraint registry errors
  VAL-060  Validation engine errors
"""

from __future__ import annotations

from typing import Any, Optional

__all__ = [
    # Base
    "ValidatorError",
    # Constraint violations
    "ConstraintViolationError",
    "RequiredFieldError",
    "DataTypeConstraintError",
    "CardinalityViolationError",
    "UriFormatError",
    "AliasConflictError",
    "BusinessRuleViolationError",
    # Semantic validation
    "SemanticValidationError",
    "HierarchyValidationError",
    "InheritanceDepthError",
    "NamespaceConsistencyError",
    "VersionCompatibilityError",
    # Referential integrity
    "ReferentialIntegrityError",
    "BrokenReferenceError",
    "CircularReferenceError",
    "InvalidEndpointError",
    "UnresolvableAliasError",
    # Configuration
    "ValidationConfigError",
    "ValidationModeError",
    # Registry
    "ConstraintRegistryError",
    "DuplicateConstraintError",
    "UnknownConstraintError",
    # Engine
    "ValidationEngineError",
    "ValidationTimeoutError",
    "ValidationNotInitializedError",
]


# ── Base ──────────────────────────────────────────────────────────────────────

class ValidatorError(Exception):
    """Base exception for all IIOS Validation & Constraint Engine errors."""

    def __init__(
        self,
        message: str = "",
        code:    str = "VAL-000",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code    = code
        self.context: dict[str, Any] = context or {}

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# ── Constraint violations (VAL-01x) ───────────────────────────────────────────

class ConstraintViolationError(ValidatorError):
    """A constraint was violated by a runtime or ontology object."""

    def __init__(
        self,
        constraint_id: str,
        target:        str,
        message:       str = "",
        code:          str = "VAL-010",
        **kw: Any,
    ) -> None:
        super().__init__(message or f"Constraint {constraint_id!r} violated by {target!r}", code=code, **kw)
        self.constraint_id = constraint_id
        self.target        = target


class RequiredFieldError(ConstraintViolationError):
    """A required field is missing or empty."""

    def __init__(self, field_name: str, target: str, **kw: Any) -> None:
        super().__init__(
            constraint_id = f"builtin.type.required_field.{field_name}",
            target        = target,
            message       = f"Required field {field_name!r} is missing on {target!r}",
            code          = "VAL-011",
            **kw,
        )
        self.field_name = field_name


class DataTypeConstraintError(ConstraintViolationError):
    """A value does not match the declared DataType."""

    def __init__(
        self,
        field_name: str,
        expected:   str,
        actual:     str,
        target:     str,
        **kw: Any,
    ) -> None:
        super().__init__(
            constraint_id = "builtin.prop.data_type",
            target        = target,
            message       = f"Field {field_name!r} on {target!r}: expected {expected}, got {actual}",
            code          = "VAL-012",
            **kw,
        )
        self.field_name = field_name
        self.expected   = expected
        self.actual     = actual


class CardinalityViolationError(ConstraintViolationError):
    """Relationship cardinality limit exceeded."""

    def __init__(
        self,
        rel_name: str,
        limit:    str,
        actual:   int,
        target:   str,
        **kw: Any,
    ) -> None:
        super().__init__(
            constraint_id = "builtin.rel.cardinality",
            target        = target,
            message       = f"Cardinality {limit} violated on {rel_name!r}: {actual} instances",
            code          = "VAL-013",
            **kw,
        )
        self.rel_name = rel_name
        self.limit    = limit
        self.actual   = actual


class UriFormatError(ConstraintViolationError):
    """A URI is malformed or violates naming conventions."""

    def __init__(self, uri: str, reason: str, **kw: Any) -> None:
        super().__init__(
            constraint_id = "builtin.type.uri_format",
            target        = uri,
            message       = f"Invalid URI {uri!r}: {reason}",
            code          = "VAL-014",
            **kw,
        )
        self.uri    = uri
        self.reason = reason


class AliasConflictError(ConstraintViolationError):
    """An alias collides with an existing type name or alias."""

    def __init__(self, alias: str, conflicting_uri: str, **kw: Any) -> None:
        super().__init__(
            constraint_id = "builtin.type.alias_conflict",
            target        = alias,
            message       = f"Alias {alias!r} conflicts with existing type {conflicting_uri!r}",
            code          = "VAL-015",
            **kw,
        )
        self.alias          = alias
        self.conflicting_uri = conflicting_uri


class BusinessRuleViolationError(ConstraintViolationError):
    """A domain business rule was violated."""

    def __init__(self, rule_id: str, target: str, detail: str = "", **kw: Any) -> None:
        super().__init__(
            constraint_id = rule_id,
            target        = target,
            message       = f"Business rule {rule_id!r} violated on {target!r}: {detail}",
            code          = "VAL-019",
            **kw,
        )
        self.rule_id = rule_id
        self.detail  = detail


# ── Semantic validation (VAL-02x) ─────────────────────────────────────────────

class SemanticValidationError(ValidatorError):
    """An ontology semantic invariant is violated."""

    def __init__(self, message: str = "", code: str = "VAL-020", **kw: Any) -> None:
        super().__init__(message, code=code, **kw)


class HierarchyValidationError(SemanticValidationError):
    """The inheritance hierarchy is invalid."""

    def __init__(self, message: str, chain: Optional[list[str]] = None, **kw: Any) -> None:
        super().__init__(message, code="VAL-021", **kw)
        self.chain: list[str] = chain or []


class InheritanceDepthError(HierarchyValidationError):
    """Inheritance chain exceeds the maximum permitted depth."""

    def __init__(self, type_uri: str, depth: int, max_depth: int, **kw: Any) -> None:
        super().__init__(
            f"Type {type_uri!r} exceeds max inheritance depth ({depth} > {max_depth})",
            **kw,
        )
        self.type_uri  = type_uri
        self.depth     = depth
        self.max_depth = max_depth


class NamespaceConsistencyError(SemanticValidationError):
    """A type URI does not belong to its declared namespace."""

    def __init__(self, type_uri: str, namespace_uri: str, **kw: Any) -> None:
        super().__init__(
            f"Type URI {type_uri!r} is not within namespace {namespace_uri!r}",
            code="VAL-022",
            **kw,
        )
        self.type_uri     = type_uri
        self.namespace_uri = namespace_uri


class VersionCompatibilityError(SemanticValidationError):
    """Two ontologies have incompatible versions."""

    def __init__(self, ont_a: str, ver_a: str, ont_b: str, ver_b: str, **kw: Any) -> None:
        super().__init__(
            f"Version mismatch: {ont_a}@{ver_a} incompatible with {ont_b}@{ver_b}",
            code="VAL-023",
            **kw,
        )
        self.ont_a = ont_a
        self.ver_a = ver_a
        self.ont_b = ont_b
        self.ver_b = ver_b


# ── Referential integrity (VAL-03x) ───────────────────────────────────────────

class ReferentialIntegrityError(ValidatorError):
    """A reference cannot be resolved."""

    def __init__(self, message: str = "", code: str = "VAL-030", **kw: Any) -> None:
        super().__init__(message, code=code, **kw)


class BrokenReferenceError(ReferentialIntegrityError):
    """A URI reference points to a non-existent type."""

    def __init__(self, ref_uri: str, source: str, kind: str = "", **kw: Any) -> None:
        super().__init__(
            f"Broken reference {ref_uri!r} from {source!r}" + (f" ({kind})" if kind else ""),
            code="VAL-031",
            **kw,
        )
        self.ref_uri = ref_uri
        self.source  = source
        self.kind    = kind


class CircularReferenceError(ReferentialIntegrityError):
    """A circular reference chain was detected."""

    def __init__(self, chain: list[str], **kw: Any) -> None:
        super().__init__(
            "Circular reference: " + " → ".join(chain),
            code="VAL-032",
            **kw,
        )
        self.chain = chain


class InvalidEndpointError(ReferentialIntegrityError):
    """A relationship endpoint points to a type that cannot play that role."""

    def __init__(self, rel_uri: str, endpoint: str, reason: str, **kw: Any) -> None:
        super().__init__(
            f"Invalid endpoint {endpoint!r} on relationship {rel_uri!r}: {reason}",
            code="VAL-033",
            **kw,
        )
        self.rel_uri  = rel_uri
        self.endpoint = endpoint
        self.reason   = reason


class UnresolvableAliasError(ReferentialIntegrityError):
    """An alias cannot be resolved to a canonical type URI."""

    def __init__(self, alias: str, **kw: Any) -> None:
        super().__init__(
            f"Cannot resolve alias {alias!r} to any known type URI",
            code="VAL-034",
            **kw,
        )
        self.alias = alias


# ── Configuration (VAL-04x) ───────────────────────────────────────────────────

class ValidationConfigError(ValidatorError):
    """Validation is misconfigured."""

    def __init__(self, message: str = "", **kw: Any) -> None:
        super().__init__(message, code="VAL-040", **kw)


class ValidationModeError(ValidationConfigError):
    """Illegal combination of validation mode and phase."""

    def __init__(self, mode: str, phase: str, **kw: Any) -> None:
        super().__init__(f"Mode {mode!r} incompatible with phase {phase!r}", **kw)
        self.mode  = mode
        self.phase = phase


# ── Registry (VAL-05x) ────────────────────────────────────────────────────────

class ConstraintRegistryError(ValidatorError):
    """Constraint registry operation failed."""

    def __init__(self, message: str = "", **kw: Any) -> None:
        super().__init__(message, code="VAL-050", **kw)


class DuplicateConstraintError(ConstraintRegistryError):
    """A constraint with this ID is already registered."""

    def __init__(self, constraint_id: str, **kw: Any) -> None:
        super().__init__(f"Constraint already registered: {constraint_id!r}", **kw)
        self.constraint_id = constraint_id


class UnknownConstraintError(ConstraintRegistryError):
    """No constraint with the given ID exists."""

    def __init__(self, constraint_id: str, **kw: Any) -> None:
        super().__init__(f"Unknown constraint: {constraint_id!r}", **kw)
        self.constraint_id = constraint_id


# ── Engine (VAL-06x) ──────────────────────────────────────────────────────────

class ValidationEngineError(ValidatorError):
    """Validation engine internal error."""

    def __init__(self, message: str = "", **kw: Any) -> None:
        super().__init__(message, code="VAL-060", **kw)


class ValidationTimeoutError(ValidationEngineError):
    """Validation exceeded the configured time limit."""

    def __init__(self, target: str, timeout_ms: float, **kw: Any) -> None:
        super().__init__(
            f"Validation of {target!r} exceeded timeout of {timeout_ms:.0f}ms",
            **kw,
        )
        self.target     = target
        self.timeout_ms = timeout_ms


class ValidationNotInitializedError(ValidationEngineError):
    """The validation engine has not been initialized."""

    def __init__(self, **kw: Any) -> None:
        super().__init__("ValidationEngine not initialized — call compile_builtins() first", **kw)
