"""
decision_snapshot_factory.py — iios.decision.snapshot
======================================================
Stateless factory for constructing DecisionSnapshot objects directly
from raw data without requiring live M1-M4 objects.

Use when:
- Reconstructing snapshots from persistent storage.
- Unit testing without full M1–M4 wiring.
- Creating minimal snapshots from dict payloads.

C9 Decision Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import (
    SCHEMA_VERSION,
    VERSION,
    DecisionHealth,
    DecisionOutcome,
    DecisionStatus,
    SnapshotStatus,
)
from .decision_snapshot import DecisionSnapshot


class DecisionSnapshotFactory:
    """Stateless factory for :class:`DecisionSnapshot` objects."""

    def create(
        self,
        *,
        session_id:            str,
        decision_id:           str,
        lifecycle_state:       str,
        decision_scope:        str,
        decision_type:         str,
        decision_priority:     str,
        snapshot_id:           Optional[str]           = None,
        snapshot_version:      int                     = 1,
        workflow_id:           str                     = "",
        execution_session_id:  str                     = "",
        portfolio_id:          str                     = "",
        strategy_id:           str                     = "",
        decision_status:       DecisionStatus           = DecisionStatus.PENDING,
        decision_health:       DecisionHealth            = DecisionHealth.UNKNOWN,
        decision_outcome:      DecisionOutcome           = DecisionOutcome.UNKNOWN,
        snapshot_status:       SnapshotStatus            = SnapshotStatus.PENDING,
        selected_decision:     Optional[Dict[str, Any]] = None,
        decision_confidence:   float                    = 0.0,
        decision_score:        float                    = 0.0,
        optimization_summary:  Optional[Dict[str, Any]] = None,
        ranking_summary:       Optional[Dict[str, Any]] = None,
        constraint_summary:    Optional[Dict[str, Any]] = None,
        policy_summary:        Optional[Dict[str, Any]] = None,
        evaluation_summary:    Optional[Dict[str, Any]] = None,
        decision_explanation:  str                     = "",
        decision_statistics:   Optional[Dict[str, Any]] = None,
        decision_metadata:     Optional[Dict[str, Any]] = None,
        audit_metadata:        Optional[Dict[str, Any]] = None,
        framework_version:     str                     = VERSION,
        created_at:            Optional[datetime]       = None,
    ) -> DecisionSnapshot:
        """
        Create a :class:`DecisionSnapshot` from raw parameters.

        All required fields must be supplied; optional fields default to
        empty values.
        """
        return DecisionSnapshot.create(
            snapshot_id           = snapshot_id,
            snapshot_version      = snapshot_version,
            session_id            = session_id,
            decision_id           = decision_id,
            workflow_id           = workflow_id,
            execution_session_id  = execution_session_id,
            portfolio_id          = portfolio_id,
            strategy_id           = strategy_id,
            decision_scope        = decision_scope,
            decision_type         = decision_type,
            decision_priority     = decision_priority,
            lifecycle_state       = lifecycle_state,
            decision_status       = decision_status,
            decision_health       = decision_health,
            decision_outcome      = decision_outcome,
            snapshot_status       = snapshot_status,
            selected_decision     = selected_decision,
            decision_confidence   = decision_confidence,
            decision_score        = decision_score,
            optimization_summary  = optimization_summary,
            ranking_summary       = ranking_summary,
            constraint_summary    = constraint_summary,
            policy_summary        = policy_summary,
            evaluation_summary    = evaluation_summary,
            decision_explanation  = decision_explanation,
            decision_statistics   = decision_statistics,
            decision_metadata     = decision_metadata,
            audit_metadata        = audit_metadata,
            framework_version     = framework_version,
            created_at            = created_at,
        )

    def from_dict(self, data: Dict[str, Any]) -> DecisionSnapshot:
        """
        Reconstruct a :class:`DecisionSnapshot` from a serialised dict.

        Missing fields fall back to safe defaults.
        """
        created_at_raw = data.get("created_at")
        created_at: Optional[datetime] = None
        if isinstance(created_at_raw, datetime):
            created_at = created_at_raw
        elif isinstance(created_at_raw, str):
            try:
                created_at = datetime.fromisoformat(created_at_raw)
            except ValueError:
                pass

        def _status(val, cls, default):
            if val is None:
                return default
            try:
                return cls(val)
            except ValueError:
                return default

        return self.create(
            session_id            = data.get("session_id", ""),
            decision_id           = data.get("decision_id", ""),
            lifecycle_state       = data.get("lifecycle_state", "created"),
            decision_scope        = data.get("decision_scope", ""),
            decision_type         = data.get("decision_type", ""),
            decision_priority     = data.get("decision_priority", "medium"),
            snapshot_id           = data.get("snapshot_id"),
            snapshot_version      = int(data.get("snapshot_version", 1)),
            workflow_id           = data.get("workflow_id", ""),
            execution_session_id  = data.get("execution_session_id", ""),
            portfolio_id          = data.get("portfolio_id", ""),
            strategy_id           = data.get("strategy_id", ""),
            decision_status       = _status(
                data.get("decision_status"), DecisionStatus, DecisionStatus.PENDING
            ),
            decision_health       = _status(
                data.get("decision_health"), DecisionHealth, DecisionHealth.UNKNOWN
            ),
            decision_outcome      = _status(
                data.get("decision_outcome"), DecisionOutcome, DecisionOutcome.UNKNOWN
            ),
            snapshot_status       = _status(
                data.get("snapshot_status"), SnapshotStatus, SnapshotStatus.PENDING
            ),
            selected_decision     = data.get("selected_decision"),
            decision_confidence   = float(data.get("decision_confidence", 0.0)),
            decision_score        = float(data.get("decision_score", 0.0)),
            optimization_summary  = dict(data.get("optimization_summary") or {}),
            ranking_summary       = dict(data.get("ranking_summary") or {}),
            constraint_summary    = dict(data.get("constraint_summary") or {}),
            policy_summary        = dict(data.get("policy_summary") or {}),
            evaluation_summary    = dict(data.get("evaluation_summary") or {}),
            decision_explanation  = data.get("decision_explanation", ""),
            decision_statistics   = dict(data.get("decision_statistics") or {}),
            decision_metadata     = dict(data.get("decision_metadata") or {}),
            audit_metadata        = dict(data.get("audit_metadata") or {}),
            framework_version     = data.get("framework_version", VERSION),
            created_at            = created_at,
        )
