"""
iios/infrastructure/infrastructure_exceptions.py
==================================================
Exception hierarchy for the IIOS Core Infrastructure Layer.
"""

from __future__ import annotations

__all__ = [
    "InfrastructureError",
    "DIError",
    "CircularDependencyError",
    "ServiceNotFoundError",
    "ServiceAlreadyRegisteredError",
    "LifecycleScopeError",
    "EventBusError",
    "EventDispatchError",
    "EventSubscriberError",
    "DeadLetterError",
    "CacheError",
    "CacheMissError",
    "CacheFullError",
    "RepositoryError",
    "EntityNotFoundError",
    "DuplicateEntityError",
    "TransactionError",
    "UnitOfWorkError",
    "SchedulerError",
    "JobNotFoundError",
    "JobAlreadyExistsError",
    "SerializationError",
    "DeserializationError",
    "StorageError",
    "StorageNotFoundError",
    "StorageIOError",
    "SecurityError",
    "TokenError",
    "EncryptionError",
    "NetworkError",
    "NetworkTimeoutError",
    "NetworkAuthError",
]


class InfrastructureError(Exception):
    """Base exception for all IIOS infrastructure errors."""

    def __init__(self, message: str = "", code: str = "", context: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.context: dict = context or {}

    def __str__(self) -> str:
        base = self.message or repr(self)
        if self.code:
            return f"[{self.code}] {base}"
        return base


# ---------------------------------------------------------------------------
# Dependency Injection
# ---------------------------------------------------------------------------

class DIError(InfrastructureError):
    """Dependency injection failure."""

class CircularDependencyError(DIError):
    """Circular dependency detected in service graph."""

class ServiceNotFoundError(DIError):
    """Requested service not registered."""

class ServiceAlreadyRegisteredError(DIError):
    """Service already registered with this key."""

class LifecycleScopeError(DIError):
    """Lifecycle scope violation (e.g. singleton resolving scoped)."""


# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------

class EventBusError(InfrastructureError):
    """General event bus failure."""

class EventDispatchError(EventBusError):
    """Event could not be dispatched."""

class EventSubscriberError(EventBusError):
    """Subscriber raised an error."""

class DeadLetterError(EventBusError):
    """Event moved to dead-letter queue."""


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

class CacheError(InfrastructureError):
    """General cache failure."""

class CacheMissError(CacheError):
    """Cache key not found."""

class CacheFullError(CacheError):
    """Cache capacity exceeded and eviction was not possible."""


# ---------------------------------------------------------------------------
# Repository / UoW
# ---------------------------------------------------------------------------

class RepositoryError(InfrastructureError):
    """General repository failure."""

class EntityNotFoundError(RepositoryError):
    """Entity with given ID not found."""

class DuplicateEntityError(RepositoryError):
    """Entity already exists."""

class TransactionError(InfrastructureError):
    """Database transaction failure."""

class UnitOfWorkError(InfrastructureError):
    """Unit of Work consistency violation."""


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class SchedulerError(InfrastructureError):
    """General scheduler failure."""

class JobNotFoundError(SchedulerError):
    """Job ID not found in registry."""

class JobAlreadyExistsError(SchedulerError):
    """Job with this ID already registered."""


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

class SerializationError(InfrastructureError):
    """Failed to serialise an object."""

class DeserializationError(InfrastructureError):
    """Failed to deserialise data."""


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

class StorageError(InfrastructureError):
    """General storage failure."""

class StorageNotFoundError(StorageError):
    """Requested storage key / path not found."""

class StorageIOError(StorageError):
    """Low-level I/O error in storage backend."""


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

class SecurityError(InfrastructureError):
    """General security failure."""

class TokenError(SecurityError):
    """Token validation or generation failure."""

class EncryptionError(SecurityError):
    """Encryption or decryption failure."""


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

class NetworkError(InfrastructureError):
    """General network failure."""

class NetworkTimeoutError(NetworkError):
    """Network request timed out."""

class NetworkAuthError(NetworkError):
    """Network authentication failure."""
