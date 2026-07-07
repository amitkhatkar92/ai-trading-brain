"""
iios/ontology/compiler/compiler_manager.py
============================================
High-level orchestrator for the full Ontology Compiler & Loader pipeline.

Responsibilities:
- Coordinate dependency resolution
- Schedule compilation in correct order
- Support sequential, parallel, incremental, and hot-reload modes
- Generate and store runtime metadata
- Write results to compiler registry and ontology cache
- Expose a single public API for all compilation operations

This is the PRIMARY ENTRY POINT for the Compiler & Loader subsystem.
"""

from __future__ import annotations

import concurrent.futures
import logging
import threading
import time
from typing import Any, Optional

from .compiler_constants import (
    BUILTIN_COMPILE_ORDER,
    CompilationStrategy,
    LoadPhase,
    MAX_PARALLEL_COMPILATIONS,
    IncrementalMode,
)
from .compiler_exceptions import (
    CompilationError,
    HotReloadError,
    IncrementalLoadError,
    LoaderError,
)
from .compiler_context    import CompilerContext, get_compiler_context
from .compiler_factory    import (
    BatchCompileRequest,
    BatchCompileResult,
    CompileRequest,
    CompileResult,
    get_compiler_factory,
)
from .compiler_registry   import CompilationRecord, get_compiler_registry
from .dependency_resolver import DependencyGraph, get_dependency_resolver
from .metadata_generator  import CompilationMetadata, get_metadata_generator
from .ontology_compiler   import get_ontology_compiler
from ..cache.ontology_cache             import get_ontology_cache
from ..loader.ontology_loader           import get_ontology_loader
from ..registry.ontology_registry_manager import get_registry_manager
from ..ontology_registry                import get_ontology_registry
from ..runtime.runtime_object import CompiledOntology, OntologyDocument, OntologyTypeDef

__all__ = [
    "CompilerManager",
    "get_compiler_manager",
    "reset_compiler_manager",
]

_LOG  = logging.getLogger("iios.ontology.compiler.manager")
_lock = threading.Lock()
_mgr: Optional["CompilerManager"] = None


class CompilerManager:
    """
    Orchestrates the full Ontology Compiler & Loader pipeline.

    Wires together:
    - OntologyLoader        (load raw documents)
    - DependencyResolver    (build dependency graph, topological order)
    - OntologyCompiler      (compile with inherited type resolution)
    - MetadataGenerator     (generate runtime metadata)
    - CompilerRegistry      (record every compilation)
    - OntologyCache         (cache compiled artefacts)
    - OntologyRegistryManager (register live types for querying)
    """

    def __init__(self) -> None:
        self._lock        = threading.RLock()
        self._initialized = False
        # Track accumulated types across compilations (for cross-doc inheritance)
        self._all_types:  dict[str, OntologyTypeDef] = {}

    # ── Initialization ────────────────────────────────────────────────────────

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    # ── Single document compilation ───────────────────────────────────────────

    def compile_one(
        self,
        request:    CompileRequest,
        overwrite:  bool = False,
    ) -> CompileResult:
        """
        Compile a single OntologyDocument.

        Thread-safe. Records result in registry and updates cache.
        """
        factory  = get_compiler_factory()
        compiler = get_ontology_compiler()
        meta_gen = get_metadata_generator()
        reg      = get_compiler_registry()
        cache    = get_ontology_cache()
        ont_reg  = get_ontology_registry()
        rm       = get_registry_manager()

        name = request.name

        # Early-out: already compiled and no overwrite
        if reg.is_compiled(name) and not request.overwrite and not overwrite:
            existing = cache.get(name)
            if existing:
                existing_meta = reg.get_metadata(name)
                return factory.make_result(
                    request     = request,
                    compiled    = existing,
                    success     = True,
                    duration_ms = 0.0,
                    phase       = LoadPhase.COMPLETE,
                    build_id    = existing_meta.build_id if existing_meta else "",
                )

        ctx = get_compiler_context()
        reg.register_start(name)
        t0  = time.perf_counter()

        with ctx.compilation(name):
            try:
                compiled = compiler.compile(
                    request.document,
                    external_types=request.external_types,
                )
                duration_ms = (time.perf_counter() - t0) * 1_000.0
                metadata    = meta_gen.generate(
                    compiled,
                    duration_ms    = duration_ms,
                    tags           = request.tags,
                    extra          = request.metadata_extra,
                )

                # Persist
                cache.put(name, compiled)
                rm.register_compiled(compiled)
                ont_reg.register_compiled(compiled, overwrite=True)

                # Update accumulated type pool
                with self._lock:
                    self._all_types.update(compiled.types)

                rec = reg.register_success(name, compiled, metadata, duration_ms)
                _LOG.info(
                    "Compiled %r in %.1fms: %d types, %d warnings",
                    name, duration_ms, compiled.type_count, len(compiled.warnings),
                )
                return factory.make_result(
                    request     = request,
                    compiled    = compiled,
                    success     = True,
                    duration_ms = duration_ms,
                    phase       = LoadPhase.COMPLETE,
                    warnings    = compiled.warnings,
                    build_id    = metadata.build_id,
                )

            except Exception as exc:
                duration_ms = (time.perf_counter() - t0) * 1_000.0
                reg.register_failure(name, str(exc), duration_ms)
                _LOG.error("Compilation of %r failed: %s", name, exc)
                return factory.make_result(
                    request     = request,
                    compiled    = None,
                    success     = False,
                    duration_ms = duration_ms,
                    phase       = LoadPhase.FAILED,
                    error       = str(exc),
                )

    # ── Batch compilation ─────────────────────────────────────────────────────

    def compile_batch(
        self,
        batch: BatchCompileRequest,
    ) -> BatchCompileResult:
        """
        Compile a batch of documents according to the batch strategy.

        Supports SEQUENTIAL and PARALLEL strategies.
        INCREMENTAL and LAZY delegate to compile_one with cache checks.
        """
        factory = get_compiler_factory()
        t0      = time.perf_counter()

        if batch.strategy == CompilationStrategy.PARALLEL:
            results = self._compile_parallel(batch)
        else:
            results = self._compile_sequential(batch)

        total_ms = (time.perf_counter() - t0) * 1_000.0
        return factory.make_batch_result(batch, results, total_ms)

    def _compile_sequential(
        self,
        batch: BatchCompileRequest,
    ) -> list[CompileResult]:
        results: list[CompileResult] = []
        for req in batch.requests:
            result = self.compile_one(req)
            results.append(result)
            if batch.fail_fast and not result.success:
                _LOG.error("Sequential batch aborted (fail_fast): %s failed", req.name)
                break
        return results

    def _compile_parallel(
        self,
        batch: BatchCompileRequest,
    ) -> list[CompileResult]:
        """
        Compile independent requests concurrently using a thread pool.
        Requests that have no inter-dependencies can run in parallel.
        """
        results: dict[int, CompileResult] = {}
        max_workers = min(MAX_PARALLEL_COMPILATIONS, len(batch.requests))

        def _compile(idx_req: tuple[int, CompileRequest]) -> tuple[int, CompileResult]:
            idx, req = idx_req
            return idx, self.compile_one(req)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_compile, (i, req)): i
                       for i, req in enumerate(batch.requests)}
            for future in concurrent.futures.as_completed(futures):
                try:
                    idx, result = future.result()
                    results[idx] = result
                    if batch.fail_fast and not result.success:
                        for f in futures:
                            f.cancel()
                        break
                except Exception as exc:
                    _LOG.error("Parallel compile future raised: %s", exc)

        return [results[i] for i in sorted(results)]

    # ── Built-in ontology loading ─────────────────────────────────────────────

    def compile_builtins(
        self,
        strategy:  CompilationStrategy = CompilationStrategy.SEQUENTIAL,
        overwrite: bool                = False,
    ) -> BatchCompileResult:
        """
        Load and compile all 7 built-in ontologies in dependency order.

        This is the standard bootstrap path used by OntologyRuntimeEngine.
        """
        loader   = get_ontology_loader()
        factory  = get_compiler_factory()
        resolver = get_dependency_resolver()

        # Load all raw documents first
        docs: dict[str, OntologyDocument] = {}
        for name in BUILTIN_COMPILE_ORDER:
            try:
                doc       = loader.load_builtin(name)
                docs[name] = doc
            except Exception as exc:
                _LOG.error("Failed to load built-in %r: %s", name, exc)

        # Build dependency graph → topological order
        graph = resolver.build_graph(docs)
        try:
            order = resolver.topological_order(graph, check=True)
        except Exception:
            # Fall back to predefined order if graph resolution fails
            order = [n for n in BUILTIN_COMPILE_ORDER if n in docs]

        # Ensure all loaded docs are included (graph may have missed some)
        for name in docs:
            if name not in order:
                order.append(name)

        # Build requests in topological order with accumulated external types
        accumulated: dict[str, OntologyTypeDef] = {}
        requests: list[CompileRequest] = []
        for name in order:
            if name not in docs:
                continue
            req = factory.make_request(
                document       = docs[name],
                external_types = dict(accumulated),
                strategy       = strategy,
                overwrite      = overwrite,
                tags           = ["builtin"],
            )
            requests.append(req)
            # Pre-populate accumulated with what we will compile
            # (compile_one will update self._all_types after each compile)

        batch  = factory.make_batch(requests, strategy=strategy)
        result = self.compile_batch(batch)

        if result.all_succeeded:
            self._initialized = True
            _LOG.info(
                "Built-in compilation complete: %d/%d succeeded, %.1fms total",
                result.succeeded, len(result.results), result.total_ms,
            )
        else:
            _LOG.warning(
                "Built-in compilation partial: %d succeeded, %d failed",
                result.succeeded, result.failed,
            )

        return result

    # ── Incremental loading ───────────────────────────────────────────────────

    def compile_incremental(
        self,
        documents: dict[str, OntologyDocument],
        mode:      IncrementalMode = IncrementalMode.HASH_BASED,
    ) -> BatchCompileResult:
        """
        Incrementally compile only the ontologies that have changed.

        For HASH_BASED mode: compares source hash against cached metadata.
        For VERSION_BASED mode: compares version strings.
        For ALWAYS mode: recompiles everything.
        """
        factory  = get_compiler_factory()
        meta_gen = get_metadata_generator()
        reg      = get_compiler_registry()

        to_compile: dict[str, OntologyDocument] = {}

        for name, doc in documents.items():
            if mode == IncrementalMode.ALWAYS:
                to_compile[name] = doc
                continue
            if mode == IncrementalMode.NEVER:
                if reg.is_compiled(name):
                    continue
                to_compile[name] = doc
                continue

            existing_meta = reg.get_metadata(name)
            if existing_meta is None:
                to_compile[name] = doc
                continue

            if mode == IncrementalMode.HASH_BASED:
                current_hash = meta_gen._hash_document(doc)
                if current_hash != existing_meta.source_hash:
                    _LOG.debug("Incremental: %r changed (hash mismatch)", name)
                    to_compile[name] = doc
            elif mode == IncrementalMode.VERSION_BASED:
                if doc.version != doc.namespace.version:
                    to_compile[name] = doc

        if not to_compile:
            _LOG.debug("Incremental: no changes detected, nothing to recompile")
            requests = []
        else:
            accumulated = dict(self._all_types)
            requests = [
                factory.make_request(doc, external_types=accumulated, overwrite=True)
                for doc in to_compile.values()
            ]

        batch = factory.make_batch(requests)
        return self.compile_batch(batch)

    # ── Hot reload ────────────────────────────────────────────────────────────

    def hot_reload(
        self,
        name:     str,
        document: OntologyDocument,
    ) -> CompileResult:
        """
        Hot-reload a single ontology without stopping the runtime.

        Recompiles the document with the current external type universe,
        updates cache and registry atomically.
        """
        factory = get_compiler_factory()
        _LOG.info("Hot-reloading ontology %r …", name)

        with self._lock:
            ext = dict(self._all_types)
            # Remove old types from this ontology so they don't conflict
            existing = get_ontology_cache().get(name)
            if existing:
                for uri in existing.types:
                    ext.pop(uri, None)

        try:
            req    = factory.make_request(document, external_types=ext, overwrite=True)
            result = self.compile_one(req, overwrite=True)
            if result.success:
                _LOG.info("Hot-reload of %r succeeded", name)
            else:
                raise HotReloadError(name, result.error or "unknown error")
            return result
        except HotReloadError:
            raise
        except Exception as exc:
            raise HotReloadError(name, str(exc)) from exc

    # ── Selective loading ─────────────────────────────────────────────────────

    def compile_selective(
        self,
        names:     list[str],
        overwrite: bool = False,
    ) -> BatchCompileResult:
        """
        Compile a specific subset of built-in ontologies.
        Dependencies are automatically included if not already compiled.
        """
        loader   = get_ontology_loader()
        factory  = get_compiler_factory()
        resolver = get_dependency_resolver()

        # Load requested docs
        docs: dict[str, OntologyDocument] = {}
        for name in names:
            try:
                docs[name] = loader.load_builtin(name)
            except Exception as exc:
                _LOG.warning("Selective load: %r not found: %s", name, exc)

        if not docs:
            batch = factory.make_batch([])
            return factory.make_batch_result(batch, [], 0.0)

        graph = resolver.build_graph(docs)
        order = resolver.topological_order(graph, check=True)
        order = [n for n in order if n in docs]

        accumulated = dict(self._all_types)
        requests = [
            factory.make_request(docs[n], external_types=accumulated, overwrite=overwrite)
            for n in order
        ]
        batch = factory.make_batch(requests)
        return self.compile_batch(batch)

    # ── Lazy loading ──────────────────────────────────────────────────────────

    def get_or_compile(
        self,
        name: str,
    ) -> Optional[CompiledOntology]:
        """
        Return a compiled ontology, compiling it on demand if needed (lazy).
        """
        cache = get_ontology_cache()
        existing = cache.get(name)
        if existing:
            return existing

        # Try to compile on demand
        loader  = get_ontology_loader()
        factory = get_compiler_factory()
        try:
            doc = loader.load_builtin(name)
            ext = dict(self._all_types)
            req = factory.make_request(doc, external_types=ext)
            res = self.compile_one(req)
            return res.compiled if res.success else None
        except Exception as exc:
            _LOG.error("Lazy compile of %r failed: %s", name, exc)
            return None

    # ── Stats ──────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        reg   = get_compiler_registry()
        cache = get_ontology_cache()
        return {
            "initialized":    self._initialized,
            "registry":       reg.stats(),
            "cache":          cache.stats(),
            "accumulated_types": len(self._all_types),
        }

    def health(self) -> dict[str, Any]:
        s = self.stats()
        return {
            "status":         "healthy" if self._initialized else "not_initialized",
            "initialized":    self._initialized,
            "compiled_count": s["registry"]["succeeded"],
            "cache_size":     get_ontology_cache().size,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_compiler_manager() -> CompilerManager:
    global _mgr
    if _mgr is None:
        with _lock:
            if _mgr is None:
                _mgr = CompilerManager()
    return _mgr


def reset_compiler_manager() -> None:
    global _mgr
    with _lock:
        _mgr = None
