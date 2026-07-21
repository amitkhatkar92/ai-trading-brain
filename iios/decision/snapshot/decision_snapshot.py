"""
decision_snapshot.py — iios.decision.snapshot
==============================================
DecisionSnapshot — the ONLY published representation of the
Decision Intelligence subsystem.

Every downstream subsystem MUST consume DecisionSnapshot instead of
internal Decision objects.

DecisionSnapshot is:
  - Immutable (frozen dataclass)
  - Serializable to dict / JSON
  - Versioned
  - Auditable
  - Self-contained — no import of M1–M4 internal types

It performs NO policy evaluation.
It performs NO optimization.
It performs NO execution.

C9 Decision Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class DecisionSnapshot:
    """
    Immutable, self-contained snapshot of a completed Decision Intelligence run.

    This is the ONLY object published outside the Decision Intelligence
    subsystem.  All downstream modules (Execution, Portfolio, Compliance,
    Reporting, Dashboard) MUST use this object exclusively.

    Identity
    --------
    snapshot_id :           Unique identifier for this snapshot.
    snapshot_version :      Monotonically increasing version (per decision_id).
    schema_version :        Serialization schema version.

    Session context
    ---------------
    session_id :            Decision lifecycle session identifier (M1).
    decision_id :           Decision identifier (shared across M1–M4).
    workflow_id :           Workflow context identifier.
    execution_session_id :  Execution session identifier.
    portfolio_id :          Portfolio context identifier.
    strategy_id :           Strategy context identifier.

    Classification
    --------------
    decision_scope :        Scope of the decision (e.g. "order", "portfolio").
    decision_type :         Type of the decision (e.g. "order", "rebalance").
    decision_priority :     Scheduling priority string (e.g. "high").

    State
    -----
    lifecycle_state :       M1 lifecycle state at snapshot time.
    decision_status :       Combined status derived from policy + outcome.
    decision_health :       Overall health assessment.
    decision_outcome :      Final workflow outcome.
    snapshot_status :       Publication status of this snapshot.

    Decision content
    ----------------
    selected_decision :     Serialized dict of the selected candidate (None if
                            no candidate was selected).
    decision_confidence :   Confidence score of the selected decision [0, 1].
    decision_score :        Optimization score of the selected decision [0, 1].

    Summaries
    ---------
    optimization_summary :  Dict summary from M4 DecisionOptimizationSummary.
    ranking_summary :       Dict summary of candidate rankings from M4.
    constraint_summary :    Dict summary of constraint evaluation from M4.
    policy_summary :        Dict summary from M3 PolicyEvaluationSummary.
    evaluation_summary :    Dict summary of the end-to-end evaluation.

    Human-readable
    --------------
    decision_explanation :  Human-readable explanation of the decision.

    Observability
    -------------
    decision_statistics :   Dict of runtime statistics.
    decision_metadata :     Dict of supplementary classification metadata.
    audit_metadata :        Dict of audit trail information.

    Framework
    ---------
    framework_version :     Framework version string.
    created_at :            UTC timestamp of snapshot creation.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    snapshot_id:          str
    snapshot_version:     int
    schema_version:       str

    # ── Session context ───────────────────────────────────────────────────────
    session_id:           str
    decision_id:          str
    workflow_id:          str
    execution_session_id: str
    portfolio_id:         str
    strategy_id:          str

    # ── Classification ────────────────────────────────────────────────────────
    decision_scope:       str
    decision_type:        str
    decision_priority:    str

    # ── State ─────────────────────────────────────────────────────────────────
    lifecycle_state:      str
    decision_status:      DecisionStatus
    decision_health:      DecisionHealth
    decision_outcome:     DecisionOutcome
    snapshot_status:      SnapshotStatus

    # ── Decision content ──────────────────────────────────────────────────────
    selected_decision:    Optional[Dict[str, Any]]
    decision_confidence:  float
    decision_score:       float

    # ── Summaries ────────────────────────────────────────────────────────────
    optimization_summary: Dict[str, Any]
    ranking_summary:      Dict[str, Any]
    constraint_summary:   Dict[str, Any]
    policy_summary:       Dict[str, Any]
    evaluation_summary:   Dict[str, Any]

    # ── Human-readable ────────────────────────────────────────────────────────
    decision_explanation: str

    # ── Observability ─────────────────────────────────────────────────────────
    decision_statistics:  Dict[str, Any]
    decision_metadata:    Dict[str, Any]
    audit_metadata:       Dict[str, Any]

    # ── Framework ─────────────────────────────────────────────────────────────
    framework_version:    str
    created_at:           datetime

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def is_approved(self) -> bool:
        return self.decision_status in (
            DecisionStatus.APPROVED,
            DecisionStatus.APPROVED_CONDITIONAL,
        )

    @property
    def is_rejected(self) -> bool:
        return self.decision_status == DecisionStatus.REJECTED

    @property
    def is_blocked(self) -> bool:
        return self.decision_status == DecisionStatus.BLOCKED

    @property
    def is_failed(self) -> bool:
        return self.decision_status == DecisionStatus.FAILED

    @property
    def is_healthy(self) -> bool:
        return self.decision_health == DecisionHealth.HEALTHY

    @property
    def is_successful(self) -> bool:
        return self.decision_outcome == DecisionOutcome.SUCCESS

    @property
    def has_selection(self) -> bool:
        return self.selected_decision is not None

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a fully serializable dict representation."""
        return {
            # Identity
            "snapshot_id":          self.snapshot_id,
            "snapshot_version":     self.snapshot_version,
            "schema_version":       self.schema_version,
            # Session
            "session_id":           self.session_id,
            "decision_id":          self.decision_id,
            "workflow_id":          self.workflow_id,
            "execution_session_id": self.execution_session_id,
            "portfolio_id":         self.portfolio_id,
            "strategy_id":          self.strategy_id,
            # Classification
            "decision_scope":       self.decision_scope,
            "decision_type":        self.decision_type,
            "decision_priority":    self.decision_priority,
            # State
            "lifecycle_state":      self.lifecycle_state,
            "decision_status":      self.decision_status.value,
            "decision_health":      self.decision_health.value,
            "decision_outcome":     self.decision_outcome.value,
            "snapshot_status":      self.snapshot_status.value,
            # Content
            "selected_decision":    self.selected_decision,
            "decision_confidence":  self.decision_confidence,
            "decision_score":       self.decision_score,
            # Summaries
            "optimization_summary": dict(self.optimization_summary),
            "ranking_summary":      dict(self.ranking_summary),
            "constraint_summary":   dict(self.constraint_summary),
            "policy_summary":       dict(self.policy_summary),
            "evaluation_summary":   dict(self.evaluation_summary),
            # Human-readable
            "decision_explanation": self.decision_explanation,
            # Observability
            "decision_statistics":  dict(self.decision_statistics),
            "decision_metadata":    dict(self.decision_metadata),
            "audit_metadata":       dict(self.audit_metadata),
            # Framework
            "framework_version":    self.framework_version,
            "created_at":           self.created_at.isoformat(),
        }

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        session_id:            str,
        decision_id:           str,
        lifecycle_state:       str,
        decision_scope:        str,
        decision_type:         str,
        decision_priority:     str,
        decision_status:       DecisionStatus        = DecisionStatus.PENDING,
        decision_health:       DecisionHealth         = DecisionHealth.UNKNOWN,
        decision_outcome:      DecisionOutcome        = DecisionOutcome.UNKNOWN,
        snapshot_status:       SnapshotStatus         = SnapshotStatus.PENDING,
        snapshot_id:           Optional[str]          = None,
        snapshot_version:      int                    = 1,
        workflow_id:           str                    = "",
        execution_session_id:  str                    = "",
        portfolio_id:          str                    = "",
        strategy_id:           str                    = "",
        selected_decision:     Optional[Dict[str, Any]] = None,
        decision_confidence:   float                  = 0.0,
        decision_score:        float                  = 0.0,
        optimization_summary:  Optional[Dict[str, Any]] = None,
        ranking_summary:       Optional[Dict[str, Any]] = None,
        constraint_summary:    Optional[Dict[str, Any]] = None,
        policy_summary:        Optional[Dict[str, Any]] = None,
        evaluation_summary:    Optional[Dict[str, Any]] = None,
        decision_explanation:  str                    = "",
        decision_statistics:   Optional[Dict[str, Any]] = None,
        decision_metadata:     Optional[Dict[str, Any]] = None,
        audit_metadata:        Optional[Dict[str, Any]] = None,
        framework_version:     str                    = VERSION,
        created_at:            Optional[datetime]      = None,
    ) -> "DecisionSnapshot":
        """
        Construct a :class:`DecisionSnapshot`.

        Parameters with ``Optional`` type default to empty dicts / default
        enum values when not supplied.
        """
        return cls(
            snapshot_id           = snapshot_id or str(uuid.uuid4()),
            snapshot_version      = snapshot_version,
            schema_version        = SCHEMA_VERSION,
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
            optimization_summary  = optimization_summary  or {},
            ranking_summary       = ranking_summary       or {},
            constraint_summary    = constraint_summary    or {},
            policy_summary        = policy_summary        or {},
            evaluation_summary    = evaluation_summary    or {},
            decision_explanation  = decision_explanation,
            decision_statistics   = decision_statistics   or {},
            decision_metadata     = decision_metadata     or {},
            audit_metadata        = audit_metadata        or {},
            framework_version     = framework_version,
            created_at            = created_at or datetime.now(timezone.utc),
        )
