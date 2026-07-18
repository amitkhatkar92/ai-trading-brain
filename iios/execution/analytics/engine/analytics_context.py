"""
iios/execution/analytics/engine/analytics_context.py
====================================================
EngineAnalyticsContext — immutable analytics request context for the
Execution Analytics Engine.

Carries all inputs required to run an analytics workflow cycle.
Input snapshots are Optional to accommodate partial subsystem availability.

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import ACTOR_SYSTEM, VERSION


@dataclass(frozen=True)
class EngineAnalyticsContext:
    """
    Immutable context passed into an analytics workflow cycle.

    Bundles the analytics request with all available execution subsystem
    snapshots.  Any snapshot field may be None if that subsystem is
    unavailable at request time.

    Fields
    ------
    context_id:           Unique ID for this context.
    request_id:           Parent AnalyticsRequest ID.
    execution_session_id: The execution session being analysed.
    monitoring_snapshot:  Optional snapshot from the Monitoring subsystem.
    recovery_snapshot:    Optional snapshot from the Recovery subsystem.
    gateway_snapshot:     Optional snapshot from the Gateway subsystem.
    risk_snapshot:        Optional snapshot from the Risk subsystem.
    execution_context:    Optional execution context object.
    requester:            Actor requesting this analytics cycle.
    priority:             Request priority (1 = highest, 10 = lowest).
    tags:                 Classification tags.
    metadata:             Caller-supplied key-value pairs.
    created_at:           Wall-time of context creation.
    framework_version:    Framework version.
    """

    context_id:           str
    request_id:           str
    execution_session_id: str
    monitoring_snapshot:  Optional[Any]   = None
    recovery_snapshot:    Optional[Any]   = None
    gateway_snapshot:     Optional[Any]   = None
    risk_snapshot:        Optional[Any]   = None
    execution_context:    Optional[Any]   = None
    requester:            str             = ACTOR_SYSTEM
    priority:             int             = 5
    tags:                 Tuple[str, ...] = field(default_factory=tuple)
    metadata:             Dict[str, Any]  = field(default_factory=dict)
    created_at:           float           = field(default_factory=time.time)
    framework_version:    str             = VERSION

    @property
    def available_snapshot_count(self) -> int:
        """Number of input snapshots that are not None."""
        return sum(
            1 for s in (
                self.monitoring_snapshot,
                self.recovery_snapshot,
                self.gateway_snapshot,
                self.risk_snapshot,
            )
            if s is not None
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id":              self.context_id,
            "request_id":              self.request_id,
            "execution_session_id":    self.execution_session_id,
            "has_monitoring_snapshot": self.monitoring_snapshot is not None,
            "has_recovery_snapshot":   self.recovery_snapshot   is not None,
            "has_gateway_snapshot":    self.gateway_snapshot    is not None,
            "has_risk_snapshot":       self.risk_snapshot       is not None,
            "has_execution_context":   self.execution_context   is not None,
            "available_snapshots":     self.available_snapshot_count,
            "requester":               self.requester,
            "priority":                self.priority,
            "tags":                    list(self.tags),
            "created_at":              self.created_at,
            "framework_version":       self.framework_version,
        }


def make_engine_analytics_context(
    request_id:           str,
    execution_session_id: str,
    *,
    context_id:          Optional[str]           = None,
    monitoring_snapshot: Optional[Any]           = None,
    recovery_snapshot:   Optional[Any]           = None,
    gateway_snapshot:    Optional[Any]           = None,
    risk_snapshot:       Optional[Any]           = None,
    execution_context:   Optional[Any]           = None,
    requester:           str                     = ACTOR_SYSTEM,
    priority:            int                     = 5,
    tags:                Tuple[str, ...]          = (),
    metadata:            Optional[Dict[str, Any]] = None,
) -> EngineAnalyticsContext:
    """Create a new EngineAnalyticsContext."""
    return EngineAnalyticsContext(
        context_id           = context_id or str(uuid.uuid4()),
        request_id           = request_id,
        execution_session_id = execution_session_id,
        monitoring_snapshot  = monitoring_snapshot,
        recovery_snapshot    = recovery_snapshot,
        gateway_snapshot     = gateway_snapshot,
        risk_snapshot        = risk_snapshot,
        execution_context    = execution_context,
        requester            = requester,
        priority             = priority,
        tags                 = tags,
        metadata             = metadata or {},
    )
