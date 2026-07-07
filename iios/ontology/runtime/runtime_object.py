"""
iios/ontology/runtime/runtime_object.py
=========================================
Core runtime data models for the Ontology Runtime Layer.

These are the in-memory representations of ontology definitions after
loading and compilation.  They are immutable (frozen dataclasses) to
guarantee thread-safety once compiled.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..ontology_constants import (
    Cardinality,
    DataType,
    DEFAULT_ONTOLOGY_VERSION,
    OntologyCategory,
    OntologyStatus,
    TypeKind,
)

__all__ = [
    "OntologyNamespace",
    "OntologyProperty",
    "OntologyTypeDef",
    "OntologyRelationshipDef",
    "OntologyDocument",
    "CompiledOntology",
    "OntologyStats",
]


# ── Namespace ─────────────────────────────────────────────────────────────────

@dataclass
class OntologyNamespace:
    """Declares a namespace that scopes a collection of type definitions."""

    uri:         str                       # "iios.observation"
    name:        str                       # "ObservationOntology"
    prefix:      str                       # "obs"
    description: str           = ""
    version:     str           = DEFAULT_ONTOLOGY_VERSION
    category:    OntologyCategory = OntologyCategory.INFORMATION
    tags:        list[str]     = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri":         self.uri,
            "name":        self.name,
            "prefix":      self.prefix,
            "description": self.description,
            "version":     self.version,
            "category":    self.category.value,
            "tags":        list(self.tags),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "OntologyNamespace":
        return cls(
            uri         = d["uri"],
            name        = d["name"],
            prefix      = d.get("prefix", ""),
            description = d.get("description", ""),
            version     = d.get("version", DEFAULT_ONTOLOGY_VERSION),
            category    = OntologyCategory(d.get("category", OntologyCategory.INFORMATION.value)),
            tags        = list(d.get("tags", [])),
        )


# ── Property ──────────────────────────────────────────────────────────────────

@dataclass
class OntologyProperty:
    """Defines a single property on an OntologyTypeDef."""

    name:        str
    data_type:   DataType        = DataType.ANY
    required:    bool            = False
    default:     Any             = None
    description: str             = ""
    aliases:     list[str]       = field(default_factory=list)
    constraints: dict[str, Any]  = field(default_factory=dict)
    # If data_type == REF, this is the target type URI
    ref_uri:     Optional[str]   = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name":        self.name,
            "data_type":   self.data_type.value,
            "required":    self.required,
            "default":     self.default,
            "description": self.description,
            "aliases":     list(self.aliases),
            "constraints": dict(self.constraints),
            "ref_uri":     self.ref_uri,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "OntologyProperty":
        return cls(
            name        = d["name"],
            data_type   = DataType(d.get("data_type", DataType.ANY.value)),
            required    = bool(d.get("required", False)),
            default     = d.get("default"),
            description = d.get("description", ""),
            aliases     = list(d.get("aliases", [])),
            constraints = dict(d.get("constraints", {})),
            ref_uri     = d.get("ref_uri"),
        )


# ── Type definition ───────────────────────────────────────────────────────────

@dataclass
class OntologyTypeDef:
    """Defines a semantic type within an ontology namespace."""

    uri:           str                               # "iios.observation.PriceObservation"
    name:          str                               # "PriceObservation"
    namespace_uri: str                               # "iios.observation"
    kind:          TypeKind          = TypeKind.CONCRETE
    parent_uri:    Optional[str]     = None          # Single-inheritance parent
    abstract:      bool              = False
    deprecated:    bool              = False
    properties:    dict[str, OntologyProperty] = field(default_factory=dict)
    labels:        list[str]         = field(default_factory=list)
    aliases:       list[str]         = field(default_factory=list)
    description:   str               = ""
    version:       str               = DEFAULT_ONTOLOGY_VERSION
    examples:      list[str]         = field(default_factory=list)
    tags:          list[str]         = field(default_factory=list)
    metadata:      dict[str, Any]    = field(default_factory=dict)

    @property
    def qualified_name(self) -> str:
        """Full dotted name: namespace_uri.name"""
        return f"{self.namespace_uri}.{self.name}"

    def has_property(self, name: str) -> bool:
        return name in self.properties or any(
            name in p.aliases for p in self.properties.values()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri":           self.uri,
            "name":          self.name,
            "namespace_uri": self.namespace_uri,
            "kind":          self.kind.value,
            "parent_uri":    self.parent_uri,
            "abstract":      self.abstract,
            "deprecated":    self.deprecated,
            "properties":    {k: v.to_dict() for k, v in self.properties.items()},
            "labels":        list(self.labels),
            "aliases":       list(self.aliases),
            "description":   self.description,
            "version":       self.version,
            "tags":          list(self.tags),
            "metadata":      dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "OntologyTypeDef":
        return cls(
            uri           = d["uri"],
            name          = d["name"],
            namespace_uri = d["namespace_uri"],
            kind          = TypeKind(d.get("kind", TypeKind.CONCRETE.value)),
            parent_uri    = d.get("parent_uri"),
            abstract      = bool(d.get("abstract", False)),
            deprecated    = bool(d.get("deprecated", False)),
            properties    = {
                k: OntologyProperty.from_dict(v)
                for k, v in d.get("properties", {}).items()
            },
            labels      = list(d.get("labels", [])),
            aliases     = list(d.get("aliases", [])),
            description = d.get("description", ""),
            version     = d.get("version", DEFAULT_ONTOLOGY_VERSION),
            tags        = list(d.get("tags", [])),
            metadata    = dict(d.get("metadata", {})),
        )


# ── Relationship definition ────────────────────────────────────────────────────

@dataclass
class OntologyRelationshipDef:
    """Defines a typed relationship between two ontology types."""

    uri:             str                         # "iios.relationship.HasSignal"
    name:            str                         # "HasSignal"
    namespace_uri:   str                         # "iios.relationship"
    source_type_uri: str                         # "iios.entity.Strategy"
    target_type_uri: str                         # "iios.observation.SignalObservation"
    cardinality:     Cardinality  = Cardinality.MANY_TO_MANY
    inverse_uri:     Optional[str]= None
    description:     str          = ""
    labels:          list[str]    = field(default_factory=list)
    deprecated:      bool         = False
    version:         str          = DEFAULT_ONTOLOGY_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri":             self.uri,
            "name":            self.name,
            "namespace_uri":   self.namespace_uri,
            "source_type_uri": self.source_type_uri,
            "target_type_uri": self.target_type_uri,
            "cardinality":     self.cardinality.value,
            "inverse_uri":     self.inverse_uri,
            "description":     self.description,
            "labels":          list(self.labels),
            "deprecated":      self.deprecated,
            "version":         self.version,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "OntologyRelationshipDef":
        return cls(
            uri             = d["uri"],
            name            = d["name"],
            namespace_uri   = d["namespace_uri"],
            source_type_uri = d["source_type_uri"],
            target_type_uri = d["target_type_uri"],
            cardinality     = Cardinality(d.get("cardinality", Cardinality.MANY_TO_MANY.value)),
            inverse_uri     = d.get("inverse_uri"),
            description     = d.get("description", ""),
            labels          = list(d.get("labels", [])),
            deprecated      = bool(d.get("deprecated", False)),
            version         = d.get("version", DEFAULT_ONTOLOGY_VERSION),
        )


# ── Ontology document ─────────────────────────────────────────────────────────

@dataclass
class OntologyDocument:
    """Raw ontology document before compilation."""

    uri:           str                                       # "iios.observation.ontology"
    name:          str                                       # "OBSERVATION_ONTOLOGY"
    namespace:     OntologyNamespace
    version:       str                   = DEFAULT_ONTOLOGY_VERSION
    category:      OntologyCategory      = OntologyCategory.INFORMATION
    description:   str                   = ""
    types:         dict[str, OntologyTypeDef]          = field(default_factory=dict)
    relationships: dict[str, OntologyRelationshipDef]  = field(default_factory=dict)
    imports:       list[str]             = field(default_factory=list)  # URIs of imported docs
    authors:       list[str]             = field(default_factory=list)
    tags:          list[str]             = field(default_factory=list)

    @property
    def type_count(self) -> int:
        return len(self.types)

    @property
    def relationship_count(self) -> int:
        return len(self.relationships)

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri":           self.uri,
            "name":          self.name,
            "namespace":     self.namespace.to_dict(),
            "version":       self.version,
            "category":      self.category.value,
            "description":   self.description,
            "types":         {k: v.to_dict() for k, v in self.types.items()},
            "relationships": {k: v.to_dict() for k, v in self.relationships.items()},
            "imports":       list(self.imports),
            "authors":       list(self.authors),
            "tags":          list(self.tags),
        }


# ── Compiled ontology ─────────────────────────────────────────────────────────

@dataclass
class CompiledOntology:
    """
    Fully compiled ontology — all inheritance resolved, all indexes built.
    This is what the runtime actually uses for queries and lookups.
    """

    document:       OntologyDocument
    compiled_at:    float                            = field(default_factory=time.time)
    status:         OntologyStatus                   = OntologyStatus.COMPILED
    # All types in this ontology, URI → TypeDef (own types only)
    types:          dict[str, OntologyTypeDef]       = field(default_factory=dict)
    # All relationships, URI → RelDef
    relationships:  dict[str, OntologyRelationshipDef] = field(default_factory=dict)
    # type_uri → resolved properties (own + all inherited)
    property_index: dict[str, dict[str, OntologyProperty]] = field(default_factory=dict)
    # parent_uri → set of direct child URIs
    children:       dict[str, set[str]]              = field(default_factory=dict)
    # alias / short name → canonical type URI
    alias_index:    dict[str, str]                   = field(default_factory=dict)
    # Warnings generated during compilation
    warnings:       list[str]                        = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.document.name

    @property
    def uri(self) -> str:
        return self.document.uri

    @property
    def namespace_uri(self) -> str:
        return self.document.namespace.uri

    @property
    def type_count(self) -> int:
        return len(self.types)

    def resolve_uri(self, ref: str) -> Optional[str]:
        """Resolve a short name or alias to a canonical type URI."""
        if ref in self.types:
            return ref
        return self.alias_index.get(ref)

    def get_type(self, uri: str) -> Optional[OntologyTypeDef]:
        resolved = self.resolve_uri(uri)
        if resolved:
            return self.types.get(resolved)
        return None

    def all_properties_of(self, type_uri: str) -> dict[str, OntologyProperty]:
        """Return merged properties (own + inherited) for a type URI."""
        resolved = self.resolve_uri(type_uri) or type_uri
        return dict(self.property_index.get(resolved, {}))

    def descendants_of(self, type_uri: str, include_self: bool = False) -> set[str]:
        """BFS to collect all descendant URIs."""
        result: set[str] = set()
        if include_self:
            result.add(type_uri)
        queue = list(self.children.get(type_uri, set()))
        while queue:
            child = queue.pop()
            if child not in result:
                result.add(child)
                queue.extend(self.children.get(child, set()))
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri":          self.uri,
            "name":         self.name,
            "compiled_at":  self.compiled_at,
            "status":       self.status.value,
            "type_count":   self.type_count,
            "rel_count":    len(self.relationships),
            "warnings":     list(self.warnings),
            "namespace_uri": self.namespace_uri,
        }


# ── Statistics ────────────────────────────────────────────────────────────────

@dataclass
class OntologyStats:
    """Runtime statistics for the ontology engine."""

    total_ontologies:    int   = 0
    total_types:         int   = 0
    total_relationships: int   = 0
    total_namespaces:    int   = 0
    compiled_count:      int   = 0
    cache_hits:          int   = 0
    cache_misses:        int   = 0
    query_count:         int   = 0
    uptime_seconds:      float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_ontologies":    self.total_ontologies,
            "total_types":         self.total_types,
            "total_relationships": self.total_relationships,
            "total_namespaces":    self.total_namespaces,
            "compiled_count":      self.compiled_count,
            "cache_hits":          self.cache_hits,
            "cache_misses":        self.cache_misses,
            "query_count":         self.query_count,
            "uptime_seconds":      round(self.uptime_seconds, 2),
        }
