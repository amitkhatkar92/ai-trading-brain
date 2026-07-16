"""iios/execution/oms/integration/oms_integration_request.py
==================================================
IntegrationRequest — mutable input to an OMS integration query.

C6 Execution Intelligence — Phase 2, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.integration.constants import (
    ComponentType,
    IntegrationQueryType,
)


@dataclass
class IntegrationRequest:
    """
    Mutable request submitted to OMSIntegrationEngine.query().

    The `payload` field carries query-specific parameters:
    - FIND_ORDER / BOOK_CONTAINS: {"order_id": "..."}
    - PERSIST_FIND:               {"record_id": "...", "repository_id": "..."}
    - QUEUE_PEEK / QUEUE_SIZE:    {}   (no params)
    - LIST_ACTIVE:                {"strategy_id": "...", "portfolio_id": "..."}  (optional filters)
    - BOOK_QUERY:                 {"portfolio_id": "...", ...}
    """
    request_id:     str   = field(default_factory=lambda: str(uuid.uuid4()))
    query_type:     IntegrationQueryType = IntegrationQueryType.FULL_HEALTH
    component_type: ComponentType | None = None
    payload:        dict[str, Any] = field(default_factory=dict)
    filters:        dict[str, Any] = field(default_factory=dict)
    correlation_id: str   = ""
    workflow_id:    str   = ""
    portfolio_id:   str   = ""
    strategy_id:    str   = ""
    requester:      str   = "iios:system"
    limit:          int   = 1000
    offset:         int   = 0
    created_at:     float = field(default_factory=time.time)
    metadata:       dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id":     self.request_id,
            "query_type":     self.query_type.value,
            "component_type": self.component_type.value if self.component_type else None,
            "correlation_id": self.correlation_id,
            "created_at":     self.created_at,
        }
