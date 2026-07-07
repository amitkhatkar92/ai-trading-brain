"""iios/ontology/loader/__init__.py"""
from __future__ import annotations

from .document_loader  import load_builtin_document, list_builtin_names, BUILTIN_DOCUMENTS
from .schema_loader    import SchemaLoader, validate_document
from .resource_loader  import ResourceLoader, load_from_dict, load_from_json_file, load_from_json_string
from .ontology_loader  import OntologyLoader, get_ontology_loader, reset_ontology_loader

__all__ = [
    "load_builtin_document",
    "list_builtin_names",
    "BUILTIN_DOCUMENTS",
    "SchemaLoader",
    "validate_document",
    "ResourceLoader",
    "load_from_dict",
    "load_from_json_file",
    "load_from_json_string",
    "OntologyLoader",
    "get_ontology_loader",
    "reset_ontology_loader",
]
