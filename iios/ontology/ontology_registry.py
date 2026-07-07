"""
iios/ontology/ontology_registry.py
=====================================
The OntologyRegistry is the module-level catalogue of all ontology
documents and their compiled artefacts, separated from the per-domain
registry views (entity_registry, etc.).

This is the authoritative source for "which ontologies are loaded and
what is their current status".
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from .ontology_constants  import OntologyStatus
from .ontology_exceptions import OntologyNotFoundError, OntologyAlreadyLoadedError
from .runtime.runtime_object import CompiledOntology, OntologyDocument

__all__ = [
    "OntologyRegistry",
    "get_ontology_registry",
    "reset_ontology_registry",
]

_LOG  = logging.getLogger("iios.ontology.registry")
_lock = threading.Lock()
_reg: Optional["OntologyRegistry"] = None


class OntologyRegistry:
    """
    Module-level catalogue of all loaded and compiled ontologies.

    Separate concern from OntologyRegistryManager (which handles
    type-level lookups) — this tracks document-level lifecycle.
    """

    def __init__(self) -> None:
        self._lock     = threading.RLock()
        self._docs:     dict[str, OntologyDocument] = {}
        self._compiled: dict[str, CompiledOntology] = {}
        self._status:   dict[str, OntologyStatus]   = {}

    # ── Document registration ──────────────────────────────────────────────────

    def register_document(
        self,
        doc:       OntologyDocument,
        overwrite: bool = False,
    ) -> None:
        with self._lock:
            if doc.name in self._docs and not overwrite:
                raise OntologyAlreadyLoadedError(doc.name)
            self._docs[doc.name]   = doc
            self._status[doc.name] = OntologyStatus.LOADED

    def register_compiled(
        self,
        compiled:  CompiledOntology,
        overwrite: bool = True,
    ) -> None:
        with self._lock:
            name = compiled.name
            self._compiled[name] = compiled
            self._docs[name]     = compiled.document
            self._status[name]   = OntologyStatus.ACTIVE

    # ── Retrieval ──────────────────────────────────────────────────────────────

    def get_document(self, name: str) -> OntologyDocument:
        with self._lock:
            doc = self._docs.get(name)
        if doc is None:
            raise OntologyNotFoundError(name)
        return doc

    def get_compiled(self, name: str) -> Optional[CompiledOntology]:
        with self._lock:
            return self._compiled.get(name)

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._docs

    def is_compiled(self, name: str) -> bool:
        with self._lock:
            return name in self._compiled

    # ── Listing ────────────────────────────────────────────────────────────────

    def all_names(self) -> list[str]:
        with self._lock:
            return list(self._docs.keys())

    def compiled_names(self) -> list[str]:
        with self._lock:
            return list(self._compiled.keys())

    def status(self, name: str) -> OntologyStatus:
        with self._lock:
            return self._status.get(name, OntologyStatus.UNLOADED)

    def all_compiled(self) -> list[CompiledOntology]:
        with self._lock:
            return list(self._compiled.values())

    # ── Stats ──────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        with self._lock:
            return {
                "total_documents": len(self._docs),
                "total_compiled":  len(self._compiled),
                "active":          sum(1 for s in self._status.values() if s == OntologyStatus.ACTIVE),
            }

    def clear(self) -> None:
        with self._lock:
            self._docs.clear()
            self._compiled.clear()
            self._status.clear()


def get_ontology_registry() -> OntologyRegistry:
    global _reg
    if _reg is None:
        with _lock:
            if _reg is None:
                _reg = OntologyRegistry()
    return _reg


def reset_ontology_registry() -> None:
    global _reg
    with _lock:
        _reg = None
