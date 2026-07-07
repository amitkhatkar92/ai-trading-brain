"""
iios/ontology/loader/incremental_loader.py
============================================
Incremental loader — detects and recompiles only changed ontologies.

Detects changes via:
- Source hash comparison (default, most accurate)
- Version string comparison
- Force-all mode

Supports partial rebuilds: if ontology A changes, only A and its
dependents are recompiled. Unchanged ontologies are left as-is.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..compiler.compiler_constants import IncrementalMode
from ..compiler.compiler_manager    import get_compiler_manager
from ..compiler.compiler_registry   import get_compiler_registry
from ..compiler.metadata_generator  import get_metadata_generator
from ..compiler.dependency_resolver import get_dependency_resolver
from ..cache.ontology_cache         import get_ontology_cache
from ..loader.ontology_loader       import get_ontology_loader
from ..runtime.runtime_object       import CompiledOntology, OntologyDocument

__all__ = [
    "IncrementalResult",
    "IncrementalLoader",
    "get_incremental_loader",
    "reset_incremental_loader",
]

_LOG  = logging.getLogger("iios.ontology.loader.incremental")
_lock = threading.Lock()
_inst: Optional["IncrementalLoader"] = None


@dataclass
class IncrementalResult:
    """Summary of an incremental load operation."""
    recompiled:  list[str]   = field(default_factory=list)
    skipped:     list[str]   = field(default_factory=list)
    failed:      list[str]   = field(default_factory=list)
    errors:      dict[str, str] = field(default_factory=dict)
    total_ms:    float         = 0.0
    mode:        str           = "hash_based"

    @property
    def changed_count(self) -> int:
        return len(self.recompiled)

    @property
    def all_succeeded(self) -> bool:
        return len(self.failed) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode":        self.mode,
            "recompiled":  list(self.recompiled),
            "skipped":     list(self.skipped),
            "failed":      list(self.failed),
            "total_ms":    round(self.total_ms, 3),
        }


class IncrementalLoader:
    """
    Detects changed ontologies and recompiles only those plus their dependents.
    """

    def __init__(self) -> None:
        # Remember last-known source hashes
        self._source_hashes: dict[str, str] = {}

    # ── Change detection ──────────────────────────────────────────────────────

    def detect_changes(
        self,
        documents: dict[str, OntologyDocument],
        mode:      IncrementalMode = IncrementalMode.HASH_BASED,
    ) -> list[str]:
        """
        Return the list of ontology names that have changed since last compile.
        """
        meta_gen = get_metadata_generator()
        changed: list[str] = []

        for name, doc in documents.items():
            if mode == IncrementalMode.ALWAYS:
                changed.append(name)
                continue
            if mode == IncrementalMode.NEVER:
                continue

            current_hash = meta_gen._hash_document(doc)
            last_hash    = self._source_hashes.get(name)

            if last_hash is None or current_hash != last_hash:
                changed.append(name)

        return changed

    def _expand_with_dependents(
        self,
        changed:   list[str],
        documents: dict[str, OntologyDocument],
    ) -> list[str]:
        """
        Given a set of changed ontology names, return the expanded set
        that includes all dependents (ontologies that depend on a changed one).
        """
        resolver = get_dependency_resolver()
        graph    = resolver.build_graph(documents)

        expanded: set[str] = set(changed)
        for name in changed:
            # All ontologies that directly or transitively depend on this one
            dependents = set()
            to_visit   = list(graph.rev.get(name, set()))
            visited: set[str] = set()
            while to_visit:
                dep = to_visit.pop()
                if dep in visited:
                    continue
                visited.add(dep)
                dependents.add(dep)
                to_visit.extend(graph.rev.get(dep, set()))
            expanded.update(dependents)

        # Return in topological order
        order = resolver.topological_order(graph, check=False)
        return [n for n in order if n in expanded]

    # ── Incremental compile ────────────────────────────────────────────────────

    def incremental_compile(
        self,
        documents: Optional[dict[str, OntologyDocument]] = None,
        mode:      IncrementalMode = IncrementalMode.HASH_BASED,
    ) -> IncrementalResult:
        """
        Detect changes and recompile affected ontologies only.

        Args:
            documents: The current document set to check. If None, loads all builtins.
            mode:      How to detect changes.

        Returns:
            IncrementalResult describing what was done.
        """
        t0  = time.perf_counter()
        mgr = get_compiler_manager()

        if documents is None:
            loader    = get_ontology_loader()
            doc_list  = loader.load_all_builtins(overwrite=False)
            documents = {d.name: d for d in doc_list}

        changed  = self.detect_changes(documents, mode)
        to_build = self._expand_with_dependents(changed, documents)

        result = IncrementalResult(mode=mode.value)
        meta_gen = get_metadata_generator()

        for name in documents:
            if name not in to_build:
                result.skipped.append(name)

        if to_build:
            _LOG.info(
                "Incremental: %d changed, %d to rebuild: %s",
                len(changed), len(to_build), to_build,
            )
            batch_result = mgr.compile_incremental(
                {n: documents[n] for n in to_build if n in documents},
                mode=mode,
            )
            for r in batch_result.results:
                if r.success:
                    result.recompiled.append(r.name)
                    # Record new hash
                    if r.name in documents:
                        h = meta_gen._hash_document(documents[r.name])
                        self._source_hashes[r.name] = h
                else:
                    result.failed.append(r.name)
                    result.errors[r.name] = r.error or "unknown"
        else:
            _LOG.debug("Incremental: no changes detected")

        result.total_ms = (time.perf_counter() - t0) * 1_000.0
        return result

    # ── Hot reload single ──────────────────────────────────────────────────────

    def hot_reload(
        self,
        name:     str,
        document: OntologyDocument,
    ) -> bool:
        """
        Hot-reload a single ontology document without stopping the runtime.

        Returns True if successful.
        """
        meta_gen = get_metadata_generator()
        try:
            mgr = get_compiler_manager()
            res = mgr.hot_reload(name, document)
            if res.success:
                h = meta_gen._hash_document(document)
                self._source_hashes[name] = h
                return True
            return False
        except Exception as exc:
            _LOG.error("Hot reload of %r failed: %s", name, exc)
            return False

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot(self) -> dict[str, str]:
        """Return a copy of the current source hash snapshot."""
        return dict(self._source_hashes)

    def reset_snapshot(self) -> None:
        """Clear all stored source hashes (forces full rebuild on next check)."""
        self._source_hashes.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_incremental_loader() -> IncrementalLoader:
    global _inst
    if _inst is None:
        with _lock:
            if _inst is None:
                _inst = IncrementalLoader()
    return _inst


def reset_incremental_loader() -> None:
    global _inst
    with _lock:
        _inst = None
