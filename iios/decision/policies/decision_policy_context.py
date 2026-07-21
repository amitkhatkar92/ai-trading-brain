"""
decision_policy_context.py — iios.decision.policies
=====================================================
Evaluation context that wraps all inputs to the policy engine.

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _navigate(data: dict, path: str, default: Any = None) -> Any:
    """Navigate a dotted path through nested dicts."""
    current: Any = data
    for key in path.split("."):
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


@dataclass(frozen=True)
class PolicyEvaluationContext:
    """
    Immutable context object that carries all inputs to a policy evaluation.

    Inputs are accessible via a dotted path using :meth:`get`.

    Parameters
    ----------
    context_id :   Unique context identifier.
    request_id :   Originating request ID (from M2 DecisionRequest or external).
    decision_id :  Decision being evaluated.
    session_id :   M1 lifecycle session ID (optional).
    pipeline_id :  M2 pipeline ID (optional).
    inputs :       Key/value inputs from the decision request.
    snapshots :    Named external data snapshots (execution analytics,
                   risk, portfolio, position, order, etc.).
    metadata :     Arbitrary metadata.
    created_at :   Creation timestamp.
    framework_version : Version string.
    """

    context_id:        str
    request_id:        str
    decision_id:       str
    session_id:        str                   = ""
    pipeline_id:       str                   = ""
    inputs:            Dict[str, Any]        = field(default_factory=dict)
    snapshots:         Dict[str, Any]        = field(default_factory=dict)
    metadata:          Dict[str, Any]        = field(default_factory=dict)
    created_at:        datetime              = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    framework_version: str                   = "1.0.0"

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def get(self, path: str, default: Any = None) -> Any:
        """
        Retrieve a value by dotted path from the context's full data dict.

        The path is resolved against ``to_dict()``.

        Examples
        --------
        ctx.get("inputs.price")
        ctx.get("snapshots.execution_risk.var_pct")
        """
        return _navigate(self.to_dict(), path, default)

    def to_dict(self) -> dict:
        """Return a flat/nested dict suitable for condition evaluation."""
        return {
            "context_id":  self.context_id,
            "request_id":  self.request_id,
            "decision_id": self.decision_id,
            "session_id":  self.session_id,
            "pipeline_id": self.pipeline_id,
            "inputs":      dict(self.inputs),
            "snapshots":   self._serialise_snapshots(),
            "metadata":    dict(self.metadata),
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
        context_id:    Optional[str]       = None,
        request_id:    str                  = "",
        decision_id:   str                  = "",
        session_id:    str                  = "",
        pipeline_id:   str                  = "",
        inputs:        Optional[Dict]       = None,
        snapshots:     Optional[Dict]       = None,
        metadata:      Optional[Dict]       = None,
    ) -> "PolicyEvaluationContext":
        """Create a new :class:`PolicyEvaluationContext`."""
        return cls(
            context_id  = context_id or str(uuid.uuid4()),
            request_id  = request_id,
            decision_id = decision_id,
            session_id  = session_id,
            pipeline_id = pipeline_id,
            inputs      = inputs   or {},
            snapshots   = snapshots or {},
            metadata    = metadata  or {},
        )

    @classmethod
    def from_engine_context(
        cls,
        engine_context: Any,
        *,
        snapshots: Optional[Dict] = None,
    ) -> "PolicyEvaluationContext":
        """Build from an M2 ``DecisionEngineContext`` object."""
        return cls(
            context_id  = str(uuid.uuid4()),
            request_id  = getattr(engine_context, "request_id",  ""),
            decision_id = getattr(engine_context, "decision_id", ""),
            session_id  = getattr(engine_context, "session_id",  ""),
            pipeline_id = getattr(engine_context, "pipeline_id", ""),
            inputs      = dict(getattr(engine_context, "inputs", {}) or {}),
            snapshots   = snapshots or {},
            metadata    = dict(getattr(engine_context, "metadata", {}) or {}),
        )
