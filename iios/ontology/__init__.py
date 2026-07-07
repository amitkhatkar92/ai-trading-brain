"""
iios/ontology/__init__.py
============================
Ontology Runtime Layer — public API.

Primary entry points::

    from iios.ontology import get_ontology_engine, get_ontology_manager

    engine = get_ontology_engine()
    engine.initialize()

    manager = get_ontology_manager()
    td = manager.get_type("Instrument")
    results = manager.search("price")
"""

from __future__ import annotations

from .ontology_constants import (
    ONTOLOGY_NAMESPACE,
    DEFAULT_ONTOLOGY_VERSION as ONTOLOGY_VERSION,
    BUILTIN_ONTOLOGY_NAMES,
    ONT_INFORMATION,
    ONT_ENTITY,
    ONT_RELATIONSHIP,
    ONT_EVENT,
    ONT_OBSERVATION,
    ONT_KNOWLEDGE,
    ONT_MASTER,
    OntologyCategory,
    OntologyStatus,
)
from .ontology_exceptions import (
    OntologyError,
    OntologyNotFoundError,
    OntologyAlreadyLoadedError,
    OntologyNotInitializedError,
    OntologyCompileError          as OntologyCompilationError,
    OntologyValidationError,
    OntologyCircularInheritanceError as OntologyCycleError,
    TypeNotFoundError,
    OntologyRuntimeError,
)
from .runtime.runtime_object import (
    DataType,
    TypeKind,
    Cardinality,
    OntologyNamespace,
    OntologyProperty,
    OntologyTypeDef,
    OntologyRelationshipDef,
    OntologyDocument,
    CompiledOntology,
    OntologyStats,
)
from .ontology_factory import (
    OntologyFactory,
    get_ontology_factory,
    reset_ontology_factory,
)
from .ontology_registry import (
    OntologyRegistry,
    get_ontology_registry,
    reset_ontology_registry,
)
from .ontology_manager import (
    OntologyManager,
    get_ontology_manager,
    reset_ontology_manager,
)
from .ontology_runtime_engine import (
    OntologyRuntimeEngine,
    get_ontology_engine,
    reset_ontology_engine,
)
from .query.ontology_query import OntologyQuery, OntologyQueryResult

__all__ = [
    # Constants
    "ONTOLOGY_NAMESPACE",
    "ONTOLOGY_VERSION",
    "BUILTIN_ONTOLOGY_NAMES",
    "ONT_INFORMATION",
    "ONT_ENTITY",
    "ONT_RELATIONSHIP",
    "ONT_EVENT",
    "ONT_OBSERVATION",
    "ONT_KNOWLEDGE",
    "ONT_MASTER",
    "OntologyCategory",
    "OntologyStatus",
    # Exceptions
    "OntologyError",
    "OntologyNotFoundError",
    "OntologyAlreadyLoadedError",
    "OntologyNotInitializedError",
    "OntologyCompilationError",
    "OntologyValidationError",
    "OntologyCycleError",
    "TypeNotFoundError",
    "OntologyRuntimeError",
    # Models
    "DataType",
    "TypeKind",
    "Cardinality",
    "OntologyNamespace",
    "OntologyProperty",
    "OntologyTypeDef",
    "OntologyRelationshipDef",
    "OntologyDocument",
    "CompiledOntology",
    "OntologyStats",
    # Factory
    "OntologyFactory",
    "get_ontology_factory",
    "reset_ontology_factory",
    # Registry
    "OntologyRegistry",
    "get_ontology_registry",
    "reset_ontology_registry",
    # Manager
    "OntologyManager",
    "get_ontology_manager",
    "reset_ontology_manager",
    # Engine
    "OntologyRuntimeEngine",
    "get_ontology_engine",
    "reset_ontology_engine",
    # Query
    "OntologyQuery",
    "OntologyQueryResult",
]
