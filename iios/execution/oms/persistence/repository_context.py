"""iios/execution/oms/persistence/repository_context.py
==================================================
RepositoryContext — immutable context for one repository operation.

C6 Execution Intelligence — Phase 2, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.persistence.constants import (
    DEFAULT_SAVE_TTL_SEC,
    OperationType,
    RecordType,
)


@dataclass(frozen=True)
class RepositoryContext:
    """
    Immutable context attached to a repository operation.

    Carries audit, routing, and lifecycle metadata without
    any reference to the payload being persisted.
    """
    context_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    operation:     OperationType = OperationType.SAVE
    record_type:   RecordType    = RecordType.ORDER
    repository_id: str   = ""       # target repository; empty = default
    correlation_id: str  = ""
    workflow_id:   str   = ""
    portfolio_id:  str   = ""
    strategy_id:   str   = ""
    requester:     str   = "iios:system"
    created_at:    float = field(default_factory=time.time)
    ttl_sec:       float = DEFAULT_SAVE_TTL_SEC
    metadata:      dict[str, Any] = field(default_factory=dict)

    @property
    def is_read_only(self) -> bool:
        return self.operation in (OperationType.FIND, OperationType.SEARCH)

    @property
    def is_mutating(self) -> bool:
        return self.operation in (
            OperationType.SAVE, OperationType.UPDATE,
            OperationType.DELETE, OperationType.ARCHIVE,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id":    self.context_id,
            "operation":     self.operation.value,
            "record_type":   self.record_type.value,
            "repository_id": self.repository_id,
            "correlation_id": self.correlation_id,
            "workflow_id":   self.workflow_id,
            "portfolio_id":  self.portfolio_id,
            "strategy_id":   self.strategy_id,
            "requester":     self.requester,
            "is_read_only":  self.is_read_only,
        }
