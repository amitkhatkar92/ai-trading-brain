"""
decision_optimization_context.py — iios.decision.optimization
==============================================================
DecisionOptimizationContext — wraps all inputs to the optimizer.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _navigate(data: dict, path: str, default: Any = None) -> Any:
    current: Any = data
    for key in path.split("."):
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


@dataclass(frozen=True)
class DecisionOptimizationContext:
    """
    Immutable context carrying all inputs to a single optimization run.

    Parameters
    ----------
    context_id :     Unique context identifier.
    request_id :     Originating request ID.
    decision_id :    The decision being optimized.
    session_id :     M1 lifecycle session ID (optional).
    pipeline_id :    M2 pipeline ID (optional).
    policy_result :  M3 policy response dict (for compliance context).
    inputs :         Key/value inputs (e.g. market data, signals).
    snapshots :      Named external snapshots (execution analytics,
                     recovery, monitoring, risk, portfolio, positions).
    metadata :       Arbitrary metadata.
    created_at :     Creation timestamp.
    framework_version : Framework version.
    """

    context_id:        str
    request_id:        str
    decision_id:       str
    session_id:        str               = ""
    pipeline_id:       str               = ""
    policy_result:     Dict[str, Any]    = field(default_factory=dict)
    inputs:            Dict[str, Any]    = field(default_factory=dict)
    snapshots:         Dict[str, Any]    = field(default_factory=dict)
    metadata:          Dict[str, Any]    = field(default_factory=dict)
    created_at:        datetime          = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    framework_version: str               = "1.0.0"

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def get(self, path: str, default: Any = None) -> Any:
        """Navigate a dotted path through the full context dict."""
        return _navigate(self.to_dict(), path, default)

    def to_dict(self) -> dict:
        return {
            "context_id":   self.context_id,
            "request_id":   self.request_id,
            "decision_id":  self.decision_id,
            "session_id":   self.session_id,
            "pipeline_id":  self.pipeline_id,
            "policy_result": dict(self.policy_result),
            "inputs":        dict(self.inputs),
            "snapshots":     self._serialise_snapshots(),
            "metadata":      dict(self.metadata),
        }

    def _serialise_snapshots(self) -> dict:
        out: dict = {}
        for key, snap in self.snapshots.items():
            if isinstance(snap, dict):
                out[key] = snap
            elif hasattr(snap, "to_dict") and callable(snap.to_dict):
                out[key] = snap.to_dict()
            elif hasattr(snap, "__dict__"):
                out[key] = snap.__dict__
            else:
                out[key] = str(snap)
        return out

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        context_id:    Optional[str]     = None,
        request_id:    str               = "",
        decision_id:   str               = "",
        session_id:    str               = "",
        pipeline_id:   str               = "",
        policy_result: Optional[Dict]    = None,
        inputs:        Optional[Dict]    = None,
        snapshots:     Optional[Dict]    = None,
        metadata:      Optional[Dict]    = None,
    ) -> "DecisionOptimizationContext":
        return cls(
            context_id    = context_id or str(uuid.uuid4()),
            request_id    = request_id,
            decision_id   = decision_id,
            session_id    = session_id,
            pipeline_id   = pipeline_id,
            policy_result = policy_result or {},
            inputs        = inputs    or {},
            snapshots     = snapshots or {},
            metadata      = metadata  or {},
        )

    @classmethod
    def from_engine_context(
        cls,
        engine_context: Any,
        *,
        policy_result: Optional[Dict] = None,
        snapshots:     Optional[Dict] = None,
    ) -> "DecisionOptimizationContext":
        """Build from an M2 ``DecisionEngineContext`` object."""
        return cls(
            context_id    = str(uuid.uuid4()),
            request_id    = getattr(engine_context, "request_id",  ""),
            decision_id   = getattr(engine_context, "decision_id", ""),
            session_id    = getattr(engine_context, "session_id",  ""),
            pipeline_id   = getattr(engine_context, "pipeline_id", ""),
            policy_result = policy_result or {},
            inputs        = dict(getattr(engine_context, "inputs", {}) or {}),
            snapshots     = snapshots or {},
            metadata      = dict(getattr(engine_context, "metadata", {}) or {}),
        )
