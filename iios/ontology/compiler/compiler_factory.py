"""
iios/ontology/compiler/compiler_factory.py
============================================
Factory for creating compiler pipeline components and compile requests.

Provides:
- CompileRequest — a structured compilation request
- CompileResult  — structured compilation result
- CompilerFactory — constructs all compiler pipeline objects
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .compiler_constants import CompilationStrategy, LoadPhase
from ..runtime.runtime_object import CompiledOntology, OntologyDocument, OntologyTypeDef

__all__ = [
    "CompileRequest",
    "CompileResult",
    "BatchCompileRequest",
    "BatchCompileResult",
    "CompilerFactory",
    "get_compiler_factory",
    "reset_compiler_factory",
]


# ── Request / result data models ──────────────────────────────────────────────

@dataclass
class CompileRequest:
    """
    A single compilation request for one ontology document.
    """
    document:        OntologyDocument
    external_types:  dict[str, OntologyTypeDef] = field(default_factory=dict)
    strategy:        CompilationStrategy         = CompilationStrategy.SEQUENTIAL
    overwrite:       bool                        = False
    operation_id:    str                         = field(default_factory=lambda: str(uuid.uuid4()))
    actor:           str                         = "iios.ontology.compiler"
    tags:            list[str]                   = field(default_factory=list)
    metadata_extra:  dict[str, Any]              = field(default_factory=dict)
    requested_at:    float                       = field(default_factory=time.time)

    @property
    def name(self) -> str:
        return self.document.name


@dataclass
class CompileResult:
    """
    The result of a single compilation request.
    """
    request:     CompileRequest
    compiled:    Optional[CompiledOntology]
    success:     bool
    duration_ms: float
    phase:       LoadPhase
    error:       Optional[str]                = None
    warnings:    list[str]                    = field(default_factory=list)
    build_id:    str                          = ""
    finished_at: float                        = field(default_factory=time.time)

    @property
    def name(self) -> str:
        return self.request.name

    def to_dict(self) -> dict[str, Any]:
        return {
            "name":        self.name,
            "success":     self.success,
            "duration_ms": round(self.duration_ms, 3),
            "phase":       self.phase.value,
            "error":       self.error,
            "warnings":    list(self.warnings),
            "build_id":    self.build_id,
        }


@dataclass
class BatchCompileRequest:
    """
    A request to compile multiple ontology documents as a batch.
    """
    requests:   list[CompileRequest]
    strategy:   CompilationStrategy       = CompilationStrategy.SEQUENTIAL
    fail_fast:  bool                      = False
    operation_id: str                     = field(default_factory=lambda: str(uuid.uuid4()))
    requested_at: float                   = field(default_factory=time.time)

    @property
    def names(self) -> list[str]:
        return [r.name for r in self.requests]


@dataclass
class BatchCompileResult:
    """
    The result of a batch compilation request.
    """
    request:     BatchCompileRequest
    results:     list[CompileResult]
    total_ms:    float
    succeeded:   int
    failed:      int
    finished_at: float = field(default_factory=time.time)

    @property
    def all_succeeded(self) -> bool:
        return self.failed == 0

    @property
    def compiled_ontologies(self) -> list[CompiledOntology]:
        return [r.compiled for r in self.results if r.compiled is not None]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total":       len(self.results),
            "succeeded":   self.succeeded,
            "failed":      self.failed,
            "total_ms":    round(self.total_ms, 3),
            "results":     [r.to_dict() for r in self.results],
        }


# ── Factory ───────────────────────────────────────────────────────────────────

class CompilerFactory:
    """
    Constructs compiler pipeline objects and requests.

    Provides a single place to assemble all compiler components
    (compiler, dependency resolver, metadata generator, registry).
    """

    # ── Requests ──────────────────────────────────────────────────────────────

    def make_request(
        self,
        document:       OntologyDocument,
        external_types: Optional[dict[str, OntologyTypeDef]] = None,
        strategy:       CompilationStrategy = CompilationStrategy.SEQUENTIAL,
        overwrite:      bool                = False,
        actor:          str                 = "iios.ontology.compiler",
        tags:           Optional[list[str]] = None,
        extra:          Optional[dict[str, Any]] = None,
    ) -> CompileRequest:
        return CompileRequest(
            document       = document,
            external_types = dict(external_types or {}),
            strategy       = strategy,
            overwrite      = overwrite,
            actor          = actor,
            tags           = list(tags or []),
            metadata_extra = dict(extra or {}),
        )

    def make_batch(
        self,
        requests:  list[CompileRequest],
        strategy:  CompilationStrategy = CompilationStrategy.SEQUENTIAL,
        fail_fast: bool                = False,
    ) -> BatchCompileRequest:
        return BatchCompileRequest(
            requests  = requests,
            strategy  = strategy,
            fail_fast = fail_fast,
        )

    def make_result(
        self,
        request:     CompileRequest,
        compiled:    Optional[CompiledOntology],
        success:     bool,
        duration_ms: float,
        phase:       LoadPhase,
        error:       Optional[str]     = None,
        warnings:    Optional[list[str]] = None,
        build_id:    str               = "",
    ) -> CompileResult:
        return CompileResult(
            request     = request,
            compiled    = compiled,
            success     = success,
            duration_ms = duration_ms,
            phase       = phase,
            error       = error,
            warnings    = list(warnings or []),
            build_id    = build_id,
        )

    def make_batch_result(
        self,
        request:  BatchCompileRequest,
        results:  list[CompileResult],
        total_ms: float,
    ) -> BatchCompileResult:
        succeeded = sum(1 for r in results if r.success)
        failed    = len(results) - succeeded
        return BatchCompileResult(
            request   = request,
            results   = results,
            total_ms  = total_ms,
            succeeded = succeeded,
            failed    = failed,
        )

    # ── Pipeline component factories ──────────────────────────────────────────

    def make_compiler(self) -> "OntologyCompiler":  # type: ignore[name-defined]
        from .ontology_compiler import OntologyCompiler
        return OntologyCompiler()

    def make_dependency_resolver(self) -> "DependencyResolver":  # type: ignore[name-defined]
        from .dependency_resolver import DependencyResolver
        return DependencyResolver()

    def make_metadata_generator(self) -> "MetadataGenerator":  # type: ignore[name-defined]
        from .metadata_generator import MetadataGenerator
        return MetadataGenerator()


# ── Singleton ─────────────────────────────────────────────────────────────────

_lock    = threading.Lock()
_factory: Optional["CompilerFactory"] = None


def get_compiler_factory() -> CompilerFactory:
    global _factory
    if _factory is None:
        with _lock:
            if _factory is None:
                _factory = CompilerFactory()
    return _factory


def reset_compiler_factory() -> None:
    global _factory
    with _lock:
        _factory = None
