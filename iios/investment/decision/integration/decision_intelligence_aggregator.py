"""iios/investment/decision/integration/decision_intelligence_aggregator.py
DecisionIntelligenceAggregator — main entry point for submitting upstream
snapshots and retrieving the current aggregation state.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.investment.decision.confidence.confidence_snapshot import ConfidenceSnapshot
from iios.investment.decision.evidence.evidence_snapshot import EvidenceSnapshot
from iios.investment.decision.explainability.explanation_snapshot import ExplanationSnapshot
from iios.investment.decision.reasoning.reasoning_snapshot import ReasoningSnapshot
from iios.investment.decision.risk.risk_snapshot import RiskSnapshot

from iios.investment.decision.integration.aggregation_engine import AggregationEngine
from iios.investment.decision.integration.aggregation_history import AggregationHistory
from iios.investment.decision.integration.aggregation_state import (
    AggregationState,
    _AggregationStateSnapshot,
)
from iios.investment.decision.integration.integration_constants import ComponentId


class DecisionIntelligenceAggregator:
    """
    Thread-safe multi-decision aggregator.

    Maintains one AggregationState per active decision_id.
    Clients submit snapshots from individual engines; the aggregator
    merges them and records each update in history.
    """

    def __init__(self) -> None:
        self._lock:   threading.RLock               = threading.RLock()
        self._states: Dict[str, AggregationState]   = {}
        self._engine: AggregationEngine             = AggregationEngine()
        self._history: AggregationHistory           = AggregationHistory()

    # ── Submit methods ────────────────────────────────────────────────────────

    def submit_evidence(self, snapshot: EvidenceSnapshot) -> None:
        self._submit(snapshot.decision_id, snapshot.subject_id,
                     snapshot.subject_type, ComponentId.EVIDENCE, snapshot)

    def submit_reasoning(self, snapshot: ReasoningSnapshot) -> None:
        self._submit(snapshot.decision_id, snapshot.subject_id,
                     snapshot.subject_type, ComponentId.REASONING, snapshot)

    def submit_confidence(self, snapshot: ConfidenceSnapshot) -> None:
        # ConfidenceSnapshot may not carry subject_id — use decision_id key
        did  = getattr(snapshot, "snapshot_id", snapshot.snapshot_id)
        sid  = getattr(snapshot, "subject_id",  "")
        stype= getattr(snapshot, "subject_type", "equity")
        # We need decision_id — ConfidenceSnapshot uses snapshot_id as key
        # Use a separate mapping maintained by the engine
        state = self._get_or_create_by_snapshot_id(did, sid, stype)
        state.update(ComponentId.CONFIDENCE, snapshot)
        self._history.record(state.snapshot())

    def submit_risk(self, snapshot: RiskSnapshot) -> None:
        self._submit(snapshot.decision_id, snapshot.decision_id,
                     "equity", ComponentId.RISK, snapshot)

    def submit_explanation(self, snapshot: ExplanationSnapshot) -> None:
        self._submit(snapshot.decision_id, snapshot.subject_id,
                     snapshot.subject_type, ComponentId.EXPLANATION, snapshot)

    def submit_committee(self, report: Any) -> None:
        """Accept CommitteeReport (or any duck-typed equivalent)."""
        did  = getattr(report, "decision_id", None)
        sid  = getattr(report, "subject_id",  None)
        stype= getattr(report, "subject_type", "equity")
        if did is None:
            raise ValueError("committee report must have decision_id")
        self._submit(did, sid or did, stype, ComponentId.COMMITTEE, report)

    def submit_recommendation(self, snapshot: Any) -> None:
        """Accept RecommendationSnapshot (duck-typed)."""
        did  = getattr(snapshot, "decision_id", None)
        sid  = getattr(snapshot, "subject_id",  None)
        stype= getattr(snapshot, "subject_type", "equity")
        if did is None:
            raise ValueError("recommendation snapshot must have decision_id")
        self._submit(did, sid or did, stype, ComponentId.RECOMMENDATION, snapshot)

    # ── Query methods ─────────────────────────────────────────────────────────

    def get_state(self, decision_id: str) -> Optional[AggregationState]:
        with self._lock:
            return self._states.get(decision_id)

    def get_snapshot(self, decision_id: str) -> Optional[_AggregationStateSnapshot]:
        state = self.get_state(decision_id)
        return state.snapshot() if state is not None else None

    def active_decisions(self) -> List[str]:
        with self._lock:
            return list(self._states.keys())

    def remove(self, decision_id: str) -> None:
        with self._lock:
            self._states.pop(decision_id, None)

    @property
    def history(self) -> AggregationHistory:
        return self._history

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _submit(
        self,
        decision_id: str,
        subject_id:  str,
        subject_type: str,
        component:   ComponentId,
        value:       Any,
    ) -> None:
        with self._lock:
            if decision_id not in self._states:
                self._states[decision_id] = AggregationState(
                    decision_id, subject_id, subject_type,
                )
            state = self._states[decision_id]
        self._engine.apply_update(state, component, value)
        self._history.record(state.snapshot())

    def _get_or_create_by_snapshot_id(
        self, snapshot_id: str, subject_id: str, subject_type: str,
    ) -> AggregationState:
        with self._lock:
            # For ConfidenceSnapshot, we use snapshot_id as the decision key
            if snapshot_id not in self._states:
                self._states[snapshot_id] = AggregationState(
                    snapshot_id, subject_id, subject_type,
                )
            return self._states[snapshot_id]
