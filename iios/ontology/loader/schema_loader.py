"""
iios/ontology/loader/schema_loader.py
=======================================
Validates ontology document structure before compilation.
Ensures required fields, consistent URIs, valid type references.
"""

from __future__ import annotations

import logging
from typing import Any

from ..ontology_exceptions import OntologySchemaError
from ..runtime.runtime_object import (
    OntologyDocument,
    OntologyNamespace,
    OntologyProperty,
    OntologyRelationshipDef,
    OntologyTypeDef,
)

__all__ = [
    "SchemaLoader",
    "validate_document",
]

_LOG = logging.getLogger("iios.ontology.loader.schema")


class SchemaLoader:
    """Validates the structural integrity of an OntologyDocument."""

    # ── Entry point ────────────────────────────────────────────────────────────

    def validate(self, doc: OntologyDocument) -> list[str]:
        """
        Validate *doc* and return a list of warning strings.
        Raises OntologySchemaError on hard errors.
        """
        warnings: list[str] = []
        self._validate_namespace(doc.namespace)
        self._validate_document_uri(doc)
        for name, typedef in doc.types.items():
            w = self._validate_type(name, typedef, doc)
            warnings.extend(w)
        for name, reldef in doc.relationships.items():
            w = self._validate_relationship(name, reldef, doc)
            warnings.extend(w)
        return warnings

    # ── Namespace validation ───────────────────────────────────────────────────

    def _validate_namespace(self, ns: OntologyNamespace) -> None:
        if not ns.uri:
            raise OntologySchemaError("Namespace URI must not be empty.")
        if not ns.name:
            raise OntologySchemaError("Namespace name must not be empty.")
        if "." not in ns.uri:
            raise OntologySchemaError(
                f"Namespace URI {ns.uri!r} must be a dotted path (e.g. 'iios.observation')."
            )

    # ── Document-level validation ──────────────────────────────────────────────

    def _validate_document_uri(self, doc: OntologyDocument) -> None:
        if not doc.uri:
            raise OntologySchemaError("OntologyDocument URI must not be empty.")
        if not doc.name:
            raise OntologySchemaError("OntologyDocument name must not be empty.")
        if not doc.uri.startswith(doc.namespace.uri):
            raise OntologySchemaError(
                f"Document URI {doc.uri!r} must start with namespace URI {doc.namespace.uri!r}."
            )

    # ── Type validation ────────────────────────────────────────────────────────

    def _validate_type(
        self,
        name:    str,
        typedef: OntologyTypeDef,
        doc:     OntologyDocument,
    ) -> list[str]:
        warnings: list[str] = []

        if not typedef.uri:
            raise OntologySchemaError(f"Type {name!r} has an empty URI.")
        if not typedef.name:
            raise OntologySchemaError(f"Type {name!r}: 'name' must not be empty.")
        if not typedef.namespace_uri:
            raise OntologySchemaError(f"Type {typedef.uri!r}: 'namespace_uri' must not be empty.")

        # URI should be under the declared namespace
        if not typedef.uri.startswith(typedef.namespace_uri):
            warnings.append(
                f"Type {typedef.uri!r} URI does not start with its namespace URI {typedef.namespace_uri!r}."
            )

        # name key must match
        if typedef.name != name:
            raise OntologySchemaError(
                f"Type dict key {name!r} does not match type.name {typedef.name!r}."
            )

        if not typedef.description:
            warnings.append(f"Type {typedef.uri!r} has no description.")

        for prop_name, prop in typedef.properties.items():
            w = self._validate_property(prop_name, prop, typedef)
            warnings.extend(w)

        return warnings

    # ── Property validation ────────────────────────────────────────────────────

    def _validate_property(
        self,
        prop_name: str,
        prop:      OntologyProperty,
        typedef:   OntologyTypeDef,
    ) -> list[str]:
        warnings: list[str] = []
        if not prop.name:
            raise OntologySchemaError(
                f"Property {prop_name!r} on {typedef.uri!r} has empty name."
            )
        if prop.name != prop_name:
            raise OntologySchemaError(
                f"Property dict key {prop_name!r} does not match prop.name {prop.name!r} on {typedef.uri!r}."
            )
        return warnings

    # ── Relationship validation ────────────────────────────────────────────────

    def _validate_relationship(
        self,
        name:   str,
        reldef: OntologyRelationshipDef,
        doc:    OntologyDocument,
    ) -> list[str]:
        warnings: list[str] = []
        if not reldef.uri:
            raise OntologySchemaError(f"Relationship {name!r} has an empty URI.")
        if not reldef.source_type_uri:
            raise OntologySchemaError(f"Relationship {reldef.uri!r}: source_type_uri must not be empty.")
        if not reldef.target_type_uri:
            raise OntologySchemaError(f"Relationship {reldef.uri!r}: target_type_uri must not be empty.")
        if not reldef.description:
            warnings.append(f"Relationship {reldef.uri!r} has no description.")
        return warnings


# ── Module-level convenience ──────────────────────────────────────────────────

_schema_loader = SchemaLoader()


def validate_document(doc: OntologyDocument) -> list[str]:
    """Validate *doc* and return warnings. Raises on hard errors."""
    return _schema_loader.validate(doc)
