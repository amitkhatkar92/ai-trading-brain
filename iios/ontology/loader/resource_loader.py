"""
iios/ontology/loader/resource_loader.py
=========================================
Loads ontology documents from external resources: file system, dicts, or
raw data structures.  Supports YAML/JSON via optional dependencies.
Built-in ontologies always use document_loader.py — this module is for
user-defined extensions.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from ..ontology_exceptions import OntologyResourceError
from ..runtime.runtime_object import (
    Cardinality,
    DataType,
    OntologyDocument,
    OntologyNamespace,
    OntologyProperty,
    OntologyRelationshipDef,
    OntologyTypeDef,
    TypeKind,
    OntologyCategory,
)

__all__ = [
    "ResourceLoader",
    "load_from_dict",
    "load_from_json_file",
    "load_from_json_string",
]

_LOG = logging.getLogger("iios.ontology.loader.resource")


class ResourceLoader:
    """
    Converts raw dict representations of ontology documents into
    OntologyDocument objects.

    The expected dict schema::

        {
            "uri":         "iios.myext.ontology",
            "name":        "MY_EXTENSION",
            "version":     "1.0.0",
            "description": "...",
            "category":    "extension",
            "namespace": {
                "uri":    "iios.myext",
                "name":   "MyExtension",
                "prefix": "ext"
            },
            "imports": [],
            "types": {
                "MyType": {
                    "uri":           "iios.myext.MyType",
                    "name":          "MyType",
                    "namespace_uri": "iios.myext",
                    "kind":          "concrete",
                    "parent_uri":    "iios.information.BaseObject",
                    "description":   "...",
                    "properties": {
                        "symbol": {
                            "name":      "symbol",
                            "data_type": "string",
                            "required":  true
                        }
                    }
                }
            },
            "relationships": {}
        }
    """

    # ── Entry point ────────────────────────────────────────────────────────────

    def load(self, data: dict[str, Any]) -> OntologyDocument:
        """Deserialise *data* to an OntologyDocument."""
        try:
            ns_data  = data.get("namespace") or {}
            ns       = self._load_namespace(ns_data or data)
            types    = self._load_types(data.get("types") or {}, ns.uri)
            rels     = self._load_relationships(data.get("relationships") or {}, ns.uri)
            cat_raw  = data.get("category", OntologyCategory.EXTENSION.value)
            try:
                category = OntologyCategory(cat_raw)
            except ValueError:
                category = OntologyCategory.EXTENSION

            return OntologyDocument(
                uri           = data["uri"],
                name          = data["name"],
                namespace     = ns,
                version       = data.get("version", "1.0.0"),
                category      = category,
                description   = data.get("description", ""),
                types         = types,
                relationships = rels,
                imports       = list(data.get("imports", [])),
                authors       = list(data.get("authors", [])),
                tags          = list(data.get("tags", [])),
            )
        except KeyError as exc:
            raise OntologyResourceError(f"Missing required field in ontology dict: {exc}") from exc
        except Exception as exc:
            raise OntologyResourceError(f"Failed to load ontology from dict: {exc}") from exc

    # ── Namespace ──────────────────────────────────────────────────────────────

    def _load_namespace(self, d: dict[str, Any]) -> OntologyNamespace:
        cat_raw = d.get("category", OntologyCategory.EXTENSION.value)
        try:
            category = OntologyCategory(cat_raw)
        except ValueError:
            category = OntologyCategory.EXTENSION
        return OntologyNamespace(
            uri         = d["uri"],
            name        = d.get("name", d["uri"]),
            prefix      = d.get("prefix", ""),
            description = d.get("description", ""),
            version     = d.get("version", "1.0.0"),
            category    = category,
            tags        = list(d.get("tags", [])),
        )

    # ── Types ──────────────────────────────────────────────────────────────────

    def _load_types(
        self,
        raw:          dict[str, Any],
        default_ns:   str,
    ) -> dict[str, OntologyTypeDef]:
        result: dict[str, OntologyTypeDef] = {}
        for key, td in raw.items():
            result[key] = self._load_type(key, td, default_ns)
        return result

    def _load_type(
        self,
        key:        str,
        d:          dict[str, Any],
        default_ns: str,
    ) -> OntologyTypeDef:
        kind_raw = d.get("kind", TypeKind.CONCRETE.value)
        try:
            kind = TypeKind(kind_raw)
        except ValueError:
            kind = TypeKind.CONCRETE

        props_raw = d.get("properties") or {}
        props: dict[str, OntologyProperty] = {}
        for pkey, pd in props_raw.items():
            props[pkey] = self._load_property(pkey, pd)

        return OntologyTypeDef(
            uri           = d.get("uri", f"{default_ns}.{key}"),
            name          = d.get("name", key),
            namespace_uri = d.get("namespace_uri", default_ns),
            kind          = kind,
            parent_uri    = d.get("parent_uri"),
            abstract      = bool(d.get("abstract", False)),
            deprecated    = bool(d.get("deprecated", False)),
            properties    = props,
            labels        = list(d.get("labels", [])),
            aliases       = list(d.get("aliases", [])),
            description   = d.get("description", ""),
            version       = d.get("version", "1.0.0"),
            tags          = list(d.get("tags", [])),
            metadata      = dict(d.get("metadata", {})),
        )

    # ── Properties ────────────────────────────────────────────────────────────

    def _load_property(self, key: str, d: dict[str, Any]) -> OntologyProperty:
        dt_raw = d.get("data_type", DataType.ANY.value)
        try:
            data_type = DataType(dt_raw)
        except ValueError:
            data_type = DataType.ANY
        return OntologyProperty(
            name        = d.get("name", key),
            data_type   = data_type,
            required    = bool(d.get("required", False)),
            default     = d.get("default"),
            description = d.get("description", ""),
            aliases     = list(d.get("aliases", [])),
            constraints = dict(d.get("constraints", {})),
            ref_uri     = d.get("ref_uri"),
        )

    # ── Relationships ─────────────────────────────────────────────────────────

    def _load_relationships(
        self,
        raw:        dict[str, Any],
        default_ns: str,
    ) -> dict[str, OntologyRelationshipDef]:
        result: dict[str, OntologyRelationshipDef] = {}
        for key, rd in raw.items():
            card_raw = rd.get("cardinality", Cardinality.MANY_TO_MANY.value)
            try:
                cardinality = Cardinality(card_raw)
            except ValueError:
                cardinality = Cardinality.MANY_TO_MANY
            result[key] = OntologyRelationshipDef(
                uri             = rd.get("uri", f"{default_ns}.{key}"),
                name            = rd.get("name", key),
                namespace_uri   = rd.get("namespace_uri", default_ns),
                source_type_uri = rd["source_type_uri"],
                target_type_uri = rd["target_type_uri"],
                cardinality     = cardinality,
                inverse_uri     = rd.get("inverse_uri"),
                description     = rd.get("description", ""),
                labels          = list(rd.get("labels", [])),
                deprecated      = bool(rd.get("deprecated", False)),
                version         = rd.get("version", "1.0.0"),
            )
        return result


# ── Module-level helpers ──────────────────────────────────────────────────────

_loader = ResourceLoader()


def load_from_dict(data: dict[str, Any]) -> OntologyDocument:
    """Load an OntologyDocument from a raw dictionary."""
    return _loader.load(data)


def load_from_json_string(json_str: str) -> OntologyDocument:
    """Load an OntologyDocument from a JSON string."""
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise OntologyResourceError(f"Invalid JSON: {exc}") from exc
    return _loader.load(data)


def load_from_json_file(path: str) -> OntologyDocument:
    """Load an OntologyDocument from a JSON file path."""
    if not os.path.isfile(path):
        raise OntologyResourceError(f"File not found: {path!r}")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise OntologyResourceError(f"Failed to read {path!r}: {exc}") from exc
    return _loader.load(data)
