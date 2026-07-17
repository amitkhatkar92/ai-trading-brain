"""iios/execution/monitoring/metrics/metrics_context.py
==================================================
MetricsContext — immutable context for a metrics computation session.

C6 Execution Intelligence — Phase 6, Module 3
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import WindowSize


@dataclass(frozen=True)
class MetricsContext:
    """
    Immutable context attached to a metrics computation session.

    Carries all the identity and configuration needed to produce and
    correlate MetricsSnapshot objects.
    """

    # ── Required correlation IDs ──────────────────────────────────────────────
    session_id:  str
    portfolio_id: str

    # ── Optional correlation IDs ──────────────────────────────────────────────
    strategy_id:          Optional[str] = None
    gateway_id:           Optional[str] = None
    execution_session_id: Optional[str] = None
    workflow_id:          Optional[str] = None

    # ── Configuration ─────────────────────────────────────────────────────────
    default_window: WindowSize = WindowSize.FIVE_MINUTES

    # ── Metadata ──────────────────────────────────────────────────────────────
    tags:     Dict[str, str] = field(default_factory=dict, compare=False)
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: float = field(default_factory=time.time, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def has_gateway(self) -> bool:
        return bool(self.gateway_id)

    @property
    def has_strategy(self) -> bool:
        return bool(self.strategy_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id":           self.session_id,
            "portfolio_id":         self.portfolio_id,
            "strategy_id":          self.strategy_id,
            "gateway_id":           self.gateway_id,
            "execution_session_id": self.execution_session_id,
            "workflow_id":          self.workflow_id,
            "default_window":       self.default_window.value,
            "created_at":           self.created_at,
        }


def make_metrics_context(
    session_id:  str,
    portfolio_id: str,
    *,
    strategy_id:          Optional[str] = None,
    gateway_id:           Optional[str] = None,
    execution_session_id: Optional[str] = None,
    workflow_id:          Optional[str] = None,
    default_window:       WindowSize    = WindowSize.FIVE_MINUTES,
    tags:     Optional[Dict[str, str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> MetricsContext:
    return MetricsContext(
        session_id=session_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        gateway_id=gateway_id,
        execution_session_id=execution_session_id,
        workflow_id=workflow_id,
        default_window=default_window,
        tags=tags or {},
        metadata=metadata or {},
    )
