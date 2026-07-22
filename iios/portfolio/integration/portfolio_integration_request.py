"""
portfolio_integration_request.py — iios.portfolio.integration
==============================================================
PortfolioIntegrationRequest — the ONLY external input object accepted
by PortfolioIntegrationEngine.submit().

C10 Portfolio Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import (
    INTEGRATION_SYSTEM_ID,
    VERSION,
    IntegrationServiceType,
)
from .portfolio_integration_context import IntegrationContext


@dataclass(frozen=True)
class PortfolioIntegrationRequest:
    """
    Immutable portfolio integration request.

    Submitted to :meth:`PortfolioIntegrationEngine.submit` to trigger the
    portfolio workflow for a specific service type.

    Fields
    ------
    request_id :        Unique request identifier.
    portfolio_id :      Target portfolio identifier.
    service_type :      Requested service classification.
    priority :          Request priority (higher = higher urgency).
    context :           Attached integration context.
    inputs :            Free-form dict of service inputs, e.g.
                        portfolio_name, lifecycle_state, optimization_data, etc.
    metadata :          Supplementary metadata.
    requested_at :      Wall-clock request creation time.
    framework_version : Framework version string.
    """
    request_id:        str
    portfolio_id:      str
    service_type:      str   # IntegrationServiceType.value
    priority:          int
    context:           IntegrationContext
    inputs:            Dict[str, Any]
    metadata:          Dict[str, Any]
    requested_at:      float
    framework_version: str

    @classmethod
    def create(
        cls,
        portfolio_id:   str,
        service_type:   IntegrationServiceType = IntegrationServiceType.PORTFOLIO_CREATION,
        *,
        request_id:     Optional[str] = None,
        priority:       int   = 5,
        inputs:         Optional[Dict[str, Any]] = None,
        metadata:       Optional[Dict[str, Any]] = None,
        actor:          str   = INTEGRATION_SYSTEM_ID,
        correlation_id: str   = "",
    ) -> "PortfolioIntegrationRequest":
        rid = request_id or str(uuid.uuid4())
        context = IntegrationContext.create(
            request_id    = rid,
            portfolio_id  = portfolio_id,
            service_type  = service_type.value,
            actor         = actor,
            correlation_id = correlation_id,
        )
        return cls(
            request_id        = rid,
            portfolio_id      = portfolio_id,
            service_type      = service_type.value,
            priority          = max(1, min(10, priority)),
            context           = context,
            inputs            = dict(inputs or {}),
            metadata          = dict(metadata or {}),
            requested_at      = time.time(),
            framework_version = VERSION,
        )

    @property
    def is_readonly(self) -> bool:
        from .constants import READONLY_SERVICES
        return self.service_type in {s.value for s in READONLY_SERVICES}

    @property
    def is_creation(self) -> bool:
        from .constants import CREATION_SERVICES
        return self.service_type in {s.value for s in CREATION_SERVICES}

    @property
    def portfolio_name(self) -> str:
        return self.inputs.get("portfolio_name", "")

    @property
    def lifecycle_state(self) -> str:
        return self.inputs.get("lifecycle_state", "running")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":       self.request_id,
            "portfolio_id":     self.portfolio_id,
            "service_type":     self.service_type,
            "priority":         self.priority,
            "context":          self.context.to_dict(),
            "inputs":           dict(self.inputs),
            "metadata":         dict(self.metadata),
            "requested_at":     self.requested_at,
            "framework_version": self.framework_version,
        }
