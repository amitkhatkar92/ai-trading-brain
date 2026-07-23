"""
risk_integration_context.py — iios.risk.integration
=====================================================
Immutable configuration context for a risk integration session.

C11 Risk Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    DEFAULT_REQUEST_TIMEOUT_S,
    RequestType,
    VERSION,
)


@dataclass(frozen=True)
class RiskIntegrationContext:
    """
    Immutable configuration context for a risk integration session.

    Carries operational parameters that govern how the integration engine
    processes a :class:`~.risk_integration_request.RiskIntegrationRequest`.
    """
    context_id:        str
    request_type:      RequestType
    portfolio_id:      str
    workflow_id:       str
    strategy_id:       str
    account_id:        str
    session_id:        str
    timeout_s:         float
    dry_run:           bool
    priority:          str    # critical / high / medium / low
    environment:       str
    correlation_id:    str
    trace_id:          str
    metadata:          Dict[str, Any]
    framework_version: str = VERSION

    @classmethod
    def create(
        cls,
        request_type: RequestType,
        portfolio_id: str,
        *,
        context_id:    Optional[str]         = None,
        workflow_id:   str                   = "",
        strategy_id:   str                   = "",
        account_id:    str                   = "",
        session_id:    str                   = "",
        timeout_s:     float                 = DEFAULT_REQUEST_TIMEOUT_S,
        dry_run:       bool                  = False,
        priority:      str                   = "medium",
        environment:   str                   = "production",
        correlation_id: str                  = "",
        trace_id:      str                   = "",
        metadata:      Optional[Dict[str, Any]] = None,
    ) -> "RiskIntegrationContext":
        return cls(
            context_id     = context_id or str(uuid.uuid4()),
            request_type   = request_type,
            portfolio_id   = portfolio_id,
            workflow_id    = workflow_id,
            strategy_id    = strategy_id,
            account_id     = account_id,
            session_id     = session_id or str(uuid.uuid4()),
            timeout_s      = timeout_s,
            dry_run        = dry_run,
            priority       = priority,
            environment    = environment,
            correlation_id = correlation_id or str(uuid.uuid4()),
            trace_id       = trace_id       or str(uuid.uuid4()),
            metadata       = dict(metadata or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":      self.context_id,
            "request_type":    self.request_type.value,
            "portfolio_id":    self.portfolio_id,
            "workflow_id":     self.workflow_id,
            "strategy_id":     self.strategy_id,
            "account_id":      self.account_id,
            "session_id":      self.session_id,
            "timeout_s":       self.timeout_s,
            "dry_run":         self.dry_run,
            "priority":        self.priority,
            "environment":     self.environment,
            "correlation_id":  self.correlation_id,
            "trace_id":        self.trace_id,
            "framework_version": self.framework_version,
        }
