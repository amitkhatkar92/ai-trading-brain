"""
iios/execution/analytics/lifecycle/analytics_context.py
=======================================================
AnalyticsContext — immutable creation context for an analytics session.

Captures all inputs needed to create and identify a session.

C8 Execution Analytics & Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import (
    ACTOR_SYSTEM,
    VERSION,
    AnalyticsMode,
    AnalyticsScope,
    AnalyticsTrigger,
)


@dataclass(frozen=True)
class AnalyticsContext:
    """
    Immutable context that parameterises an analytics session.

    Passed to AnalyticsFactory.create() and stored on the session for
    full audit traceability.

    Fields
    ------
    context_id:            Unique ID for this context.
    execution_session_id:  Parent execution session being analysed.
    analytics_scope:       Scope of the analysis.
    analytics_mode:        Operational mode.
    analytics_trigger:     What triggered the session.
    workflow_id:           Associated workflow (optional).
    portfolio_id:          Associated portfolio (optional).
    strategy_id:           Associated strategy (optional).
    analytics_version:     Analytics framework version requested.
    requester:             Actor requesting the session.
    tags:                  Classification tags.
    metadata:              Caller-supplied key-value pairs.
    created_at:            Wall-time of context creation.
    """

    context_id:            str
    execution_session_id:  str
    analytics_scope:       AnalyticsScope
    analytics_mode:        AnalyticsMode
    analytics_trigger:     AnalyticsTrigger
    workflow_id:           str            = ""
    portfolio_id:          str            = ""
    strategy_id:           str            = ""
    analytics_version:     int            = 1
    requester:             str            = ACTOR_SYSTEM
    tags:                  Tuple[str, ...] = ()
    metadata:              Dict[str, Any]  = field(default_factory=dict)
    created_at:            float          = field(default_factory=time.time)
    framework_version:     str            = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":            self.context_id,
            "execution_session_id":  self.execution_session_id,
            "analytics_scope":       self.analytics_scope.value,
            "analytics_mode":        self.analytics_mode.value,
            "analytics_trigger":     self.analytics_trigger.value,
            "workflow_id":           self.workflow_id,
            "portfolio_id":          self.portfolio_id,
            "strategy_id":           self.strategy_id,
            "analytics_version":     self.analytics_version,
            "requester":             self.requester,
            "tags":                  list(self.tags),
            "created_at":            self.created_at,
            "framework_version":     self.framework_version,
        }


def make_analytics_context(
    execution_session_id: str,
    *,
    analytics_scope:    AnalyticsScope   = AnalyticsScope.EXECUTION,
    analytics_mode:     AnalyticsMode    = AnalyticsMode.ON_DEMAND,
    analytics_trigger:  AnalyticsTrigger = AnalyticsTrigger.AUTOMATIC,
    workflow_id:        str              = "",
    portfolio_id:       str              = "",
    strategy_id:        str              = "",
    analytics_version:  int              = 1,
    requester:          str              = ACTOR_SYSTEM,
    tags:               Optional[Tuple[str, ...]]  = None,
    metadata:           Optional[Dict[str, Any]]   = None,
    context_id:         Optional[str]              = None,
) -> AnalyticsContext:
    """Factory for AnalyticsContext."""
    return AnalyticsContext(
        context_id           = context_id or str(uuid.uuid4()),
        execution_session_id = execution_session_id,
        analytics_scope      = analytics_scope,
        analytics_mode       = analytics_mode,
        analytics_trigger    = analytics_trigger,
        workflow_id          = workflow_id,
        portfolio_id         = portfolio_id,
        strategy_id          = strategy_id,
        analytics_version    = analytics_version,
        requester            = requester,
        tags                 = tags or (),
        metadata             = dict(metadata) if metadata else {},
    )
