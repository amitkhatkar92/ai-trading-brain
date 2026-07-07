"""iios/ontology/loader/__init__.py"""
from __future__ import annotations

from .document_loader    import load_builtin_document, list_builtin_names, BUILTIN_DOCUMENTS
from .schema_loader      import SchemaLoader, validate_document
from .resource_loader    import ResourceLoader, load_from_dict, load_from_json_file, load_from_json_string
from .ontology_loader    import OntologyLoader, get_ontology_loader, reset_ontology_loader
from .compiled_loader    import CompiledLoader, get_compiled_loader, reset_compiled_loader
from .runtime_loader     import LoadResult, RuntimeLoader, get_runtime_loader, reset_runtime_loader
from .incremental_loader import IncrementalResult, IncrementalLoader, get_incremental_loader, reset_incremental_loader
from .cache_loader       import CacheEntry, CacheLoader, get_cache_loader, reset_cache_loader

__all__ = [
    # Document loader
    "load_builtin_document",
    "list_builtin_names",
    "BUILTIN_DOCUMENTS",
    # Schema
    "SchemaLoader",
    "validate_document",
    # Resource loader
    "ResourceLoader",
    "load_from_dict",
    "load_from_json_file",
    "load_from_json_string",
    # Ontology loader (raw docs)
    "OntologyLoader",
    "get_ontology_loader",
    "reset_ontology_loader",
    # Compiled loader (warm cache)
    "CompiledLoader",
    "get_compiled_loader",
    "reset_compiled_loader",
    # Runtime loader (production entry point)
    "LoadResult",
    "RuntimeLoader",
    "get_runtime_loader",
    "reset_runtime_loader",
    # Incremental loader
    "IncrementalResult",
    "IncrementalLoader",
    "get_incremental_loader",
    "reset_incremental_loader",
    # Cache loader
    "CacheEntry",
    "CacheLoader",
    "get_cache_loader",
    "reset_cache_loader",
]
