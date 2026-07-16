"""iios/execution/oms/persistence/__init__.py
==================================================
Public API for the IIOS Order Persistence layer (M5).

C6 Execution Intelligence — Phase 2, Module 5
"""
from iios.execution.oms.persistence.constants import (
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REPOSITORIES,
    DEFAULT_SAVE_TTL_SEC,
    DEFAULT_SEARCH_LIMIT,
    FACTORY_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    PERSISTENCE_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    SCHEMA_VERSION,
    TERMINAL_RECORD_STATUSES,
    VALIDATOR_SYSTEM_ID,
    VERSION,
    OperationType,
    PersistenceEventType,
    PersistenceValidationCode,
    RecordStatus,
    RecordType,
    RecoveryState,
    RepositoryHealth,
    VersionType,
)
from iios.execution.oms.persistence.exceptions import (
    DuplicateRecordError,
    PersistenceError,
    PersistenceValidationError,
    RecordNotFoundError,
    RecoveryError,
    RepositoryCapacityError,
    RepositoryNotRunning,
    SchemaVersionError,
    SnapshotCorruptedError,
    StorageContractViolationError,
    VersionConflictError,
)
from iios.execution.oms.persistence.storage_metadata import (
    HealthStatus,
    StorageMetadata,
    StorageRecord,
    StorageStatistics,
)
from iios.execution.oms.persistence.storage_version import (
    StorageVersion,
    VersionHistory,
)
from iios.execution.oms.persistence.storage_snapshot import StorageSnapshot
from iios.execution.oms.persistence.repository_context import RepositoryContext
from iios.execution.oms.persistence.repository_request import RepositoryRequest
from iios.execution.oms.persistence.repository_response import RepositoryResponse
from iios.execution.oms.persistence.repository_events import (
    PersistenceEvent,
    make_record_archived,
    make_record_restored,
    make_record_saved,
    make_record_updated,
    make_recovery_completed,
    make_recovery_started,
    make_repository_validated,
)
from iios.execution.oms.persistence.recovery_record import RecoveryRecord
from iios.execution.oms.persistence.recovery_index import RecoveryIndex
from iios.execution.oms.persistence.storage_contract import StorageContract
from iios.execution.oms.persistence.repository_interface import (
    REQUIRED_METHODS,
    RepositoryInterface,
)
from iios.execution.oms.persistence.repository_validation import RepositoryValidator
from iios.execution.oms.persistence.repository_factory import RepositoryFactory
from iios.execution.oms.persistence.order_repository import (
    AbstractOrderRepository,
    InMemoryOrderRepository,
)
from iios.execution.oms.persistence.repository_registry import RepositoryRegistry
from iios.execution.oms.persistence.repository_manager import RepositoryManager

__all__ = [
    # Constants
    "PERSISTENCE_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VALIDATOR_SYSTEM_ID",
    "VERSION",
    "SCHEMA_VERSION",
    "DEFAULT_MAX_REPOSITORIES",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_SAVE_TTL_SEC",
    "DEFAULT_SEARCH_LIMIT",
    "TERMINAL_RECORD_STATUSES",
    # Enums
    "RecordType",
    "RecordStatus",
    "OperationType",
    "RepositoryHealth",
    "VersionType",
    "RecoveryState",
    "PersistenceEventType",
    "PersistenceValidationCode",
    # Exceptions
    "PersistenceError",
    "RecordNotFoundError",
    "DuplicateRecordError",
    "VersionConflictError",
    "RepositoryCapacityError",
    "RepositoryNotRunning",
    "PersistenceValidationError",
    "RecoveryError",
    "StorageContractViolationError",
    "SchemaVersionError",
    "SnapshotCorruptedError",
    # Data models
    "StorageMetadata",
    "StorageRecord",
    "StorageStatistics",
    "HealthStatus",
    "StorageVersion",
    "VersionHistory",
    "StorageSnapshot",
    "RepositoryContext",
    "RepositoryRequest",
    "RepositoryResponse",
    "PersistenceEvent",
    "RecoveryRecord",
    # Event factories
    "make_record_saved",
    "make_record_updated",
    "make_record_archived",
    "make_record_restored",
    "make_recovery_started",
    "make_recovery_completed",
    "make_repository_validated",
    # Index
    "RecoveryIndex",
    # Abstractions
    "StorageContract",
    "RepositoryInterface",
    "REQUIRED_METHODS",
    # Services
    "RepositoryValidator",
    "RepositoryFactory",
    "AbstractOrderRepository",
    "InMemoryOrderRepository",
    "RepositoryRegistry",
    "RepositoryManager",
]
