"""
iios/ontology/ontology_exceptions.py
======================================
Exception hierarchy for the IIOS Ontology Runtime Layer.

All exceptions derive from OntologyError → Exception.
Each carries a machine-readable ``code`` attribute for structured logging.

Error code prefix: ONT-
"""

from __future__ import annotations

from typing import Any

__all__ = [
    # Base
    "OntologyError",
    # Load errors
    "OntologyLoadError",
    "OntologyNotFoundError",
    "OntologyAlreadyLoadedError",
    "OntologyResourceError",
    # Compile errors
    "OntologyCompileError",
    "OntologyResolveError",
    "OntologyCircularInheritanceError",
    "OntologyInvalidReferenceError",
    "OntologySchemaError",
    # Registry errors
    "OntologyRegistryError",
    "TypeNotFoundError",
    "TypeAlreadyExistsError",
    "NamespaceNotFoundError",
    "NamespaceAlreadyExistsError",
    # Query errors
    "OntologyQueryError",
    "OntologyQueryTimeoutError",
    # Runtime errors
    "OntologyRuntimeError",
    "OntologyNotInitializedError",
    "OntologyVersionError",
    # Validation errors
    "OntologyValidationError",
    "OntologyConstraintError",
]


class OntologyError(Exception):
    """Base exception for all IIOS Ontology Runtime errors."""

    def __init__(
        self,
        message: str = "",
        code:    str = "ONT-000",
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code    = code
        self.context: dict[str, Any] = context or {}

    def __str__(self) -> str:
        base = self.message or repr(self)
        return f"[{self.code}] {base}"


# ── Load errors ───────────────────────────────────────────────────────────────

class OntologyLoadError(OntologyError):
    """Failed to load an ontology document."""

    def __init__(
        self,
        message:  str,
        ont_name: str = "",
        code:     str = "ONT-010",
        **kw: Any,
    ) -> None:
        super().__init__(message, code=code, **kw)
        self.ont_name = ont_name


class OntologyNotFoundError(OntologyLoadError):
    """Requested ontology document does not exist."""

    def __init__(self, name: str, code: str = "ONT-011", **kw: Any) -> None:
        super().__init__(f"Ontology not found: {name!r}", ont_name=name, code=code, **kw)
        self.name = name


class OntologyAlreadyLoadedError(OntologyLoadError):
    """Attempted to load an ontology that is already loaded."""

    def __init__(self, name: str, code: str = "ONT-012", **kw: Any) -> None:
        super().__init__(f"Ontology already loaded: {name!r}", ont_name=name, code=code, **kw)
        self.name = name


class OntologyResourceError(OntologyLoadError):
    """IO or resource error while loading an ontology."""

    def __init__(self, message: str, code: str = "ONT-013", **kw: Any) -> None:
        super().__init__(message, code=code, **kw)


# ── Compile errors ────────────────────────────────────────────────────────────

class OntologyCompileError(OntologyError):
    """Ontology compilation failed."""

    def __init__(self, message: str, code: str = "ONT-020", **kw: Any) -> None:
        super().__init__(message, code=code, **kw)


class OntologyResolveError(OntologyCompileError):
    """Failed to resolve a reference or import in an ontology."""

    def __init__(self, message: str, uri: str = "", code: str = "ONT-021", **kw: Any) -> None:
        super().__init__(message, code=code, **kw)
        self.uri = uri


class OntologyCircularInheritanceError(OntologyCompileError):
    """Circular inheritance detected in type hierarchy."""

    def __init__(self, chain: list[str], code: str = "ONT-022", **kw: Any) -> None:
        path = " → ".join(chain)
        super().__init__(f"Circular inheritance: {path}", code=code, **kw)
        self.chain = chain


class OntologyInvalidReferenceError(OntologyCompileError):
    """A type or relationship references an unknown URI."""

    def __init__(self, ref: str, from_uri: str = "", code: str = "ONT-023", **kw: Any) -> None:
        super().__init__(f"Invalid reference {ref!r} in {from_uri!r}", code=code, **kw)
        self.ref      = ref
        self.from_uri = from_uri


class OntologySchemaError(OntologyCompileError):
    """The ontology document does not conform to the expected schema."""

    def __init__(self, message: str, code: str = "ONT-024", **kw: Any) -> None:
        super().__init__(message, code=code, **kw)


# ── Registry errors ───────────────────────────────────────────────────────────

class OntologyRegistryError(OntologyError):
    """A registry operation failed."""

    def __init__(self, message: str, code: str = "ONT-030", **kw: Any) -> None:
        super().__init__(message, code=code, **kw)


class TypeNotFoundError(OntologyRegistryError):
    """Requested type URI is not registered."""

    def __init__(self, uri: str, code: str = "ONT-031", **kw: Any) -> None:
        super().__init__(f"Type not found: {uri!r}", code=code, **kw)
        self.uri = uri


class TypeAlreadyExistsError(OntologyRegistryError):
    """A type with the same URI is already registered."""

    def __init__(self, uri: str, code: str = "ONT-032", **kw: Any) -> None:
        super().__init__(f"Type already exists: {uri!r}", code=code, **kw)
        self.uri = uri


class NamespaceNotFoundError(OntologyRegistryError):
    """Requested namespace URI is not registered."""

    def __init__(self, uri: str, code: str = "ONT-033", **kw: Any) -> None:
        super().__init__(f"Namespace not found: {uri!r}", code=code, **kw)
        self.uri = uri


class NamespaceAlreadyExistsError(OntologyRegistryError):
    """A namespace with the same URI is already registered."""

    def __init__(self, uri: str, code: str = "ONT-034", **kw: Any) -> None:
        super().__init__(f"Namespace already exists: {uri!r}", code=code, **kw)
        self.uri = uri


# ── Query errors ──────────────────────────────────────────────────────────────

class OntologyQueryError(OntologyError):
    """Ontology query failed."""

    def __init__(self, message: str, code: str = "ONT-040", **kw: Any) -> None:
        super().__init__(message, code=code, **kw)


class OntologyQueryTimeoutError(OntologyQueryError):
    """Ontology query exceeded the allowed time limit."""

    def __init__(self, timeout_ms: float = 0.0, code: str = "ONT-041", **kw: Any) -> None:
        super().__init__(f"Query timeout after {timeout_ms:.0f}ms", code=code, **kw)
        self.timeout_ms = timeout_ms


# ── Runtime errors ────────────────────────────────────────────────────────────

class OntologyRuntimeError(OntologyError):
    """A runtime failure in the ontology engine."""

    def __init__(self, message: str, code: str = "ONT-050", **kw: Any) -> None:
        super().__init__(message, code=code, **kw)


class OntologyNotInitializedError(OntologyRuntimeError):
    """Operation attempted before the ontology engine was initialised."""

    def __init__(self, code: str = "ONT-051", **kw: Any) -> None:
        super().__init__(
            "OntologyRuntimeEngine is not initialised. Call get_ontology_engine().initialize() first.",
            code=code,
            **kw,
        )


class OntologyVersionError(OntologyRuntimeError):
    """Version conflict or incompatibility."""

    def __init__(self, message: str, code: str = "ONT-052", **kw: Any) -> None:
        super().__init__(message, code=code, **kw)


# ── Validation errors ─────────────────────────────────────────────────────────

class OntologyValidationError(OntologyError):
    """An ontology object failed validation."""

    def __init__(
        self,
        message: str,
        violations: list[str] | None = None,
        code: str = "ONT-060",
        **kw: Any,
    ) -> None:
        super().__init__(message, code=code, **kw)
        self.violations: list[str] = violations or []


class OntologyConstraintError(OntologyValidationError):
    """A constraint defined in the ontology was violated."""

    def __init__(self, message: str, code: str = "ONT-061", **kw: Any) -> None:
        super().__init__(message, code=code, **kw)
