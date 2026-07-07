"""
iios/ontology/loader/ontology_loader.py
=========================================
Orchestrates loading of ontology documents from all sources:
built-in (document_loader.py), external JSON/dict (resource_loader.py).

Supports lazy and eager loading strategies.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from ..ontology_constants import (
    BUILTIN_ONTOLOGY_NAMES,
    LoadStrategy,
    OntologyStatus,
)
from ..ontology_exceptions import (
    OntologyAlreadyLoadedError,
    OntologyLoadError,
    OntologyNotFoundError,
)
from ..runtime.runtime_object import OntologyDocument
from .document_loader import load_builtin_document
from .resource_loader import ResourceLoader
from .schema_loader   import validate_document

__all__ = [
    "OntologyLoader",
    "get_ontology_loader",
    "reset_ontology_loader",
]

_LOG  = logging.getLogger("iios.ontology.loader")
_lock = threading.Lock()
_loader_inst: Optional["OntologyLoader"] = None


class OntologyLoader:
    """
    Central loader for all ontology documents.

    Responsibilities:
    - Load built-in documents from document_loader.py
    - Load user-defined documents from dicts / JSON files
    - Validate each document via schema_loader.py
    - Track load status per document name
    - Prevent duplicate loads (overwrite=False by default)
    """

    def __init__(self) -> None:
        self._lock      = threading.RLock()
        self._documents: dict[str, OntologyDocument] = {}
        self._status:   dict[str, OntologyStatus]    = {}
        self._resource_loader = ResourceLoader()

    # ── Builtin loading ────────────────────────────────────────────────────────

    def load_builtin(
        self,
        name:      str,
        overwrite: bool = False,
    ) -> OntologyDocument:
        """
        Load a named built-in ontology.

        Args:
            name:      One of the BUILTIN_ONTOLOGY_NAMES constants.
            overwrite: If True, reload even if already loaded.

        Returns:
            The loaded OntologyDocument.
        """
        with self._lock:
            if name in self._documents and not overwrite:
                return self._documents[name]

            self._status[name] = OntologyStatus.LOADING
            try:
                doc      = load_builtin_document(name)
                warnings = validate_document(doc)
                if warnings:
                    for w in warnings:
                        _LOG.debug("Schema warning in %s: %s", name, w)
                self._documents[name] = doc
                self._status[name]   = OntologyStatus.LOADED
                _LOG.info("Loaded built-in ontology %r (%d types)", name, doc.type_count)
                return doc
            except Exception as exc:
                self._status[name] = OntologyStatus.ERROR
                raise OntologyLoadError(str(exc), ont_name=name) from exc

    def load_all_builtins(self, overwrite: bool = False) -> list[OntologyDocument]:
        """Load all built-in ontologies and return them in definition order."""
        results: list[OntologyDocument] = []
        for name in BUILTIN_ONTOLOGY_NAMES:
            results.append(self.load_builtin(name, overwrite=overwrite))
        return results

    # ── User-defined loading ───────────────────────────────────────────────────

    def load_from_dict(
        self,
        data:      dict,
        name:      Optional[str] = None,
        overwrite: bool           = False,
    ) -> OntologyDocument:
        """Load an ontology from a raw dictionary."""
        doc_name = name or data.get("name", "UNKNOWN")
        with self._lock:
            if doc_name in self._documents and not overwrite:
                raise OntologyAlreadyLoadedError(doc_name)
            self._status[doc_name] = OntologyStatus.LOADING
            try:
                doc      = self._resource_loader.load(data)
                warnings = validate_document(doc)
                for w in warnings:
                    _LOG.debug("Schema warning in %s: %s", doc_name, w)
                self._documents[doc_name] = doc
                self._status[doc_name]   = OntologyStatus.LOADED
                _LOG.info("Loaded user ontology %r (%d types)", doc_name, doc.type_count)
                return doc
            except OntologyAlreadyLoadedError:
                raise
            except Exception as exc:
                self._status[doc_name] = OntologyStatus.ERROR
                raise OntologyLoadError(str(exc), ont_name=doc_name) from exc

    def load_from_json_file(
        self,
        path:      str,
        name:      Optional[str] = None,
        overwrite: bool           = False,
    ) -> OntologyDocument:
        """Load an ontology from a JSON file."""
        from .resource_loader import load_from_json_file
        data     = {}
        # Peek at file for the name key
        import json
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:
            raise OntologyLoadError(f"Cannot read {path!r}: {exc}") from exc
        return self.load_from_dict(data, name=name or data.get("name"), overwrite=overwrite)

    # ── Retrieval ──────────────────────────────────────────────────────────────

    def get(self, name: str) -> OntologyDocument:
        """Return a loaded document by name. Raises OntologyNotFoundError."""
        doc = self._documents.get(name)
        if doc is None:
            raise OntologyNotFoundError(name)
        return doc

    def get_or_none(self, name: str) -> Optional[OntologyDocument]:
        return self._documents.get(name)

    def has(self, name: str) -> bool:
        return name in self._documents

    # ── Status ─────────────────────────────────────────────────────────────────

    def status(self, name: str) -> OntologyStatus:
        return self._status.get(name, OntologyStatus.UNLOADED)

    def all_names(self) -> list[str]:
        return list(self._documents.keys())

    def all_documents(self) -> list[OntologyDocument]:
        return list(self._documents.values())

    def count(self) -> int:
        return len(self._documents)

    # ── Reset ──────────────────────────────────────────────────────────────────

    def clear(self) -> None:
        with self._lock:
            self._documents.clear()
            self._status.clear()

    def stats(self) -> dict:
        return {
            "loaded":  sum(1 for s in self._status.values() if s == OntologyStatus.LOADED),
            "error":   sum(1 for s in self._status.values() if s == OntologyStatus.ERROR),
            "total":   len(self._documents),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_ontology_loader() -> OntologyLoader:
    global _loader_inst
    if _loader_inst is None:
        with _lock:
            if _loader_inst is None:
                _loader_inst = OntologyLoader()
    return _loader_inst


def reset_ontology_loader() -> None:
    global _loader_inst
    with _lock:
        _loader_inst = None
