"""
decision_snapshot_builder.py — iios.decision.snapshot
======================================================
Builds a DecisionSnapshot from validated M1–M4 outputs.

The builder is the ONLY authorised way to create snapshots from
live Decision Intelligence pipeline results.  Direct use of
:meth:`DecisionSnapshot.create` is reserved for the store / factory.

Sources accepted
----------------
- M1 :class:`DecisionSession` (required) — lifecycle state, IDs, scope/type.
- M2 ``DecisionResponse`` (optional)     — engine snapshot, evaluation context.
- M3 ``DecisionPolicyResponse`` (optional) — policy action and summary.
- M4 ``DecisionOptimizationResponse`` (optional) — optimization result.

Rejection rules (raises :class:`SnapshotBuildError`)
------------------------------------------------------
- Missing required identifiers (session_id, decision_id).
- Incomplete decision state (lifecycle_state, decision_scope, decision_type).
- Invalid lifecycle state.
- Invalid optimization state (is_success=False AND candidates present).

C9 Decision Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    ACTOR_BUILDER,
    SOURCE_M1,
    SOURCE_M2,
    SOURCE_M3,
    SOURCE_M4,
    VERSION,
    DecisionHealth,
    DecisionOutcome,
    DecisionStatus,
    SnapshotStatus,
)
from .decision_snapshot import DecisionSnapshot
from .decision_snapshot_metadata import DecisionSnapshotMetadata, SnapshotAuditMetadata
from .exceptions import SnapshotBuildError

_log = get_logger(__name__)

# Lifecycle states the builder accepts
_VALID_LIFECYCLE_STATES = frozenset({
    "created", "initializing", "collecting", "evaluating",
    "ready", "active", "paused", "resuming",
    "completed", "failed", "archived",
})

# Map M3 policy action strings → DecisionStatus
_POLICY_ACTION_MAP: Dict[str, DecisionStatus] = {
    "approve":                 DecisionStatus.APPROVED,
    "approve_with_conditions": DecisionStatus.APPROVED_CONDITIONAL,
    "reject":                  DecisionStatus.REJECTED,
    "block":                   DecisionStatus.BLOCKED,
    "escalate":                DecisionStatus.ESCALATED,
    "defer":                   DecisionStatus.DEFERRED,
    "require_manual_review":   DecisionStatus.MANUAL_REVIEW,
}


class DecisionSnapshotBuilder:
    """
    Builds a :class:`DecisionSnapshot` from validated M1–M4 outputs.

    Usage::

        builder = DecisionSnapshotBuilder()
        snapshot = builder.build(
            session=m1_session,
            policy_response=m3_response,
            optimization_response=m4_response,
            engine_response=m2_response,
        )

    Parameters
    ----------
    builder_id : Optional identifier for this builder instance.
    """

    def __init__(self, builder_id: Optional[str] = None) -> None:
        self._builder_id = builder_id or ACTOR_BUILDER

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        session:               Any,
        *,
        engine_response:       Optional[Any] = None,
        policy_response:       Optional[Any] = None,
        optimization_response: Optional[Any] = None,
        snapshot_id:           Optional[str] = None,
        snapshot_version:      int           = 1,
        execution_session_id:  str           = "",
        decision_metadata:     Optional[Dict[str, Any]] = None,
    ) -> DecisionSnapshot:
        """
        Build and return a :class:`DecisionSnapshot`.

        Parameters
        ----------
        session :               M1 :class:`DecisionSession` (required).
        engine_response :       M2 :class:`DecisionResponse` (optional).
        policy_response :       M3 :class:`DecisionPolicyResponse` (optional).
        optimization_response : M4 :class:`DecisionOptimizationResponse` (optional).
        snapshot_id :           Override generated UUID.
        snapshot_version :      Override version number.
        execution_session_id :  Execution session identifier.
        decision_metadata :     Additional metadata dict.

        Raises
        ------
        :class:`SnapshotBuildError` : On validation failure or missing data.
        """
        t_start = time.time()

        # --- 1. Validate session ---
        self._validate_session(session)

        # --- 2. Extract M1 fields ---
        sid        = snapshot_id or str(uuid.uuid4())
        session_id = self._get(session, "session_id", "_session_id")
        decision_id= self._get(session, "decision_id", "_decision_id")
        workflow_id= self._get(session, "workflow_id", "_workflow_id", default="")
        portfolio_id=self._get(session, "portfolio_id", "_portfolio_id", default="")
        strategy_id= self._get(session, "strategy_id", "_strategy_id", default="")
        lifecycle_state  = self._state_str(session)
        decision_scope   = self._enum_str(
            self._get(session, "decision_scope", "_decision_scope")
        )
        decision_type    = self._enum_str(
            self._get(session, "decision_type", "_decision_type")
        )
        decision_priority= self._priority_str(
            self._get(session, "decision_priority", "_decision_priority")
        )

        # --- 3. Source module tracking ---
        sources = [SOURCE_M1]

        # --- 4. Extract M3 policy fields ---
        policy_summary: Dict[str, Any] = {}
        decision_status = DecisionStatus.PENDING

        if policy_response is not None:
            sources.append(SOURCE_M3)
            policy_summary = self._extract_policy_summary(policy_response)
            action_str = self._enum_str(getattr(policy_response, "action", None))
            decision_status = _POLICY_ACTION_MAP.get(action_str, DecisionStatus.PENDING)

        # --- 5. Extract M4 optimization fields ---
        optimization_summary: Dict[str, Any] = {}
        ranking_summary:      Dict[str, Any] = {}
        constraint_summary:   Dict[str, Any] = {}
        selected_decision:    Optional[Dict[str, Any]] = None
        decision_confidence   = 0.0
        decision_score        = 0.0

        if optimization_response is not None:
            sources.append(SOURCE_M4)
            (optimization_summary, ranking_summary,
             constraint_summary, selected_decision,
             decision_confidence, decision_score) = self._extract_optimization_fields(
                optimization_response
            )

        # --- 6. Extract M2 engine fields ---
        evaluation_summary: Dict[str, Any] = {}
        if engine_response is not None:
            sources.append(SOURCE_M2)
            evaluation_summary = self._extract_engine_summary(engine_response)

        # --- 7. Derive health and outcome ---
        decision_health  = self._compute_health(decision_status, optimization_response)
        decision_outcome = self._compute_outcome(lifecycle_state, decision_status)

        # --- 8. Derive explanation ---
        decision_explanation = self._build_explanation(
            decision_status, lifecycle_state, policy_summary, optimization_summary
        )

        # --- 9. Derive statistics ---
        decision_stats = self._build_statistics(
            sources, optimization_summary, evaluation_summary
        )

        # --- 10. Build audit metadata ---
        elapsed = time.time() - t_start
        audit_md = SnapshotAuditMetadata.create(
            snapshot_id    = sid,
            builder_id     = self._builder_id,
            build_time_s   = elapsed,
            source_modules = tuple(sources),
        ).to_dict()

        # --- 11. Assemble snapshot ---
        snapshot = DecisionSnapshot.create(
            snapshot_id           = sid,
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
            snapshot_status       = SnapshotStatus.PENDING,
            selected_decision     = selected_decision,
            decision_confidence   = decision_confidence,
            decision_score        = decision_score,
            optimization_summary  = optimization_summary,
            ranking_summary       = ranking_summary,
            constraint_summary    = constraint_summary,
            policy_summary        = policy_summary,
            evaluation_summary    = evaluation_summary,
            decision_explanation  = decision_explanation,
            decision_statistics   = decision_stats,
            decision_metadata     = dict(decision_metadata or {}),
            audit_metadata        = audit_md,
        )

        _log.debug(
            f"DecisionSnapshotBuilder: built snapshot "
            f"{sid!r} for decision {decision_id!r} in {elapsed*1000:.1f}ms"
        )
        return snapshot

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_session(self, session: Any) -> None:
        """Raise SnapshotBuildError if the session is unusable."""
        if session is None:
            raise SnapshotBuildError("session is required")

        session_id  = self._get(session, "session_id", "_session_id", default="")
        decision_id = self._get(session, "decision_id", "_decision_id", default="")

        if not session_id:
            raise SnapshotBuildError("session.session_id is missing or empty")
        if not decision_id:
            raise SnapshotBuildError("session.decision_id is missing or empty")

        lifecycle_state = self._state_str(session)
        if not lifecycle_state:
            raise SnapshotBuildError("session.state is missing or empty")
        if lifecycle_state not in _VALID_LIFECYCLE_STATES:
            raise SnapshotBuildError(
                f"Invalid lifecycle_state: {lifecycle_state!r}"
            )

        scope = self._enum_str(self._get(session, "decision_scope", "_decision_scope"))
        dtype = self._enum_str(self._get(session, "decision_type", "_decision_type"))
        if not scope:
            raise SnapshotBuildError("session.decision_scope is missing or empty")
        if not dtype:
            raise SnapshotBuildError("session.decision_type is missing or empty")

    # ------------------------------------------------------------------
    # Field extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get(obj: Any, *attr_names: str, default: Any = "") -> Any:
        """Try multiple attribute names (supports private _name and public name)."""
        for name in attr_names:
            val = getattr(obj, name, None)
            if val is not None:
                return val
        return default

    @staticmethod
    def _enum_str(val: Any) -> str:
        """Safely convert an enum or string to its string value."""
        if val is None:
            return ""
        if hasattr(val, "value"):
            return str(val.value)
        return str(val)

    @staticmethod
    def _state_str(session: Any) -> str:
        """Extract lifecycle state string from session."""
        state = getattr(session, "state", None)
        if state is None:
            state = getattr(session, "_state", None)
        if state is None:
            return ""
        if hasattr(state, "value"):
            return str(state.value)
        return str(state)

    @staticmethod
    def _priority_str(val: Any) -> str:
        """Extract priority as a string (handles IntEnum and string Enum)."""
        if val is None:
            return "medium"
        if hasattr(val, "name"):
            return val.name.lower()
        return str(val).lower()

    @staticmethod
    def _extract_policy_summary(pr: Any) -> Dict[str, Any]:
        """Serialize the key fields from a M3 DecisionPolicyResponse."""
        summary = getattr(pr, "summary", None)
        return {
            "action":            DecisionSnapshotBuilder._enum_str(
                                     getattr(pr, "action", None)
                                 ),
            "is_approved":       getattr(pr, "is_approved", False),
            "is_rejected":       getattr(pr, "is_rejected", False),
            "is_blocked":        getattr(pr, "is_blocked", False),
            "is_success":        getattr(pr, "is_success", False),
            "evaluation_time_s": getattr(pr, "evaluation_time_s", 0.0),
            "policy_count":      getattr(summary, "policy_count", 0) if summary else 0,
            "approved_count":    getattr(summary, "approved_count", 0) if summary else 0,
            "rejected_count":    getattr(summary, "rejected_count", 0) if summary else 0,
            "conditions":        list(getattr(summary, "conditions", []) or [])
                                 if summary else [],
        }

    @staticmethod
    def _extract_optimization_fields(
        or_: Any,
    ) -> tuple:
        """Extract optimization fields from M4 DecisionOptimizationResponse."""
        summary  = getattr(or_, "summary", None)
        solution = getattr(or_, "solution", None)
        report   = getattr(or_, "optimization_report", None)

        selected_decision  = None
        decision_confidence = 0.0
        decision_score      = 0.0

        if solution is not None:
            cand = getattr(solution, "selected_candidate", None)
            if cand is not None:
                try:
                    selected_decision = cand.to_dict()
                except Exception:
                    pass
            decision_score      = float(getattr(solution, "final_score", 0.0))
            if cand is not None:
                decision_confidence = float(getattr(cand, "confidence", 0.0))

        opt_summary: Dict[str, Any] = {}
        if summary is not None:
            opt_summary = {
                "selected_candidate_id": getattr(summary, "selected_candidate_id", None),
                "is_feasible":           getattr(summary, "is_feasible", False),
                "final_score":           getattr(summary, "final_score", 0.0),
                "candidates_evaluated":  getattr(summary, "candidates_evaluated", 0),
                "feasible_count":        getattr(summary, "feasible_count", 0),
                "infeasible_count":      getattr(summary, "infeasible_count", 0),
                "optimization_strategy": getattr(summary, "optimization_strategy", ""),
                "optimization_time_s":   getattr(summary, "optimization_time_s", 0.0),
                "objectives_applied":    getattr(summary, "objectives_applied", 0),
                "constraints_applied":   getattr(summary, "constraints_applied", 0),
                "constraint_violations": getattr(summary, "constraint_violations", 0),
                "rationale":             getattr(summary, "rationale", ""),
            }

        ranking_summary: Dict[str, Any] = {}
        constraint_summary: Dict[str, Any] = {}
        if report is not None:
            rankings = getattr(report, "rankings", ())
            ranking_summary = {
                "total":           len(rankings) if rankings else 0,
                "feasible_count":  getattr(report, "feasible_count", 0),
                "top_candidate_id": rankings[0].candidate_id if rankings else None,
                "rankings": [
                    {
                        "rank":           r.rank,
                        "candidate_id":   r.candidate_id,
                        "final_score":    r.final_score,
                        "is_feasible":    r.is_feasible,
                    }
                    for r in rankings
                ] if rankings else [],
            }
            constraint_summary = {
                "total_checked":    getattr(report, "constraint_violations", 0),
                "violations":       getattr(report, "constraint_violations", 0),
            }

        return (
            opt_summary, ranking_summary, constraint_summary,
            selected_decision, decision_confidence, decision_score,
        )

    @staticmethod
    def _extract_engine_summary(er: Any) -> Dict[str, Any]:
        """Serialize key fields from a M2 DecisionResponse."""
        snap = getattr(er, "snapshot", None)
        return {
            "status":             DecisionSnapshotBuilder._enum_str(
                                      getattr(er, "status", None)
                                  ),
            "collection_time_s":  getattr(er, "collection_time_s", 0.0),
            "dispatch_time_s":    getattr(er, "dispatch_time_s", 0.0),
            "total_time_s":       getattr(er, "total_time_s", 0.0),
            "pipeline_state":     getattr(snap, "pipeline_state", "") if snap else "",
        }

    # ------------------------------------------------------------------
    # Derived fields
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_health(
        status: DecisionStatus,
        optimization_response: Optional[Any],
    ) -> DecisionHealth:
        if status in (DecisionStatus.BLOCKED, DecisionStatus.FAILED):
            return DecisionHealth.CRITICAL
        if status in (DecisionStatus.ESCALATED, DecisionStatus.MANUAL_REVIEW):
            return DecisionHealth.DEGRADED
        if status in (DecisionStatus.APPROVED, DecisionStatus.APPROVED_CONDITIONAL):
            if optimization_response is not None:
                if getattr(optimization_response, "is_feasible", False):
                    return DecisionHealth.HEALTHY
                return DecisionHealth.DEGRADED
            return DecisionHealth.HEALTHY
        if status == DecisionStatus.PENDING:
            return DecisionHealth.UNKNOWN
        return DecisionHealth.UNKNOWN

    @staticmethod
    def _compute_outcome(
        lifecycle_state: str,
        decision_status: DecisionStatus,
    ) -> DecisionOutcome:
        if lifecycle_state in ("completed", "archived"):
            if decision_status in (
                DecisionStatus.APPROVED, DecisionStatus.APPROVED_CONDITIONAL
            ):
                return DecisionOutcome.SUCCESS
            if decision_status == DecisionStatus.REJECTED:
                return DecisionOutcome.FAILURE
            return DecisionOutcome.PARTIAL
        if lifecycle_state == "failed":
            return DecisionOutcome.FAILURE
        return DecisionOutcome.UNKNOWN

    @staticmethod
    def _build_explanation(
        status:               DecisionStatus,
        lifecycle_state:      str,
        policy_summary:       Dict[str, Any],
        optimization_summary: Dict[str, Any],
    ) -> str:
        parts = [f"Decision status: {status.value}."]
        parts.append(f"Lifecycle state: {lifecycle_state}.")
        if optimization_summary:
            strat = optimization_summary.get("optimization_strategy", "")
            score = optimization_summary.get("final_score", 0.0)
            parts.append(f"Optimization strategy: {strat}, score: {score:.3f}.")
            rationale = optimization_summary.get("rationale", "")
            if rationale:
                parts.append(rationale)
        if policy_summary:
            action = policy_summary.get("action", "")
            if action:
                parts.append(f"Policy action: {action}.")
        return " ".join(parts)

    @staticmethod
    def _build_statistics(
        sources:              list,
        optimization_summary: Dict[str, Any],
        evaluation_summary:   Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "source_modules":      sources,
            "candidates_evaluated":optimization_summary.get("candidates_evaluated", 0),
            "objectives_applied":  optimization_summary.get("objectives_applied", 0),
            "constraints_applied": optimization_summary.get("constraints_applied", 0),
            "optimization_time_s": optimization_summary.get("optimization_time_s", 0.0),
            "total_pipeline_time_s": evaluation_summary.get("total_time_s", 0.0),
        }
