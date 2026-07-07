"""iios/ontology/compiler/__init__.py"""
from __future__ import annotations

from .ontology_compiler   import OntologyCompiler,   get_ontology_compiler,   reset_ontology_compiler
from .compiler_constants  import (
    CompilationStrategy, LoadPhase, DependencyKind, MetadataField,
    CompilationPass, CacheStrategy, IncrementalMode,
    COMPILER_VERSION, BUILTIN_COMPILE_ORDER,
)
from .compiler_exceptions import (
    CompilerError, DependencyError, CircularDependencyError,
    UnresolvedDependencyError, CompilationError, CompilationTimeoutError,
    PassFailedError, TypeResolutionError, LoaderError, ColdStartError,
    WarmStartError, IncrementalLoadError, HotReloadError, CacheLoaderError,
    MetadataError, HashMismatchError, CompilerRegistryError,
    DuplicateCompilationError, CompilerContextError,
)
from .compiler_context    import (
    CompilationDiagnostic, CompilerContext, DiagnosticLevel,
    get_compiler_context, reset_compiler_context, compiler_compilation,
)
from .compiler_factory    import (
    CompileRequest, CompileResult, BatchCompileRequest, BatchCompileResult,
    CompilerFactory, get_compiler_factory, reset_compiler_factory,
)
from .compiler_registry   import (
    CompilationRecord, CompilerRegistry,
    get_compiler_registry, reset_compiler_registry,
)
from .dependency_resolver import (
    DependencyEdge, DependencyGraph, DependencyResolver,
    get_dependency_resolver, reset_dependency_resolver,
)
from .metadata_generator  import (
    CompilationMetadata, MetadataGenerator,
    get_metadata_generator, reset_metadata_generator,
)
from .compiler_manager    import (
    CompilerManager, get_compiler_manager, reset_compiler_manager,
)

__all__ = [
    # Core compiler
    "OntologyCompiler", "get_ontology_compiler", "reset_ontology_compiler",
    # Constants / enums
    "CompilationStrategy", "LoadPhase", "DependencyKind", "MetadataField",
    "CompilationPass", "CacheStrategy", "IncrementalMode",
    "COMPILER_VERSION", "BUILTIN_COMPILE_ORDER",
    # Exceptions
    "CompilerError", "DependencyError", "CircularDependencyError",
    "UnresolvedDependencyError", "CompilationError", "CompilationTimeoutError",
    "PassFailedError", "TypeResolutionError", "LoaderError", "ColdStartError",
    "WarmStartError", "IncrementalLoadError", "HotReloadError", "CacheLoaderError",
    "MetadataError", "HashMismatchError", "CompilerRegistryError",
    "DuplicateCompilationError", "CompilerContextError",
    # Context
    "CompilationDiagnostic", "CompilerContext", "DiagnosticLevel",
    "get_compiler_context", "reset_compiler_context", "compiler_compilation",
    # Factory
    "CompileRequest", "CompileResult", "BatchCompileRequest", "BatchCompileResult",
    "CompilerFactory", "get_compiler_factory", "reset_compiler_factory",
    # Registry
    "CompilationRecord", "CompilerRegistry",
    "get_compiler_registry", "reset_compiler_registry",
    # Dependency resolver
    "DependencyEdge", "DependencyGraph", "DependencyResolver",
    "get_dependency_resolver", "reset_dependency_resolver",
    # Metadata generator
    "CompilationMetadata", "MetadataGenerator",
    "get_metadata_generator", "reset_metadata_generator",
    # Manager (primary entry point)
    "CompilerManager", "get_compiler_manager", "reset_compiler_manager",
]
