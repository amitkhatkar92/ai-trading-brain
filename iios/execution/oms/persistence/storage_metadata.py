"""iios/execution/oms/persistence/storage_metadata.py
==================================================
StorageRecord, StorageMetadata, StorageStatistics, HealthStatus —
core data models for the persistence layer.

C6 Execution Intelligence — Phase 2, Module 5
"""
from __future__ import annotations

import dataclasses
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.persistence.constants import (
    SCHEMA_VERSION,
    OperationType,
    RecordStatus,
    RecordType,
    RepositoryHealth,
)


@dataclass(frozen=True)
class StorageMetadata:
    """
    Immutable header information about a persisted record.

    Produced by repositories and included in responses.
    Never contains the record payload.
    """
    record_id:       str   = ""
    record_type:     RecordType     = RecordType.ORDER
    status:          RecordStatus   = RecordStatus.ACTIVE
    version:         int   = 1
    schema_version:  str   = SCHEMA_VERSION
    repository_id:   str   = ""
    correlation_id:  str   = ""
    created_at:      float = field(default_factory=time.time)
    updated_at:      float = field(default_factory=time.time)
    archived_at:     float = 0.0
    metadata:        dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id":      self.record_id,
            "record_type":    self.record_type.value,
            "status":         self.status.value,
            "version":        self.version,
            "schema_version": self.schema_version,
            "repository_id":  self.repository_id,
            "created_at":     self.created_at,
            "updated_at":     self.updated_at,
            "archived_at":    self.archived_at,
        }


@dataclass(frozen=True)
class StorageRecord:
    """
    Immutable persisted record: header + payload.

    Use with_* helpers to create updated copies.
    """
    record_id:      str   = ""
    record_type:    RecordType     = RecordType.ORDER
    status:         RecordStatus   = RecordStatus.ACTIVE
    version:        int   = 1
    schema_version: str   = SCHEMA_VERSION
    payload:        dict[str, Any] = field(default_factory=dict)
    repository_id:  str   = ""
    correlation_id: str   = ""
    workflow_id:    str   = ""
    portfolio_id:   str   = ""
    strategy_id:    str   = ""
    created_at:     float = field(default_factory=time.time)
    updated_at:     float = field(default_factory=time.time)
    archived_at:    float = 0.0
    metadata:       dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> StorageMetadata:
        return StorageMetadata(
            record_id      = self.record_id,
            record_type    = self.record_type,
            status         = self.status,
            version        = self.version,
            schema_version = self.schema_version,
            repository_id  = self.repository_id,
            correlation_id = self.correlation_id,
            created_at     = self.created_at,
            updated_at     = self.updated_at,
            archived_at    = self.archived_at,
            metadata       = dict(self.metadata),
        )

    def with_version(self, payload: dict[str, Any]) -> StorageRecord:
        """Return a new StorageRecord with incremented version and updated payload."""
        return dataclasses.replace(
            self,
            version    = self.version + 1,
            payload    = payload,
            updated_at = time.time(),
        )

    def with_status(self, status: RecordStatus, archived_at: float = 0.0) -> StorageRecord:
        """Return a new StorageRecord with updated status."""
        return dataclasses.replace(
            self,
            status      = status,
            archived_at = archived_at or self.archived_at,
            updated_at  = time.time(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id":      self.record_id,
            "record_type":    self.record_type.value,
            "status":         self.status.value,
            "version":        self.version,
            "schema_version": self.schema_version,
            "payload":        self.payload,
            "repository_id":  self.repository_id,
            "workflow_id":    self.workflow_id,
            "portfolio_id":   self.portfolio_id,
            "strategy_id":    self.strategy_id,
            "created_at":     self.created_at,
            "updated_at":     self.updated_at,
        }


@dataclass(frozen=True)
class StorageStatistics:
    """Immutable statistics snapshot from a repository."""
    repository_id:    str   = ""
    records_stored:   int   = 0
    records_updated:  int   = 0
    records_archived: int   = 0
    records_deleted:  int   = 0
    records_restored: int   = 0
    recovery_count:   int   = 0
    total_active:     int   = 0
    total_archived:   int   = 0
    avg_save_ms:      float = 0.0
    avg_restore_ms:   float = 0.0
    health:           RepositoryHealth = RepositoryHealth.HEALTHY
    last_updated_at:  float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository_id":    self.repository_id,
            "records_stored":   self.records_stored,
            "records_updated":  self.records_updated,
            "records_archived": self.records_archived,
            "records_deleted":  self.records_deleted,
            "recovery_count":   self.recovery_count,
            "total_active":     self.total_active,
            "total_archived":   self.total_archived,
            "avg_save_ms":      round(self.avg_save_ms, 3),
            "avg_restore_ms":   round(self.avg_restore_ms, 3),
            "health":           self.health.value,
        }


@dataclass(frozen=True)
class HealthStatus:
    """Result of a repository health check."""
    repository_id: str   = ""
    health:        RepositoryHealth = RepositoryHealth.UNKNOWN
    message:       str   = ""
    latency_ms:    float = 0.0
    checked_at:    float = field(default_factory=time.time)

    @property
    def is_healthy(self) -> bool:
        return self.health == RepositoryHealth.HEALTHY

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "health":        self.health.value,
            "message":       self.message,
            "latency_ms":    self.latency_ms,
            "checked_at":    self.checked_at,
            "is_healthy":    self.is_healthy,
        }
