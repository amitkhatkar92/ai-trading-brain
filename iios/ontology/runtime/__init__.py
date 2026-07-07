"""iios/ontology/runtime/__init__.py"""
from __future__ import annotations

from .runtime_object import (
    OntologyNamespace,
    OntologyProperty,
    OntologyTypeDef,
    OntologyRelationshipDef,
    OntologyDocument,
    CompiledOntology,
    OntologyStats,
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
