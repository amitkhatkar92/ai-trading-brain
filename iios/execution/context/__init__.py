"""iios/execution/context/__init__.py
==================================================
Public API for the IIOS Execution Context package.

C6 Execution Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

# ── Constants ─────────────────────────────────────────────────────────────────
from iios.execution.context.constants import (
    CONTEXT_SYSTEM_ID,
    BUILDER_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    VALIDATOR_SYSTEM_ID,
    VERSION,
    ACTOR_SYSTEM,
    ACTOR_BUILDER,
    ACTOR_FACTORY,
    ACTOR_REGISTRY,
    ACTOR_VALIDATOR,
    ACTOR_USER,
    DEFAULT_MAX_CONTEXTS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_BUNDLE_SIZE,
    ExecutionMode,
    ExecutionEnvironment,
    MarketSession,
    ContextStatus,
    ContextValidationCode,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from iios.execution.context.exceptions import (
    ExecutionContextError,
    ContextBuildError,
    ContextValidationError,
    ContextNotFoundError,
    DuplicateContextError,
    ContextCapacityError,
    ContextRegistryNotRunning,
    ContextIncompleteError,
    ContextInconsistencyError,
    ContextSerializationError,
    ContextHistoryError,
)

# ── Core context ──────────────────────────────────────────────────────────────
from iios.execution.context.execution_context import ExecutionContext

# ── Sub-contexts and descriptors ──────────────────────────────────────────────
from iios.execution.context.execution_metadata import ExecutionMetadata
from iios.execution.context.execution_environment import ExecutionEnvironmentDescriptor
from iios.execution.context.execution_session import ExecutionSession
from iios.execution.context.execution_request_context import (
    BrokerContextRef,
    ExecutionRequestContext,
)

# ── Bundle ────────────────────────────────────────────────────────────────────
from iios.execution.context.execution_bundle import ExecutionBundle

# ── Events ────────────────────────────────────────────────────────────────────
from iios.execution.context.execution_context_events import (
    ExecutionContextEventType,
    ExecutionContextEvent,
    make_context_event,
)

# ── Validation ────────────────────────────────────────────────────────────────
from iios.execution.context.execution_context_validator import (
    ExecutionContextValidator,
    ContextValidationResult,
)

# ── Builder ───────────────────────────────────────────────────────────────────
from iios.execution.context.execution_context_builder import ExecutionContextBuilder

# ── Factory ───────────────────────────────────────────────────────────────────
from iios.execution.context.execution_context_factory import ExecutionContextFactory

# ── Registry ─────────────────────────────────────────────────────────────────
from iios.execution.context.execution_context_registry import (
    ContextRecord,
    ExecutionContextRegistry,
)

# ── History ───────────────────────────────────────────────────────────────────
from iios.execution.context.execution_context_history import (
    ContextRevision,
    ExecutionContextHistory,
    make_revision,
)

# ── Statistics ────────────────────────────────────────────────────────────────
from iios.execution.context.execution_context_statistics import (
    ContextBuildStatistics,
    ExecutionContextStatistics,
)

__all__ = [
    # System IDs
    "CONTEXT_SYSTEM_ID",
    "BUILDER_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "VALIDATOR_SYSTEM_ID",
    "VERSION",
    # Actors
    "ACTOR_SYSTEM",
    "ACTOR_BUILDER",
    "ACTOR_FACTORY",
    "ACTOR_REGISTRY",
    "ACTOR_VALIDATOR",
    "ACTOR_USER",
    # Capacity
    "DEFAULT_MAX_CONTEXTS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_BUNDLE_SIZE",
    # Enums
    "ExecutionMode",
    "ExecutionEnvironment",
    "MarketSession",
    "ContextStatus",
    "ContextValidationCode",
    # Exceptions
    "ExecutionContextError",
    "ContextBuildError",
    "ContextValidationError",
    "ContextNotFoundError",
    "DuplicateContextError",
    "ContextCapacityError",
    "ContextRegistryNotRunning",
    "ContextIncompleteError",
    "ContextInconsistencyError",
    "ContextSerializationError",
    "ContextHistoryError",
    # Core
    "ExecutionContext",
    # Sub-contexts
    "ExecutionMetadata",
    "ExecutionEnvironmentDescriptor",
    "ExecutionSession",
    "BrokerContextRef",
    "ExecutionRequestContext",
    # Bundle
    "ExecutionBundle",
    # Events
    "ExecutionContextEventType",
    "ExecutionContextEvent",
    "make_context_event",
    # Validation
    "ExecutionContextValidator",
    "ContextValidationResult",
    # Builder
    "ExecutionContextBuilder",
    # Factory
    "ExecutionContextFactory",
    # Registry
    "ContextRecord",
    "ExecutionContextRegistry",
    # History
    "ContextRevision",
    "ExecutionContextHistory",
    "make_revision",
    # Statistics
    "ContextBuildStatistics",
    "ExecutionContextStatistics",
]
