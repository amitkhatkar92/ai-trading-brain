"""
iios/ontology/compiler/metadata_generator.py
==============================================
Generates rich runtime metadata for compiled ontology artefacts.

Metadata includes:
- Compilation timestamps and duration
- Source + schema hashes (for cache validation)
- Dependency fingerprints
- Build IDs (deterministic UUID from content)
- Type / property / relationship counts
- Compiler version information
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .compiler_constants import (
    COMPILER_VERSION,
    METADATA_HASH_TRUNCATE,
    METADATA_VERSION,
    MetadataField,
    SCHEMA_HASH_ALGORITHM,
)
from .compiler_exceptions import MetadataError
from ..runtime.runtime_object import CompiledOntology, OntologyDocument

__all__ = [
    "CompilationMetadata",
    "MetadataGenerator",
    "get_metadata_generator",
    "reset_metadata_generator",
]

_LOG = logging.getLogger("iios.ontology.compiler.metadata")


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class CompilationMetadata:
    """
    Runtime metadata attached to every compiled ontology artefact.

    Immutable after creation — once compiled, the metadata is the
    ground truth about what was produced and when.
    """
    ont_name:        str
    compiled_at:     float
    compiler_version: str
    metadata_version: str
    source_hash:     str           # Hash of the raw document dict
    schema_hash:     str           # Hash of the type structure
    build_id:        str           # Deterministic UUID from content
    type_count:      int
    rel_count:       int
    prop_count:      int
    warning_count:   int
    duration_ms:     float
    dependency_ids:  list[str]     = field(default_factory=list)
    tags:            list[str]     = field(default_factory=list)
    extra:           dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            MetadataField.COMPILED_AT.value:    self.compiled_at,
            MetadataField.COMPILER_VER.value:   self.compiler_version,
            MetadataField.SOURCE_HASH.value:    self.source_hash,
            MetadataField.SCHEMA_HASH.value:    self.schema_hash,
            MetadataField.DEPENDENCY_IDS.value: list(self.dependency_ids),
            MetadataField.TYPE_COUNT.value:     self.type_count,
            MetadataField.REL_COUNT.value:      self.rel_count,
            MetadataField.PROP_COUNT.value:     self.prop_count,
            MetadataField.BUILD_ID.value:       self.build_id,
            MetadataField.WARNINGS.value:       self.warning_count,
            MetadataField.DURATION_MS.value:    round(self.duration_ms, 3),
            "ont_name":                         self.ont_name,
            "metadata_version":                 self.metadata_version,
            "tags":                             list(self.tags),
            "extra":                            dict(self.extra),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CompilationMetadata":
        return cls(
            ont_name         = d.get("ont_name", ""),
            compiled_at      = d.get(MetadataField.COMPILED_AT.value, 0.0),
            compiler_version = d.get(MetadataField.COMPILER_VER.value, COMPILER_VERSION),
            metadata_version = d.get("metadata_version", METADATA_VERSION),
            source_hash      = d.get(MetadataField.SOURCE_HASH.value, ""),
            schema_hash      = d.get(MetadataField.SCHEMA_HASH.value, ""),
            build_id         = d.get(MetadataField.BUILD_ID.value, ""),
            type_count       = int(d.get(MetadataField.TYPE_COUNT.value, 0)),
            rel_count        = int(d.get(MetadataField.REL_COUNT.value, 0)),
            prop_count       = int(d.get(MetadataField.PROP_COUNT.value, 0)),
            warning_count    = int(d.get(MetadataField.WARNINGS.value, 0)),
            duration_ms      = float(d.get(MetadataField.DURATION_MS.value, 0.0)),
            dependency_ids   = list(d.get(MetadataField.DEPENDENCY_IDS.value, [])),
            tags             = list(d.get("tags", [])),
            extra            = dict(d.get("extra", {})),
        )


# ── Generator ─────────────────────────────────────────────────────────────────

class MetadataGenerator:
    """
    Generates CompilationMetadata for a compiled ontology artefact.

    Stateless — safe to call from multiple threads simultaneously.
    """

    # ── Hash helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _md5(data: bytes) -> str:
        return hashlib.md5(data, usedforsecurity=False).hexdigest()[:METADATA_HASH_TRUNCATE]

    @staticmethod
    def _hash_document(doc: OntologyDocument) -> str:
        """Stable hash of the raw document (namespace + type names + versions)."""
        payload = json.dumps({
            "name":      doc.name,
            "namespace": doc.namespace.uri,
            "version":   doc.namespace.version,
            "types":     sorted(doc.types.keys()),
            "rels":      sorted(doc.relationships.keys()),
        }, sort_keys=True).encode()
        return hashlib.md5(payload, usedforsecurity=False).hexdigest()[:METADATA_HASH_TRUNCATE]

    @staticmethod
    def _hash_schema(compiled: CompiledOntology) -> str:
        """Hash of the compiled type structure (URIs + property names)."""
        type_summaries = {
            uri: sorted(props.keys())
            for uri, props in compiled.property_index.items()
        }
        payload = json.dumps(type_summaries, sort_keys=True).encode()
        return hashlib.md5(payload, usedforsecurity=False).hexdigest()[:METADATA_HASH_TRUNCATE]

    @staticmethod
    def _build_id(
        ont_name:    str,
        source_hash: str,
        schema_hash: str,
        compiled_at: float,
    ) -> str:
        """
        Deterministic build ID: UUID5 of the content fingerprint.
        Same source + schema → same build_id (for cache keying).
        """
        fingerprint = f"{ont_name}:{source_hash}:{schema_hash}"
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, fingerprint))

    # ── Property count helper ─────────────────────────────────────────────────

    @staticmethod
    def _count_properties(compiled: CompiledOntology) -> int:
        """Total resolved properties across all types."""
        return sum(len(props) for props in compiled.property_index.values())

    # ── Main generation ───────────────────────────────────────────────────────

    def generate(
        self,
        compiled:      CompiledOntology,
        duration_ms:   float = 0.0,
        dependency_ids: Optional[list[str]] = None,
        tags:          Optional[list[str]]  = None,
        extra:         Optional[dict[str, Any]] = None,
    ) -> CompilationMetadata:
        """
        Generate full CompilationMetadata for a compiled ontology.

        Args:
            compiled:       The compiled artefact.
            duration_ms:    How long compilation took in milliseconds.
            dependency_ids: Build IDs of dependency ontologies (for chain hashing).
            tags:           Optional free-form tags.
            extra:          Additional key-value metadata.

        Returns:
            CompilationMetadata instance.
        """
        try:
            source_hash = self._hash_document(compiled.document)
            schema_hash = self._hash_schema(compiled)
            build_id    = self._build_id(
                compiled.name, source_hash, schema_hash, compiled.compiled_at
            )
            prop_count  = self._count_properties(compiled)

            return CompilationMetadata(
                ont_name         = compiled.name,
                compiled_at      = compiled.compiled_at,
                compiler_version = COMPILER_VERSION,
                metadata_version = METADATA_VERSION,
                source_hash      = source_hash,
                schema_hash      = schema_hash,
                build_id         = build_id,
                type_count       = compiled.type_count,
                rel_count        = len(compiled.relationships),
                prop_count       = prop_count,
                warning_count    = len(compiled.warnings),
                duration_ms      = duration_ms,
                dependency_ids   = list(dependency_ids or []),
                tags             = list(tags or []),
                extra            = dict(extra or {}),
            )
        except Exception as exc:
            raise MetadataError(str(exc)) from exc

    def validate(
        self,
        compiled:  CompiledOntology,
        metadata:  CompilationMetadata,
    ) -> bool:
        """
        Verify that the metadata matches the compiled artefact.
        Returns True if valid, raises HashMismatchError if not.
        """
        from .compiler_exceptions import HashMismatchError
        expected_schema = self._hash_schema(compiled)
        if expected_schema != metadata.schema_hash:
            raise HashMismatchError(
                compiled.name, metadata.schema_hash, expected_schema
            )
        return True

    def chain_hash(self, metadata_list: list[CompilationMetadata]) -> str:
        """
        Produce a single hash that represents an entire compilation chain.
        Useful for validating that a complete build set is consistent.
        """
        ids     = sorted(m.build_id for m in metadata_list)
        payload = ":".join(ids).encode()
        return hashlib.md5(payload, usedforsecurity=False).hexdigest()[:METADATA_HASH_TRUNCATE]


# ── Singleton ─────────────────────────────────────────────────────────────────

import threading as _threading
_lock = _threading.Lock()
_gen: Optional["MetadataGenerator"] = None


def get_metadata_generator() -> MetadataGenerator:
    global _gen
    if _gen is None:
        with _lock:
            if _gen is None:
                _gen = MetadataGenerator()
    return _gen


def reset_metadata_generator() -> None:
    global _gen
    with _lock:
        _gen = None
