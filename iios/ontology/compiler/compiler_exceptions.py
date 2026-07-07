"""
iios/ontology/compiler/compiler_exceptions.py
================================================
Exception hierarchy for the IIOS Ontology Compiler & Loader subsystem.

All exceptions derive from CompilerError → Exception.
Error code prefix: CMP-
"""

from __future__ import annotations

from typing import Any

__all__ = [
    # Base
    "CompilerError",
    # Dependency resolution
    "DependencyError",
    "CircularDependencyError",
    "UnresolvedDependencyError",
    "DependencyDepthError",
    # Compilation
    "CompilationError",
    "CompilationTimeoutError",
    "PassFailedError",
    "TypeResolutionError",
    "PropertyResolutionError",
    "IndexBuildError",
    # Loading
    "LoaderError",
    "ColdStartError",
    "WarmStartError",
    "IncrementalLoadError",
    "HotReloadError",
    "CacheLoaderError",
    # Metadata
    "MetadataError",
    "HashMismatchError",
    # Registry
    "CompilerRegistryError",
    "DuplicateCompilationError",
    # Context
    "CompilerContextError",
]


class CompilerError(Exception):
    """Base exception for all Ontology Compiler errors."""

    def __init__(
        self,
        message: str = "",
        code:    str = "CMP-000",
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code    = code
        self.context: dict[str, Any] = context or {}

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# ── Dependency resolution errors ──────────────────────────────────────────────

class DependencyError(CompilerError):
    """Dependency resolution failed."""
    def __init__(self, message: str, code: str = "CMP-010", **kw: Any) -> None:
        super().__init__(message, code=code, **kw)


class CircularDependencyError(DependencyError):
    """Circular dependency detected between ontology documents."""
    def __init__(self, chain: list[str], code: str = "CMP-011", **kw: Any) -> None:
        names = " → ".join(chain)
        super().__init__(f"Circular dependency detected: {names}", code=code, **kw)
        self.chain = chain


class UnresolvedDependencyError(DependencyError):
    """A required dependency could not be resolved."""
    def __init__(self, dep_name: str, requirer: str, code: str = "CMP-012", **kw: Any) -> None:
        super().__init__(
            f"Unresolved dependency {dep_name!r} required by {requirer!r}",
            code=code, **kw
        )
        self.dep_name = dep_name
        self.requirer = requirer


class DependencyDepthError(DependencyError):
    """Maximum dependency depth exceeded."""
    def __init__(self, depth: int, max_depth: int, code: str = "CMP-013", **kw: Any) -> None:
        super().__init__(
            f"Dependency depth {depth} exceeds maximum {max_depth}",
            code=code, **kw
        )
        self.depth     = depth
        self.max_depth = max_depth


# ── Compilation errors ────────────────────────────────────────────────────────

class CompilationError(CompilerError):
    """Compilation failed."""
    def __init__(self, message: str, ont_name: str = "", code: str = "CMP-020", **kw: Any) -> None:
        super().__init__(message, code=code, **kw)
        self.ont_name = ont_name


class CompilationTimeoutError(CompilationError):
    """Compilation timed out."""
    def __init__(self, ont_name: str, timeout_ms: float, code: str = "CMP-021", **kw: Any) -> None:
        super().__init__(
            f"Compilation of {ont_name!r} timed out after {timeout_ms:.0f}ms",
            ont_name=ont_name, code=code, **kw
        )
        self.timeout_ms = timeout_ms


class PassFailedError(CompilationError):
    """A specific compilation pass failed."""
    def __init__(self, pass_name: str, reason: str, code: str = "CMP-022", **kw: Any) -> None:
        super().__init__(
            f"Compilation pass {pass_name!r} failed: {reason}",
            code=code, **kw
        )
        self.pass_name = pass_name
        self.reason    = reason


class TypeResolutionError(CompilationError):
    """A type URI could not be resolved."""
    def __init__(self, type_uri: str, code: str = "CMP-023", **kw: Any) -> None:
        super().__init__(f"Cannot resolve type URI: {type_uri!r}", code=code, **kw)
        self.type_uri = type_uri


class PropertyResolutionError(CompilationError):
    """Property inheritance resolution failed."""
    def __init__(self, type_uri: str, reason: str, code: str = "CMP-024", **kw: Any) -> None:
        super().__init__(
            f"Property resolution failed for {type_uri!r}: {reason}",
            code=code, **kw
        )
        self.type_uri = type_uri


class IndexBuildError(CompilationError):
    """Building a runtime index failed."""
    def __init__(self, index_name: str, reason: str, code: str = "CMP-025", **kw: Any) -> None:
        super().__init__(
            f"Index build failed for {index_name!r}: {reason}",
            code=code, **kw
        )
        self.index_name = index_name


# ── Loading errors ────────────────────────────────────────────────────────────

class LoaderError(CompilerError):
    """Loader operation failed."""
    def __init__(self, message: str, code: str = "CMP-030", **kw: Any) -> None:
        super().__init__(message, code=code, **kw)


class ColdStartError(LoaderError):
    """Cold-start loading failed."""
    def __init__(self, reason: str, code: str = "CMP-031", **kw: Any) -> None:
        super().__init__(f"Cold start failed: {reason}", code=code, **kw)


class WarmStartError(LoaderError):
    """Warm-start loading failed."""
    def __init__(self, reason: str, code: str = "CMP-032", **kw: Any) -> None:
        super().__init__(f"Warm start failed: {reason}", code=code, **kw)


class IncrementalLoadError(LoaderError):
    """Incremental load operation failed."""
    def __init__(self, ont_name: str, reason: str, code: str = "CMP-033", **kw: Any) -> None:
        super().__init__(
            f"Incremental load failed for {ont_name!r}: {reason}",
            code=code, **kw
        )
        self.ont_name = ont_name


class HotReloadError(LoaderError):
    """Hot reload operation failed."""
    def __init__(self, ont_name: str, reason: str, code: str = "CMP-034", **kw: Any) -> None:
        super().__init__(
            f"Hot reload failed for {ont_name!r}: {reason}",
            code=code, **kw
        )
        self.ont_name = ont_name


class CacheLoaderError(LoaderError):
    """Cache loader operation failed."""
    def __init__(self, reason: str, code: str = "CMP-035", **kw: Any) -> None:
        super().__init__(f"Cache loader error: {reason}", code=code, **kw)


# ── Metadata errors ───────────────────────────────────────────────────────────

class MetadataError(CompilerError):
    """Metadata generation failed."""
    def __init__(self, reason: str, code: str = "CMP-040", **kw: Any) -> None:
        super().__init__(f"Metadata error: {reason}", code=code, **kw)


class HashMismatchError(MetadataError):
    """Cached hash does not match recomputed hash — cache invalid."""
    def __init__(self, ont_name: str, expected: str, actual: str, code: str = "CMP-041", **kw: Any) -> None:
        super().__init__(
            f"Hash mismatch for {ont_name!r}: expected {expected!r}, got {actual!r}",
            code=code, **kw
        )
        self.ont_name = ont_name
        self.expected = expected
        self.actual   = actual


# ── Registry errors ───────────────────────────────────────────────────────────

class CompilerRegistryError(CompilerError):
    """Compiler registry operation failed."""
    def __init__(self, message: str, code: str = "CMP-050", **kw: Any) -> None:
        super().__init__(message, code=code, **kw)


class DuplicateCompilationError(CompilerRegistryError):
    """An ontology was compiled more than once without overwrite permission."""
    def __init__(self, name: str, code: str = "CMP-051", **kw: Any) -> None:
        super().__init__(f"Ontology already compiled: {name!r}", code=code, **kw)
        self.name = name


# ── Context errors ────────────────────────────────────────────────────────────

class CompilerContextError(CompilerError):
    """Compiler context operation failed."""
    def __init__(self, message: str, code: str = "CMP-060", **kw: Any) -> None:
        super().__init__(message, code=code, **kw)
