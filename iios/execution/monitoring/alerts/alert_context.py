"""iios/execution/monitoring/alerts/alert_context.py
==================================================
AlertContext — immutable input data passed to alert rules for evaluation.

The Alert Framework NEVER computes metrics.  AlertContext is
constructed from a MetricsSnapshot produced by M3.

C6 Execution Intelligence — Phase 6, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class AlertContext:
    """
    Immutable snapshot of pre-computed metrics passed to each AlertRule.

    The Alert Framework reads from this object only — it never modifies
    metrics or calls into the Metrics Framework.

    Fields
    ------
    context_id           : unique ID for this evaluation context
    session_id           : execution monitoring session identifier
    portfolio_id         : owning portfolio
    metrics              : flat dict of metric_key → float (from MetricsSnapshot)
    window_metrics       : Dict[window → Dict[metric_key → float]]
    timestamp            : wall-time at context creation
    gateway_id           : associated gateway (optional)
    strategy_id          : originating strategy (optional)
    execution_session_id : execution engine session (optional)
    tags                 : free-form string tags
    metadata             : arbitrary annotations
    """

    context_id:           str
    session_id:           str
    portfolio_id:         str
    metrics:              Dict[str, float]
    window_metrics:       Dict[str, Dict[str, float]]
    timestamp:            float

    gateway_id:           Optional[str]     = None
    strategy_id:          Optional[str]     = None
    execution_session_id: Optional[str]     = None
    tags:                 Tuple[str, ...]   = ()
    metadata:             Dict[str, Any]    = field(default_factory=dict)

    # ── Metric access helpers ─────────────────────────────────────────────────

    def get_metric(self, key: str, default: float = 0.0) -> float:
        """Return session-wide metric value for ``key``."""
        return self.metrics.get(key, default)

    def get_window_metric(
        self,
        window:  str,
        key:     str,
        default: float = 0.0,
    ) -> float:
        """Return windowed metric value for (``window``, ``key``)."""
        return self.window_metrics.get(window, {}).get(key, default)

    def has_metric(self, key: str) -> bool:
        return key in self.metrics

    def has_window_metric(self, window: str, key: str) -> bool:
        return key in self.window_metrics.get(window, {})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":   self.context_id,
            "session_id":   self.session_id,
            "portfolio_id": self.portfolio_id,
            "timestamp":    self.timestamp,
            "gateway_id":   self.gateway_id,
            "strategy_id":  self.strategy_id,
            "metric_count": len(self.metrics),
        }


def make_alert_context(
    session_id:   str,
    portfolio_id: str,
    metrics:      Dict[str, float],
    *,
    window_metrics:       Optional[Dict[str, Dict[str, float]]] = None,
    gateway_id:           Optional[str]   = None,
    strategy_id:          Optional[str]   = None,
    execution_session_id: Optional[str]   = None,
    tags:                 Tuple[str, ...] = (),
    metadata:             Optional[Dict[str, Any]] = None,
    context_id:           Optional[str]   = None,
    timestamp:            Optional[float] = None,
) -> AlertContext:
    """Factory for AlertContext."""
    return AlertContext(
        context_id           = context_id or str(uuid.uuid4()),
        session_id           = session_id,
        portfolio_id         = portfolio_id,
        metrics              = dict(metrics),
        window_metrics       = {k: dict(v) for k, v in (window_metrics or {}).items()},
        timestamp            = timestamp if timestamp is not None else time.time(),
        gateway_id           = gateway_id,
        strategy_id          = strategy_id,
        execution_session_id = execution_session_id,
        tags                 = tags,
        metadata             = dict(metadata) if metadata else {},
    )
