"""iios/execution/monitoring/integration/monitoring_integration_context.py
==================================================
MonitoringIntegrationContext — immutable context for an integration
monitoring request.

C6 Execution Intelligence — Phase 6, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import VERSION


@dataclass(frozen=True)
class MonitoringIntegrationContext:
    """
    Immutable context identifying and configuring an integration session.

    This is the caller-supplied identity envelope.  The integration engine
    validates it, creates a MonitoringSession from it (M1), and threads
    the identity through the metrics and alert sub-systems.

    Fields
    ------
    context_id:          Unique ID for this context instance.
    session_id:          External session / correlation ID.
    portfolio_id:        Owning portfolio.
    gateway_id:          Optional gateway correlation.
    strategy_id:         Optional strategy correlation.
    workflow_id:         Optional workflow correlation.
    order_id:            Optional order correlation.
    tags:                Immutable string tags for routing / filtering.
    metadata:            Arbitrary caller-provided metadata.
    created_at:          Wall-time the context was created.
    framework_version:   Version for compatibility checks.
    """

    context_id:        str
    session_id:        str
    portfolio_id:      str

    # Optional correlations
    gateway_id:        Optional[str]        = None
    strategy_id:       Optional[str]        = None
    workflow_id:       Optional[str]        = None
    order_id:          Optional[str]        = None

    tags:              Tuple[str, ...]      = ()
    metadata:          Dict[str, Any]       = field(default_factory=dict, compare=False)

    created_at:        float                = field(default_factory=time.time, compare=False)
    framework_version: str                  = VERSION

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def has_gateway(self) -> bool:
        return bool(self.gateway_id)

    @property
    def has_strategy(self) -> bool:
        return bool(self.strategy_id)

    @property
    def has_workflow(self) -> bool:
        return bool(self.workflow_id)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":        self.context_id,
            "session_id":        self.session_id,
            "portfolio_id":      self.portfolio_id,
            "gateway_id":        self.gateway_id,
            "strategy_id":       self.strategy_id,
            "workflow_id":       self.workflow_id,
            "order_id":          self.order_id,
            "tags":              list(self.tags),
            "metadata":          dict(self.metadata),
            "created_at":        self.created_at,
            "framework_version": self.framework_version,
        }


def make_monitoring_integration_context(
    session_id:   str,
    portfolio_id: str,
    *,
    gateway_id:  Optional[str]        = None,
    strategy_id: Optional[str]        = None,
    workflow_id: Optional[str]        = None,
    order_id:    Optional[str]        = None,
    tags:        Tuple[str, ...]      = (),
    metadata:    Optional[Dict[str, Any]] = None,
    context_id:  Optional[str]        = None,
) -> MonitoringIntegrationContext:
    """Factory for ``MonitoringIntegrationContext``."""
    return MonitoringIntegrationContext(
        context_id    = context_id or str(uuid.uuid4()),
        session_id    = session_id,
        portfolio_id  = portfolio_id,
        gateway_id    = gateway_id,
        strategy_id   = strategy_id,
        workflow_id   = workflow_id,
        order_id      = order_id,
        tags          = tags,
        metadata      = metadata or {},
    )
