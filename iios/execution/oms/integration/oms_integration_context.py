"""iios/execution/oms/integration/oms_integration_context.py
==================================================
IntegrationContext — immutable context for one OMS integration operation.

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


@dataclass(frozen=True)
class IntegrationContext:
    """
    Immutable context attached to an OMS integration operation.

    Carries audit, routing, and lifecycle metadata without
    reference to a specific payload.
    """
    context_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    query_type:    IntegrationQueryType = IntegrationQueryType.FULL_HEALTH
    component_type: ComponentType | None = None   # None = cross-component
    correlation_id: str  = ""
    workflow_id:   str   = ""
    portfolio_id:  str   = ""
    strategy_id:   str   = ""
    requester:     str   = "iios:system"
    created_at:    float = field(default_factory=time.time)
    metadata:      dict[str, Any] = field(default_factory=dict)

    @property
    def is_cross_component(self) -> bool:
        """True when the operation spans multiple components."""
        return self.component_type is None

    @property
    def is_single_component(self) -> bool:
        return self.component_type is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id":     self.context_id,
            "query_type":     self.query_type.value,
            "component_type": self.component_type.value if self.component_type else None,
            "correlation_id": self.correlation_id,
            "workflow_id":    self.workflow_id,
            "portfolio_id":   self.portfolio_id,
            "strategy_id":    self.strategy_id,
            "requester":      self.requester,
        }
