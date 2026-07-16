"""iios/execution/oms/persistence/repository_factory.py
==================================================
RepositoryFactory — creates all persistence data objects.

C6 Execution Intelligence — Phase 2, Module 5
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from iios.execution.oms.persistence.constants import (
    SCHEMA_VERSION,
    OperationType,
    RecordStatus,
    RecordType,
    RecoveryState,
)
from iios.execution.oms.persistence.recovery_record import RecoveryRecord
from iios.execution.oms.persistence.repository_request import RepositoryRequest
from iios.execution.oms.persistence.repository_response import RepositoryResponse
from iios.execution.oms.persistence.storage_metadata import StorageRecord
from iios.execution.oms.persistence.storage_version import StorageVersion, VersionType


class RepositoryFactory:
    """
    Stateless factory for creating persistence layer data objects.

    All methods are pure functions that never raise unless required
    fields are empty.
    """

    # ------------------------------------------------------------------
    # Request builders
    # ------------------------------------------------------------------

    def make_save_request(
        self,
        record_id:      str,
        payload:        dict[str, Any],
        record_type:    RecordType    = RecordType.ORDER,
        repository_id:  str           = "",
        correlation_id: str           = "",
        workflow_id:    str           = "",
        portfolio_id:   str           = "",
        strategy_id:    str           = "",
        schema_version: str           = SCHEMA_VERSION,
        metadata:       dict[str, Any] | None = None,
    ) -> RepositoryRequest:
        return RepositoryRequest(
            operation      = OperationType.SAVE,
            record_id      = record_id,
            record_type    = record_type,
            repository_id  = repository_id,
            payload        = payload,
            expected_version = 0,
            schema_version = schema_version,
            correlation_id = correlation_id,
            workflow_id    = workflow_id,
            portfolio_id   = portfolio_id,
            strategy_id    = strategy_id,
            metadata       = metadata or {},
        )

    def make_update_request(
        self,
        record_id:        str,
        payload:          dict[str, Any],
        expected_version: int           = 0,
        record_type:      RecordType    = RecordType.ORDER,
        repository_id:    str           = "",
        correlation_id:   str           = "",
        metadata:         dict[str, Any] | None = None,
    ) -> RepositoryRequest:
        return RepositoryRequest(
            operation        = OperationType.UPDATE,
            record_id        = record_id,
            record_type      = record_type,
            repository_id    = repository_id,
            payload          = payload,
            expected_version = expected_version,
            correlation_id   = correlation_id,
            metadata         = metadata or {},
        )

    def make_find_request(
        self,
        record_id:     str,
        repository_id: str = "",
        record_type:   RecordType = RecordType.ORDER,
    ) -> RepositoryRequest:
        return RepositoryRequest(
            operation     = OperationType.FIND,
            record_id     = record_id,
            record_type   = record_type,
            repository_id = repository_id,
        )

    def make_search_request(
        self,
        repository_id:    str           = "",
        portfolio_id:     str           = "",
        strategy_id:      str           = "",
        workflow_id:      str           = "",
        status_filter:    list[RecordStatus] | None = None,
        time_range_start: float         = 0.0,
        time_range_end:   float         = 0.0,
        limit:            int           = 1000,
        offset:           int           = 0,
        include_archived: bool          = False,
    ) -> RepositoryRequest:
        return RepositoryRequest(
            operation        = OperationType.SEARCH,
            repository_id    = repository_id,
            portfolio_id     = portfolio_id,
            strategy_id      = strategy_id,
            workflow_id      = workflow_id,
            status_filter    = status_filter or [],
            time_range_start = time_range_start,
            time_range_end   = time_range_end,
            limit            = limit,
            offset           = offset,
            include_archived = include_archived,
        )

    def make_delete_request(
        self,
        record_id:     str,
        repository_id: str = "",
        record_type:   RecordType = RecordType.ORDER,
        correlation_id: str = "",
    ) -> RepositoryRequest:
        return RepositoryRequest(
            operation      = OperationType.DELETE,
            record_id      = record_id,
            record_type    = record_type,
            repository_id  = repository_id,
            correlation_id = correlation_id,
        )

    def make_archive_request(
        self,
        record_id:     str,
        repository_id: str = "",
    ) -> RepositoryRequest:
        return RepositoryRequest(
            operation     = OperationType.ARCHIVE,
            record_id     = record_id,
            repository_id = repository_id,
        )

    def make_restore_request(
        self,
        record_id:     str,
        repository_id: str = "",
    ) -> RepositoryRequest:
        return RepositoryRequest(
            operation     = OperationType.RESTORE,
            record_id     = record_id,
            repository_id = repository_id,
        )

    # ------------------------------------------------------------------
    # Response builders
    # ------------------------------------------------------------------

    def make_success_response(
        self,
        request_id:    str,
        operation:     OperationType,
        record_id:     str,
        repository_id: str           = "",
        record_version: int          = 1,
        record:        StorageRecord | None = None,
        records:       tuple[StorageRecord, ...] = (),
        elapsed_ms:    float         = 0.0,
        total_matches: int           = 0,
        metadata:      dict[str, Any] | None = None,
    ) -> RepositoryResponse:
        return RepositoryResponse(
            request_id     = request_id,
            operation      = operation,
            record_id      = record_id,
            repository_id  = repository_id,
            succeeded      = True,
            record_version = record_version,
            record         = record,
            records        = records,
            elapsed_ms     = elapsed_ms,
            total_matches  = total_matches,
            metadata       = metadata or {},
        )

    def make_error_response(
        self,
        request_id:    str,
        operation:     OperationType,
        record_id:     str,
        error_code:    str,
        error_message: str,
        repository_id: str = "",
        elapsed_ms:    float = 0.0,
        metadata:      dict[str, Any] | None = None,
    ) -> RepositoryResponse:
        return RepositoryResponse(
            request_id    = request_id,
            operation     = operation,
            record_id     = record_id,
            repository_id = repository_id,
            succeeded     = False,
            error_code    = error_code,
            error_message = error_message,
            elapsed_ms    = elapsed_ms,
            metadata      = metadata or {},
        )

    # ------------------------------------------------------------------
    # StorageRecord builder
    # ------------------------------------------------------------------

    def make_storage_record(
        self,
        record_id:      str,
        payload:        dict[str, Any],
        record_type:    RecordType    = RecordType.ORDER,
        repository_id:  str           = "",
        correlation_id: str           = "",
        workflow_id:    str           = "",
        portfolio_id:   str           = "",
        strategy_id:    str           = "",
        schema_version: str           = SCHEMA_VERSION,
        version:        int           = 1,
        metadata:       dict[str, Any] | None = None,
    ) -> StorageRecord:
        now = time.time()
        return StorageRecord(
            record_id      = record_id,
            record_type    = record_type,
            status         = RecordStatus.ACTIVE,
            version        = version,
            schema_version = schema_version,
            payload        = payload,
            repository_id  = repository_id,
            correlation_id = correlation_id,
            workflow_id    = workflow_id,
            portfolio_id   = portfolio_id,
            strategy_id    = strategy_id,
            created_at     = now,
            updated_at     = now,
            archived_at    = 0.0,
            metadata       = metadata or {},
        )

    # ------------------------------------------------------------------
    # RecoveryRecord builder
    # ------------------------------------------------------------------

    def make_recovery_record(
        self,
        order_id:      str,
        record_id:     str,
        payload:       dict[str, Any],
        checkpoint_id: str        = "",
        snapshot_id:   str        = "",
        record_type:   RecordType = RecordType.ORDER,
        metadata:      dict[str, Any] | None = None,
    ) -> RecoveryRecord:
        return RecoveryRecord(
            order_id       = order_id,
            record_id      = record_id,
            record_type    = record_type,
            checkpoint_id  = checkpoint_id,
            snapshot_id    = snapshot_id,
            recovery_state = RecoveryState.PENDING,
            payload        = payload,
            metadata       = metadata or {},
        )

    # ------------------------------------------------------------------
    # StorageVersion builder
    # ------------------------------------------------------------------

    def make_version_entry(
        self,
        record_id:      str,
        version_number: int,
        author:         str         = "iios:system",
        change_summary: str         = "",
        version_type:   VersionType = VersionType.RECORD,
        schema_version: str         = SCHEMA_VERSION,
    ) -> StorageVersion:
        return StorageVersion(
            record_id      = record_id,
            version_type   = version_type,
            version_number = version_number,
            schema_version = schema_version,
            author         = author,
            change_summary = change_summary or f"Version {version_number}",
        )
