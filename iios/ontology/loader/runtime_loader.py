"""
iios/ontology/loader/runtime_loader.py
========================================
Runtime loader — the primary entry point for all production loading.

Manages three loading strategies:
- COLD START: load raw documents → compile → register (first ever run)
- WARM START: load from disk/memory cache → validate → register (restart)
- SELECTIVE: load/compile only named ontologies

Integrates with CompilerManager for compilation and CompiledLoader for cache.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..compiler.compiler_constants import CompilationStrategy, IncrementalMode, LoadPhase
from ..compiler.compiler_exceptions import ColdStartError, WarmStartError
from ..compiler.compiler_manager    import CompilerManager, get_compiler_manager
from .compiled_loader               import CompiledLoader, get_compiled_loader
from ..ontology_constants           import BUILTIN_ONTOLOGY_NAMES
from ..runtime.runtime_object       import CompiledOntology

__all__ = [
    "LoadResult",
    "RuntimeLoader",
    "get_runtime_loader",
    "reset_runtime_loader",
]

_LOG  = logging.getLogger("iios.ontology.loader.runtime")
_lock = threading.Lock()
_inst: Optional["RuntimeLoader"] = None


# ── Result data model ─────────────────────────────────────────────────────────

@dataclass
class LoadResult:
    """Summary of a runtime load operation."""
    strategy:    str
    succeeded:   int
    failed:      int
    skipped:     int
    total_ms:    float
    errors:      list[str]    = field(default_factory=list)
    loaded_names: list[str]   = field(default_factory=list)
    finished_at:  float       = field(default_factory=time.time)

    @property
    def all_succeeded(self) -> bool:
        return self.failed == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy":     self.strategy,
            "succeeded":    self.succeeded,
            "failed":       self.failed,
            "skipped":      self.skipped,
            "total_ms":     round(self.total_ms, 3),
            "errors":       list(self.errors),
            "loaded_names": list(self.loaded_names),
        }


# ── Runtime loader ────────────────────────────────────────────────────────────

class RuntimeLoader:
    """
    Production loader for the Ontology Runtime Layer.

    Usage (in OntologyRuntimeEngine.initialize)::

        loader = get_runtime_loader()
        result = loader.cold_start()
        assert result.all_succeeded
    """

    def __init__(self) -> None:
        self._lock        = threading.RLock()
        self._initialized = False

    # ── Cold start ────────────────────────────────────────────────────────────

    def cold_start(
        self,
        strategy:  CompilationStrategy = CompilationStrategy.SEQUENTIAL,
    ) -> LoadResult:
        """
        Full cold start: load raw documents, compile, and register.

        Typical use: first-ever startup, or after a cache wipe.
        """
        t0 = time.perf_counter()
        _LOG.info("Cold start: loading all built-in ontologies …")

        try:
            mgr    = get_compiler_manager()
            result = mgr.compile_builtins(strategy=strategy)
            total  = (time.perf_counter() - t0) * 1_000.0

            errors = [r.error for r in result.results if r.error]
            names  = [r.name  for r in result.results if r.success]

            load_result = LoadResult(
                strategy     = "cold_start",
                succeeded    = result.succeeded,
                failed       = result.failed,
                skipped      = 0,
                total_ms     = total,
                errors       = [e for e in errors if e],
                loaded_names = names,
            )
            self._initialized = result.succeeded > 0
            _LOG.info(
                "Cold start complete: %d/%d succeeded in %.1fms",
                result.succeeded, len(result.results), total,
            )
            return load_result

        except Exception as exc:
            total = (time.perf_counter() - t0) * 1_000.0
            raise ColdStartError(str(exc)) from exc

    # ── Warm start ────────────────────────────────────────────────────────────

    def warm_start(
        self,
        cache_dir: Optional[str] = None,
    ) -> LoadResult:
        """
        Warm start: load compiled artefacts from disk cache, skipping compilation.

        Falls back to cold_start if any artefact is missing or invalid.
        """
        t0      = time.perf_counter()
        _LOG.info("Warm start: loading compiled artefacts from cache …")

        cl       = get_compiled_loader(cache_dir=cache_dir)
        mgr      = get_compiler_manager()
        loaded   = 0
        missing  = 0
        errors: list[str] = []
        names:  list[str] = []

        for name in BUILTIN_ONTOLOGY_NAMES:
            try:
                compiled = cl.load_from_disk(name) if cache_dir else cl.load_from_memory(name)
                if compiled:
                    from ..cache.ontology_cache import get_ontology_cache
                    from ..registry.ontology_registry_manager import get_registry_manager
                    from ..ontology_registry import get_ontology_registry
                    get_ontology_cache().put(name, compiled)
                    get_registry_manager().register_compiled(compiled)
                    get_ontology_registry().register_compiled(compiled)
                    loaded += 1
                    names.append(name)
                else:
                    missing += 1
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                missing += 1

        total = (time.perf_counter() - t0) * 1_000.0

        if missing > 0:
            _LOG.info("Warm start: %d missing — falling back to cold start", missing)
            cold = self.cold_start()
            cold.total_ms += total
            cold.skipped   = loaded
            return cold

        self._initialized = True
        _LOG.info("Warm start complete: %d loaded in %.1fms", loaded, total)
        return LoadResult(
            strategy     = "warm_start",
            succeeded    = loaded,
            failed       = len(errors),
            skipped      = 0,
            total_ms     = total,
            errors       = errors,
            loaded_names = names,
        )

    # ── Selective load ────────────────────────────────────────────────────────

    def selective_load(
        self,
        names:     list[str],
        overwrite: bool = False,
    ) -> LoadResult:
        """Load and compile only the specified ontologies."""
        t0  = time.perf_counter()
        mgr = get_compiler_manager()

        try:
            result = mgr.compile_selective(names, overwrite=overwrite)
            total  = (time.perf_counter() - t0) * 1_000.0
            errors = [r.error for r in result.results if r.error]
            loaded = [r.name  for r in result.results if r.success]
            return LoadResult(
                strategy     = "selective",
                succeeded    = result.succeeded,
                failed       = result.failed,
                skipped      = len(names) - len(result.results),
                total_ms     = total,
                errors       = [e for e in errors if e],
                loaded_names = loaded,
            )
        except Exception as exc:
            total = (time.perf_counter() - t0) * 1_000.0
            return LoadResult(
                strategy  = "selective",
                succeeded = 0,
                failed    = len(names),
                skipped   = 0,
                total_ms  = total,
                errors    = [str(exc)],
            )

    # ── Lazy load ─────────────────────────────────────────────────────────────

    def lazy_load(self, name: str) -> Optional[CompiledOntology]:
        """Load a single ontology on demand."""
        return get_compiler_manager().get_or_compile(name)

    # ── Stats ──────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "initialized": self._initialized,
            "compiler":    get_compiler_manager().stats(),
        }

    @property
    def is_initialized(self) -> bool:
        return self._initialized


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_runtime_loader() -> RuntimeLoader:
    global _inst
    if _inst is None:
        with _lock:
            if _inst is None:
                _inst = RuntimeLoader()
    return _inst


def reset_runtime_loader() -> None:
    global _inst
    with _lock:
        _inst = None
