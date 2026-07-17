"""iios/execution/gateway/integration/gateway_integration_request.py
==================================================
GatewayIntegrationRequest — immutable gateway integration request.

Wraps a GatewayIntegrationContext with identity and tracking metadata.

C6 Execution Intelligence — Phase 5, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import IntegrationRequestStatus, VERSION
from .gateway_integration_context import GatewayIntegrationContext


@dataclass(frozen=True)
class GatewayIntegrationRequest:
    """
    Immutable integration-level request wrapping an execution context.

    Created by GatewayIntegrationEngine or GatewayComponentFactory.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    request_id:     str
    integration_id: str

    # ── Payload ───────────────────────────────────────────────────────────────
    context: GatewayIntegrationContext

    # ── Processing hints ──────────────────────────────────────────────────────
    status:      IntegrationRequestStatus = IntegrationRequestStatus.PENDING
    priority:    int = 0
    retry_count: int = 0

    # ── Metadata ──────────────────────────────────────────────────────────────
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: float = field(default_factory=time.time, compare=False)

    # ── Convenience passthrough ───────────────────────────────────────────────

    @property
    def execution_id(self) -> str:
        return self.context.execution_id

    @property
    def order_id(self) -> str:
        return self.context.order_id

    @property
    def portfolio_id(self) -> str:
        return self.context.portfolio_id

    @property
    def strategy_id(self) -> str:
        return self.context.strategy_id

    @property
    def is_pending(self) -> bool:
        return self.status == IntegrationRequestStatus.PENDING

    @property
    def is_terminal(self) -> bool:
        from .constants import TERMINAL_REQUEST_STATUSES
        return self.status in TERMINAL_REQUEST_STATUSES

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":     self.request_id,
            "integration_id": self.integration_id,
            "status":         self.status.value,
            "priority":       self.priority,
            "retry_count":    self.retry_count,
            "context":        self.context.to_dict(),
            "created_at":     self.created_at,
        }


def make_integration_request(
    context:        GatewayIntegrationContext,
    integration_id: str,
    *,
    priority:    int = 0,
    retry_count: int = 0,
    metadata:    Optional[Dict[str, Any]] = None,
) -> GatewayIntegrationRequest:
    return GatewayIntegrationRequest(
        request_id=str(uuid.uuid4()),
        integration_id=integration_id,
        context=context,
        status=IntegrationRequestStatus.PENDING,
        priority=priority,
        retry_count=retry_count,
        metadata=metadata or {},
    )
