"""iios/execution/oms/persistence/repository_response.py
==================================================
RepositoryResponse — immutable output from a repository operation.

C6 Execution Intelligence — Phase 2, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.execution.oms.persistence.constants import OperationType
from iios.execution.oms.persistence.storage_metadata import StorageRecord


@dataclass(frozen=True)
class RepositoryResponse:
    """
    Immutable response returned from any StorageContract method.

    On success:
      - `succeeded` is True
      - `record` is populated for FIND / RESTORE operations
      - `records` is populated for SEARCH operations
      - `record_version` reflects the stored version after the operation

    On failure:
      - `succeeded` is False
      - `error_code` and `error_message` describe the failure
      - `record` and `records` are empty
    """
    response_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:     str   = ""
    operation:      OperationType = OperationType.SAVE
    record_id:      str   = ""
    repository_id:  str   = ""
    succeeded:      bool  = True
    record_version: int   = 0

    # Populated only for FIND / RESTORE
    record:         Optional[StorageRecord] = None

    # Populated only for SEARCH
    records:        tuple[StorageRecord, ...] = field(default_factory=tuple)

    elapsed_ms:     float = 0.0
    error_code:     str   = ""
    error_message:  str   = ""
    total_matches:  int   = 0     # total hits before limit/offset for SEARCH
    metadata:       dict[str, Any] = field(default_factory=dict)

    @property
    def is_error(self) -> bool:
        return not self.succeeded

    @property
    def record_count(self) -> int:
        return len(self.records)

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id":    self.response_id,
            "request_id":     self.request_id,
            "operation":      self.operation.value,
            "record_id":      self.record_id,
            "repository_id":  self.repository_id,
            "succeeded":      self.succeeded,
            "record_version": self.record_version,
            "elapsed_ms":     round(self.elapsed_ms, 3),
            "error_code":     self.error_code,
            "error_message":  self.error_message,
            "total_matches":  self.total_matches,
            "record_count":   self.record_count,
        }
