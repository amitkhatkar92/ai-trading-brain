"""
iios.infrastructure
===================
Core Infrastructure Layer — Wave 2 implementation.

Subpackages:
  dependency_injection  — DI container, registry, providers, factories
  events                — async event bus, publisher, subscriber, dispatcher
  cache                 — in-memory LRU/LFU/FIFO cache + manager
  repositories          — repository pattern, unit of work, transactions
  scheduler             — cron / interval / once job scheduler
  serialization         — JSON, YAML, TOML serializers
  storage               — local filesystem, JSON, binary, compressed
  utilities             — retry, rate limiter, circuit breaker
  security              — HMAC token manager, symmetric encryption
  network               — HTTP client with retry + circuit breaker
  database              — SQLite backend + query builder
  messaging             — in-process message broker + queue
"""

from __future__ import annotations

# Root-level models and constants (imported by subpackages, re-exported here)
from .infrastructure_constants import (
    LifecycleScope,
    EventPriority,
    CachePolicy,
    CacheBackend,
    JobType,
    JobStatus,
    StorageFormat,
    CompressionFormat,
    SerializationFormat,
    HttpMethod,
    RepositoryOp,
)
from .infrastructure_exceptions import (
    InfrastructureError,
    DIError,
    CircularDependencyError,
    ServiceNotFoundError,
    ServiceAlreadyRegisteredError,
    LifecycleScopeError,
    EventBusError,
    CacheError,
    RepositoryError,
    TransactionError,
    UnitOfWorkError,
    SchedulerError,
    SerializationError,
    DeserializationError,
    StorageError,
    SecurityError,
    NetworkError,
)
from .infrastructure_models import (
    ServiceDescriptor,
    ResolvedService,
    EventEnvelope,
    DeadLetterEntry,
    CacheEntry,
    CacheStats,
    JobDefinition,
    JobExecution,
    StorageMetadata,
    TransactionContext,
    HttpRequest,
    HttpResponse,
    RetryPolicy,
    CircuitBreakerState,
    RateLimitState,
)

# Subpackage re-exports (key public API only)
from .dependency_injection import (
    Container, get_container, reset_container,
    ServiceLocator, get_service,
)
from .events import EventBus, get_event_bus, reset_event_bus
from .cache import MemoryCache, CacheManager, get_cache_manager, reset_cache_manager
from .repositories import (
    BaseRepository, InMemoryRepository,
    RepositoryManager, get_repository_manager,
)
from .scheduler import JobScheduler, get_scheduler, reset_scheduler
from .serialization import JsonSerializer, YamlSerializer, TomlSerializer
from .storage import LocalStorage, JsonStorage, BinaryStorage, CompressedStorage
from .utilities import retry, RateLimiter, CircuitBreaker
from .security import TokenManager, SymmetricEncryption, generate_key
from .network import HttpClient
from .database import SQLiteBackend, QueryBuilder
from .messaging import Message, MessageQueue, MessageBroker, get_message_broker

__all__ = [
    # Constants
    "LifecycleScope", "EventPriority", "CachePolicy", "CacheBackend",
    "JobType", "JobStatus", "StorageFormat", "CompressionFormat",
    "SerializationFormat", "HttpMethod", "RepositoryOp",
    # Exceptions
    "InfrastructureError", "DIError", "CircularDependencyError",
    "ServiceNotFoundError", "ServiceAlreadyRegisteredError", "LifecycleScopeError",
    "EventBusError", "CacheError", "RepositoryError", "TransactionError",
    "UnitOfWorkError", "SchedulerError", "SerializationError", "DeserializationError",
    "StorageError", "SecurityError", "NetworkError",
    # Models
    "ServiceDescriptor", "ResolvedService", "EventEnvelope", "DeadLetterEntry",
    "CacheEntry", "CacheStats", "JobDefinition", "JobExecution",
    "StorageMetadata", "TransactionContext", "HttpRequest", "HttpResponse",
    "RetryPolicy", "CircuitBreakerState", "RateLimitState",
    # DI
    "Container", "get_container", "reset_container", "ServiceLocator", "get_service",
    # Events
    "EventBus", "get_event_bus", "reset_event_bus",
    # Cache
    "MemoryCache", "CacheManager", "get_cache_manager", "reset_cache_manager",
    # Repositories
    "BaseRepository", "InMemoryRepository", "RepositoryManager", "get_repository_manager",
    # Scheduler
    "JobScheduler", "get_scheduler", "reset_scheduler",
    # Serialization
    "JsonSerializer", "YamlSerializer", "TomlSerializer",
    # Storage
    "LocalStorage", "JsonStorage", "BinaryStorage", "CompressedStorage",
    # Utilities
    "retry", "RateLimiter", "CircuitBreaker",
    # Security
    "TokenManager", "SymmetricEncryption", "generate_key",
    # Network
    "HttpClient",
    # Database
    "SQLiteBackend", "QueryBuilder",
    # Messaging
    "Message", "MessageQueue", "MessageBroker", "get_message_broker",
]


__version__ = "0.1.0"
__status__ = "placeholder"
__wave__ = 2
__layer__ = "INFRASTRUCTURE"
__owner__ = "Platform"
__foundation__ = "IIOS-FCR-001"

# Planned submodules (enable as implemented in Wave 2):
# from .container import *  # TODO Wave 2
# from .service_registry import *  # TODO Wave 2
# from .component_registry import *  # TODO Wave 2

__all__ = []

