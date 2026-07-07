"""
iios/ontology/loader/compiled_loader.py
=========================================
Loads compiled ontology artefacts directly from the cache or disk,
bypassing the full compilation pipeline for warm-start scenarios.

Supports:
- Loading from in-memory LRU cache
- Loading from persistent JSON cache (disk)
- Loading from a pre-built artefact dict
- Cache key validation via metadata hashes
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from ..compiler.compiler_constants import CacheStrategy, PERSISTENT_CACHE_VERSION
from ..compiler.compiler_exceptions import CacheLoaderError, HashMismatchError
from ..compiler.metadata_generator import CompilationMetadata, get_metadata_generator
from ..cache.ontology_cache import get_ontology_cache
from ..runtime.runtime_object import (
    CompiledOntology,
    OntologyDocument,
    OntologyNamespace,
    OntologyProperty,
    OntologyRelationshipDef,
    OntologyTypeDef,
    OntologyStatus,
)
from ..ontology_constants import DEFAULT_ONTOLOGY_VERSION, OntologyCategory

__all__ = [
    "CompiledLoader",
    "get_compiled_loader",
    "reset_compiled_loader",
]

_LOG  = logging.getLogger("iios.ontology.loader.compiled")
_lock = threading.Lock()
_inst: Optional["CompiledLoader"] = None


class CompiledLoader:
    """
    Loads compiled ontology artefacts from the cache or persistent storage.

    Warm-start path: skip compilation if a valid cached artefact exists.
    Validates cache entries using metadata hashes before returning.
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        strategy:  CacheStrategy  = CacheStrategy.MEMORY,
    ) -> None:
        self._cache_dir = Path(cache_dir) if cache_dir else None
        self._strategy  = strategy
        self._meta_gen  = get_metadata_generator()

    # ── Memory cache ──────────────────────────────────────────────────────────

    def load_from_memory(self, name: str) -> Optional[CompiledOntology]:
        """Load from the in-memory LRU cache."""
        return get_ontology_cache().get(name)

    def is_cached(self, name: str) -> bool:
        """Return True if the compiled ontology is in the memory cache."""
        return get_ontology_cache().has(name)

    # ── Persistent cache (JSON) ───────────────────────────────────────────────

    def save_to_disk(
        self,
        compiled: CompiledOntology,
        metadata: Optional[CompilationMetadata] = None,
    ) -> Optional[Path]:
        """
        Save a compiled artefact to the persistent cache directory as JSON.

        Returns the path written, or None if no cache_dir is configured.
        """
        if self._cache_dir is None:
            return None
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            path = self._cache_dir / f"{compiled.name}.json"

            payload: dict[str, Any] = {
                "_version":  PERSISTENT_CACHE_VERSION,
                "_saved_at": time.time(),
                "compiled":  self._compiled_to_dict(compiled),
                "metadata":  metadata.to_dict() if metadata else None,
            }
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            _LOG.debug("Saved compiled %r to %s", compiled.name, path)
            return path
        except Exception as exc:
            raise CacheLoaderError(f"Failed to save {compiled.name!r} to disk: {exc}") from exc

    def load_from_disk(
        self,
        name:     str,
        validate: bool = True,
    ) -> Optional[CompiledOntology]:
        """
        Load a compiled artefact from the persistent cache directory.

        Args:
            name:     Ontology name (file will be <cache_dir>/<name>.json).
            validate: If True, validate the schema hash matches the artefact.

        Returns:
            CompiledOntology if found and valid, else None.
        """
        if self._cache_dir is None:
            return None
        path = self._cache_dir / f"{name}.json"
        if not path.exists():
            return None

        try:
            payload  = json.loads(path.read_text(encoding="utf-8"))
            version  = payload.get("_version", 0)
            if version != PERSISTENT_CACHE_VERSION:
                _LOG.debug("Disk cache version mismatch for %r, skipping", name)
                return None

            compiled = self._compiled_from_dict(payload["compiled"])
            if validate and payload.get("metadata"):
                meta = CompilationMetadata.from_dict(payload["metadata"])
                self._meta_gen.validate(compiled, meta)

            _LOG.debug("Loaded compiled %r from disk cache", name)
            return compiled
        except HashMismatchError:
            _LOG.warning("Hash mismatch for disk-cached %r — discarding", name)
            path.unlink(missing_ok=True)
            return None
        except Exception as exc:
            _LOG.warning("Failed to load %r from disk cache: %s", name, exc)
            return None

    # ── Two-level cache ───────────────────────────────────────────────────────

    def load(
        self,
        name:     str,
        validate: bool = True,
    ) -> Optional[CompiledOntology]:
        """
        Load using the configured cache strategy.

        TWO_LEVEL: check memory, then disk, then return None.
        MEMORY:    check memory only.
        PERSISTENT: check disk only.
        """
        if self._strategy in (CacheStrategy.MEMORY, CacheStrategy.TWO_LEVEL):
            cached = self.load_from_memory(name)
            if cached:
                return cached

        if self._strategy in (CacheStrategy.PERSISTENT, CacheStrategy.TWO_LEVEL):
            disk = self.load_from_disk(name, validate=validate)
            if disk:
                # Populate memory cache for subsequent access
                if self._strategy == CacheStrategy.TWO_LEVEL:
                    get_ontology_cache().put(name, disk)
                return disk

        return None

    # ── Serialisation helpers ──────────────────────────────────────────────────

    @staticmethod
    def _compiled_to_dict(compiled: CompiledOntology) -> dict[str, Any]:
        """Serialise a CompiledOntology to a JSON-compatible dict."""
        return {
            "document":       compiled.document.to_dict(),
            "compiled_at":    compiled.compiled_at,
            "status":         compiled.status.value,
            "types":          {k: v.to_dict() for k, v in compiled.types.items()},
            "relationships":  {k: v.to_dict() for k, v in compiled.relationships.items()},
            "property_index": {
                k: {pk: pv.to_dict() for pk, pv in props.items()}
                for k, props in compiled.property_index.items()
            },
            "children":  {k: list(v) for k, v in compiled.children.items()},
            "alias_index": dict(compiled.alias_index),
            "warnings":   list(compiled.warnings),
        }

    @staticmethod
    def _compiled_from_dict(d: dict[str, Any]) -> CompiledOntology:
        """Deserialise a CompiledOntology from a dict."""
        from ..loader.resource_loader import ResourceLoader
        doc_data  = d["document"]
        ns_data   = doc_data.get("namespace", {})
        namespace = OntologyNamespace.from_dict(ns_data)

        types: dict[str, OntologyTypeDef] = {
            k: OntologyTypeDef.from_dict(v)
            for k, v in doc_data.get("types", {}).items()
        }
        relationships: dict[str, OntologyRelationshipDef] = {
            k: OntologyRelationshipDef.from_dict(v)
            for k, v in doc_data.get("relationships", {}).items()
        }
        document = OntologyDocument(
            uri           = doc_data.get("uri", ""),
            name          = doc_data.get("name", ""),
            namespace     = namespace,
            version       = doc_data.get("version", DEFAULT_ONTOLOGY_VERSION),
            category      = OntologyCategory(doc_data.get("category", OntologyCategory.INFORMATION.value)),
            description   = doc_data.get("description", ""),
            types         = types,
            relationships = relationships,
            imports       = list(doc_data.get("imports", [])),
        )

        comp_types: dict[str, OntologyTypeDef] = {
            k: OntologyTypeDef.from_dict(v) for k, v in d.get("types", {}).items()
        }
        comp_rels: dict[str, OntologyRelationshipDef] = {
            k: OntologyRelationshipDef.from_dict(v) for k, v in d.get("relationships", {}).items()
        }
        property_index: dict[str, dict[str, OntologyProperty]] = {
            k: {pk: OntologyProperty.from_dict(pv) for pk, pv in props.items()}
            for k, props in d.get("property_index", {}).items()
        }
        children: dict[str, set[str]] = {
            k: set(v) for k, v in d.get("children", {}).items()
        }

        return CompiledOntology(
            document       = document,
            compiled_at    = d.get("compiled_at", time.time()),
            status         = OntologyStatus(d.get("status", OntologyStatus.COMPILED.value)),
            types          = comp_types,
            relationships  = comp_rels,
            property_index = property_index,
            children       = children,
            alias_index    = dict(d.get("alias_index", {})),
            warnings       = list(d.get("warnings", [])),
        )


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_compiled_loader(
    cache_dir: Optional[str] = None,
    strategy:  CacheStrategy  = CacheStrategy.MEMORY,
) -> CompiledLoader:
    global _inst
    if _inst is None:
        with _lock:
            if _inst is None:
                _inst = CompiledLoader(cache_dir=cache_dir, strategy=strategy)
    return _inst


def reset_compiled_loader() -> None:
    global _inst
    with _lock:
        _inst = None
