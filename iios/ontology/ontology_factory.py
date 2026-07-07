"""
iios/ontology/ontology_factory.py
====================================
Factory for creating user-defined OntologyDocument objects
and individual type/property/relationship definitions.
"""

from __future__ import annotations

import threading
import uuid
from typing import Any, Optional

from .ontology_constants import DEFAULT_ONTOLOGY_VERSION, OntologyCategory
from .runtime.runtime_object import (
    Cardinality,
    DataType,
    OntologyDocument,
    OntologyNamespace,
    OntologyProperty,
    OntologyRelationshipDef,
    OntologyTypeDef,
    TypeKind,
)

__all__ = [
    "OntologyFactory",
    "get_ontology_factory",
    "reset_ontology_factory",
]

_lock     = threading.Lock()
_factory: Optional["OntologyFactory"] = None


class OntologyFactory:
    """Creates ontology model objects from structured parameters."""

    # ── Namespace ──────────────────────────────────────────────────────────────

    def create_namespace(
        self,
        uri:         str,
        name:        str,
        prefix:      str           = "",
        description: str           = "",
        version:     str           = DEFAULT_ONTOLOGY_VERSION,
        category:    OntologyCategory = OntologyCategory.EXTENSION,
        tags:        Optional[list[str]] = None,
    ) -> OntologyNamespace:
        return OntologyNamespace(
            uri         = uri,
            name        = name,
            prefix      = prefix or uri.split(".")[-1],
            description = description,
            version     = version,
            category    = category,
            tags        = list(tags or []),
        )

    # ── Type ──────────────────────────────────────────────────────────────────

    def create_type(
        self,
        name:          str,
        namespace_uri: str,
        kind:          TypeKind          = TypeKind.CONCRETE,
        parent_uri:    Optional[str]     = None,
        abstract:      bool              = False,
        description:   str               = "",
        labels:        Optional[list[str]] = None,
        aliases:       Optional[list[str]] = None,
        properties:    Optional[list[OntologyProperty]] = None,
        tags:          Optional[list[str]] = None,
        uri:           Optional[str]     = None,
    ) -> OntologyTypeDef:
        effective_uri = uri or f"{namespace_uri}.{name}"
        return OntologyTypeDef(
            uri           = effective_uri,
            name          = name,
            namespace_uri = namespace_uri,
            kind          = kind,
            parent_uri    = parent_uri,
            abstract      = abstract,
            description   = description,
            labels        = list(labels or []),
            aliases       = list(aliases or []),
            properties    = {p.name: p for p in (properties or [])},
            tags          = list(tags or []),
        )

    # ── Property ──────────────────────────────────────────────────────────────

    def create_property(
        self,
        name:        str,
        data_type:   DataType       = DataType.STRING,
        required:    bool           = False,
        default:     Any            = None,
        description: str            = "",
        ref_uri:     Optional[str]  = None,
        aliases:     Optional[list[str]] = None,
        constraints: Optional[dict[str, Any]] = None,
    ) -> OntologyProperty:
        return OntologyProperty(
            name        = name,
            data_type   = data_type,
            required    = required,
            default     = default,
            description = description,
            ref_uri     = ref_uri,
            aliases     = list(aliases or []),
            constraints = dict(constraints or {}),
        )

    # ── Relationship ──────────────────────────────────────────────────────────

    def create_relationship(
        self,
        name:            str,
        namespace_uri:   str,
        source_type_uri: str,
        target_type_uri: str,
        cardinality:     Cardinality  = Cardinality.MANY_TO_MANY,
        inverse_uri:     Optional[str]= None,
        description:     str          = "",
        uri:             Optional[str]= None,
    ) -> OntologyRelationshipDef:
        effective_uri = uri or f"{namespace_uri}.{name}"
        return OntologyRelationshipDef(
            uri             = effective_uri,
            name            = name,
            namespace_uri   = namespace_uri,
            source_type_uri = source_type_uri,
            target_type_uri = target_type_uri,
            cardinality     = cardinality,
            inverse_uri     = inverse_uri,
            description     = description,
        )

    # ── Document ──────────────────────────────────────────────────────────────

    def create_document(
        self,
        name:          str,
        namespace:     OntologyNamespace,
        version:       str           = DEFAULT_ONTOLOGY_VERSION,
        category:      OntologyCategory = OntologyCategory.EXTENSION,
        description:   str           = "",
        types:         Optional[list[OntologyTypeDef]] = None,
        relationships: Optional[list[OntologyRelationshipDef]] = None,
        imports:       Optional[list[str]] = None,
    ) -> OntologyDocument:
        uri = f"{namespace.uri}.ontology"
        return OntologyDocument(
            uri           = uri,
            name          = name,
            namespace     = namespace,
            version       = version,
            category      = category,
            description   = description,
            types         = {t.name: t for t in (types or [])},
            relationships = {r.name: r for r in (relationships or [])},
            imports       = list(imports or []),
        )


def get_ontology_factory() -> OntologyFactory:
    global _factory
    if _factory is None:
        with _lock:
            if _factory is None:
                _factory = OntologyFactory()
    return _factory


def reset_ontology_factory() -> None:
    global _factory
    with _lock:
        _factory = None
