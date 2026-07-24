"""
__init__.py — iios.knowledge.lifecycle
----------------------------------------
Public API surface of the Knowledge Lifecycle subsystem.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from .constants import (
    ACTIVE_STATES,
    ACTOR_LIFECYCLE,
    ACTOR_OPERATOR,
    ACTOR_SYSTEM,
    DEFAULT_MAX_ARCHIVED,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_MAX_TRANSITIONS,
    IMMUTABLE_STATES,
    LIFECYCLE_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    SCHEMA_VERSION,
    SUCCESS_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    VERSION,
    KnowledgeEventType,
    KnowledgeLifecycleState,
    KnowledgeScope,
    KnowledgeSource,
    KnowledgeType,
)
from .exceptions import (
    KnowledgeCapacityError,
    KnowledgeHistoryError,
    KnowledgeInvalidTransitionError,
    KnowledgeLifecycleError,
    KnowledgeLifecycleNotRunningError,
    KnowledgeRegistryError,
    KnowledgeSessionNotFoundError,
    KnowledgeSessionTerminatedError,
    KnowledgeValidationError,
)
from .knowledge_context import KnowledgeContext
from .knowledge_events import KnowledgeEvent, KnowledgeEventBus
from .knowledge_factory import KnowledgeFactory
from .knowledge_history import KnowledgeHistory
from .knowledge_lifecycle import KnowledgeLifecycle
from .knowledge_metadata import KnowledgeMetadata
from .knowledge_registry import KnowledgeRegistry
from .knowledge_session import KnowledgeSession
from .knowledge_state import KnowledgeStateRecord
from .knowledge_statistics import KnowledgeStatistics
from .knowledge_transition import KnowledgeTransition
from .knowledge_validation import (
    KnowledgeValidationCode,
    KnowledgeValidationResult,
    KnowledgeValidator,
)

__all__ = [
    # Constants / enums
    "VERSION",
    "SCHEMA_VERSION",
    "LIFECYCLE_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "ACTOR_LIFECYCLE",
    "ACTOR_OPERATOR",
    "ACTOR_SYSTEM",
    "DEFAULT_MAX_SESSIONS",
    "DEFAULT_MAX_ARCHIVED",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_TRANSITIONS",
    "KnowledgeLifecycleState",
    "KnowledgeType",
    "KnowledgeScope",
    "KnowledgeSource",
    "KnowledgeEventType",
    "VALID_TRANSITIONS",
    "ACTIVE_STATES",
    "TERMINAL_STATES",
    "IMMUTABLE_STATES",
    "SUCCESS_STATES",
    # Exceptions
    "KnowledgeLifecycleError",
    "KnowledgeLifecycleNotRunningError",
    "KnowledgeSessionNotFoundError",
    "KnowledgeInvalidTransitionError",
    "KnowledgeSessionTerminatedError",
    "KnowledgeValidationError",
    "KnowledgeRegistryError",
    "KnowledgeCapacityError",
    "KnowledgeHistoryError",
    # Domain objects
    "KnowledgeSession",
    "KnowledgeMetadata",
    "KnowledgeContext",
    "KnowledgeStateRecord",
    "KnowledgeTransition",
    # Infrastructure
    "KnowledgeRegistry",
    "KnowledgeHistory",
    "KnowledgeStatistics",
    "KnowledgeFactory",
    "KnowledgeValidator",
    "KnowledgeValidationCode",
    "KnowledgeValidationResult",
    # Events
    "KnowledgeEvent",
    "KnowledgeEventBus",
    # Primary façade
    "KnowledgeLifecycle",
]
