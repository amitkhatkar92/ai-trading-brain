"""iios/execution/oms/persistence/repository_request.py
==================================================
RepositoryRequest — mutable input to a repository operation.

C6 Execution Intelligence — Phase 2, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.persistence.constants import (
    DEFAULT_SAVE_TTL_SEC,
    DEFAULT_SEARCH_LIMIT,
    SCHEMA_VERSION,
    OperationType,
    RecordStatus,
    RecordType,
)


@dataclass
class RepositoryRequest:
    """
    Mutable request submitted to a StorageContract implementation.

    Carries both the operation intent and all parameters needed
    to perform save, update, delete, archive, restore, find, or search.
    """
    request_id:       str   = field(default_factory=lambda: str(uuid.uuid4()))
    operation:        OperationType = OperationType.SAVE
    record_id:        str   = ""
    record_type:      RecordType    = RecordType.ORDER
    repository_id:    str   = ""

    # Payload — the domain object serialised as a dict
    payload:          dict[str, Any] = field(default_factory=dict)

    # Optimistic concurrency — 0 = first save (no version check)
    expected_version: int   = 0

    # Routing / audit fields
    schema_version:   str   = SCHEMA_VERSION
    correlation_id:   str   = ""
    workflow_id:      str   = ""
    portfolio_id:     str   = ""
    strategy_id:      str   = ""
    requester:        str   = "iios:system"

    # Search parameters
    status_filter:    list[RecordStatus] = field(default_factory=list)
    time_range_start: float = 0.0
    time_range_end:   float = 0.0
    limit:            int   = DEFAULT_SEARCH_LIMIT
    offset:           int   = 0
    include_archived: bool  = False

    created_at:       float = field(default_factory=time.time)
    metadata:         dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id":      self.request_id,
            "operation":       self.operation.value,
            "record_id":       self.record_id,
            "record_type":     self.record_type.value,
            "repository_id":   self.repository_id,
            "expected_version": self.expected_version,
            "schema_version":  self.schema_version,
            "correlation_id":  self.correlation_id,
            "workflow_id":     self.workflow_id,
            "portfolio_id":    self.portfolio_id,
            "strategy_id":     self.strategy_id,
            "created_at":      self.created_at,
        }
