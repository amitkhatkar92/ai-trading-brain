"""iios/investment/decision/integration/conflict_detector.py
Detects conflicts between upstream engine outputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from iios.investment.decision.integration.aggregation_state import _AggregationStateSnapshot
from iios.investment.decision.integration.integration_constants import (
    CONFLICT_SEVERITY_SCORE_CRITICAL,
    CONFLICT_SEVERITY_SCORE_HIGH,
    CONFLICT_SEVERITY_SCORE_MEDIUM,
    ConflictSeverity,
    ConflictType,
)


@dataclass(frozen=True)
class DetectedConflict:
    conflict_id:    str
    conflict_type:  ConflictType
    severity:       ConflictSeverity
    component_a:    str
    component_b:    str
    description:    str
    detail:         Optional[str]
    metric_a:       Optional[float]
    metric_b:       Optional[float]
    detected_at:    datetime
    is_resolved:    bool = False
    resolution_note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id":    self.conflict_id,
            "conflict_type":  self.conflict_type.value,
            "severity":       self.severity.value,
            "component_a":    self.component_a,
            "component_b":    self.component_b,
            "description":    self.description,
            "detail":         self.detail,
            "metric_a":       self.metric_a,
            "metric_b":       self.metric_b,
            "is_resolved":    self.is_resolved,
            "resolution_note":self.resolution_note,
            "detected_at":    self.detected_at.isoformat(),
        }


def _severity_from_score(score: float) -> ConflictSeverity:
    if score >= CONFLICT_SEVERITY_SCORE_CRITICAL: return ConflictSeverity.CRITICAL
    if score >= CONFLICT_SEVERITY_SCORE_HIGH:     return ConflictSeverity.HIGH
    if score >= CONFLICT_SEVERITY_SCORE_MEDIUM:   return ConflictSeverity.MEDIUM
    return ConflictSeverity.LOW


def _conflict(
    conflict_type: ConflictType,
    severity:      ConflictSeverity,
    component_a:   str,
    component_b:   str,
    description:   str,
    detail:        Optional[str] = None,
    metric_a:      Optional[float] = None,
    metric_b:      Optional[float] = None,
) -> DetectedConflict:
    return DetectedConflict(
        conflict_id   = str(uuid.uuid4()),
        conflict_type = conflict_type,
        severity      = severity,
        component_a   = component_a,
        component_b   = component_b,
        description   = description,
        detail        = detail,
        metric_a      = metric_a,
        metric_b      = metric_b,
        detected_at   = datetime.now(timezone.utc),
    )


class ConflictDetector:
    """
    Stateless detector that examines an AggregationStateSnapshot and
    returns a list of DetectedConflict objects.
    """

    def detect(self, snap: _AggregationStateSnapshot) -> List[DetectedConflict]:
        conflicts: List[DetectedConflict] = []
        conflicts.extend(self._check_evidence_reasoning(snap))
        conflicts.extend(self._check_confidence_risk(snap))
        conflicts.extend(self._check_committee_risk(snap))
        conflicts.extend(self._check_committee_recommendation(snap))
        conflicts.extend(self._check_subject_mismatch(snap))
        conflicts.extend(self._check_staleness(snap))
        return conflicts

    # ── Evidence ↔ Reasoning ─────────────────────────────────────────────────

    def _check_evidence_reasoning(
        self, snap: _AggregationStateSnapshot,
    ) -> List[DetectedConflict]:
        if snap.evidence is None or snap.reasoning is None:
            return []
        result = []

        # Subject mismatch
        if snap.evidence.subject_id != snap.reasoning.subject_id:
            result.append(_conflict(
                ConflictType.EVIDENCE_REASONING, ConflictSeverity.CRITICAL,
                "evidence", "reasoning",
                "Subject ID mismatch between Evidence and Reasoning",
                detail=f"ev={snap.evidence.subject_id}, rs={snap.reasoning.subject_id}",
            ))

        # Evidence snapshot ID mismatch (reasoning was built on a different evidence)
        rs_ev_id = getattr(snap.reasoning, "evidence_snapshot_id", None)
        if rs_ev_id and rs_ev_id != snap.evidence.snapshot_id:
            result.append(_conflict(
                ConflictType.EVIDENCE_REASONING, ConflictSeverity.HIGH,
                "evidence", "reasoning",
                "Reasoning was built on a different EvidenceSnapshot",
                detail=f"reasoning.evidence_snapshot_id={rs_ev_id}, "
                       f"current evidence.snapshot_id={snap.evidence.snapshot_id}",
            ))
        return result

    # ── Confidence ↔ Risk ────────────────────────────────────────────────────

    def _check_confidence_risk(
        self, snap: _AggregationStateSnapshot,
    ) -> List[DetectedConflict]:
        if snap.confidence is None or snap.risk is None:
            return []
        result = []
        conf = snap.confidence.overall_confidence
        risk = snap.risk.overall_risk

        # Extreme high confidence with critical risk
        if conf >= 80.0 and risk >= 80.0:
            sev = ConflictSeverity.HIGH
            result.append(_conflict(
                ConflictType.CONFIDENCE_RISK, sev,
                "confidence", "risk",
                "Very high confidence simultaneously with very high risk",
                detail=f"confidence={conf:.1f}, risk={risk:.1f}",
                metric_a=conf, metric_b=risk,
            ))

        # Very low confidence with very low risk
        elif conf <= 25.0 and risk <= 15.0:
            result.append(_conflict(
                ConflictType.CONFIDENCE_RISK, ConflictSeverity.MEDIUM,
                "confidence", "risk",
                "Very low confidence but very low risk — unusual combination",
                detail=f"confidence={conf:.1f}, risk={risk:.1f}",
                metric_a=conf, metric_b=risk,
            ))
        return result

    # ── Committee ↔ Risk ─────────────────────────────────────────────────────

    def _check_committee_risk(
        self, snap: _AggregationStateSnapshot,
    ) -> List[DetectedConflict]:
        if snap.committee is None or snap.risk is None:
            return []
        from iios.investment.decision.committee.committee_constants import CommitteePosition
        pos = getattr(snap.committee, "position", None)
        if pos is None:
            return []
        result = []

        # Committee approved but risk blocks execution
        if pos == CommitteePosition.PROCEED_TO_RECOMMENDATION and snap.risk.blocks_execution:
            result.append(_conflict(
                ConflictType.COMMITTEE_RISK, ConflictSeverity.CRITICAL,
                "committee", "risk",
                "Committee approved PROCEED but Risk engine blocks execution",
                detail=f"committee.position={pos.value}, risk.blocks_execution=True",
            ))

        # Committee blocked but risk is non-critical
        if pos == CommitteePosition.BLOCKED and not snap.risk.blocks_execution:
            result.append(_conflict(
                ConflictType.COMMITTEE_RISK, ConflictSeverity.MEDIUM,
                "committee", "risk",
                "Committee BLOCKED but Risk engine does not block execution",
                detail=f"committee.position={pos.value}, risk.blocks_execution=False",
            ))
        return result

    # ── Committee ↔ Recommendation ───────────────────────────────────────────

    def _check_committee_recommendation(
        self, snap: _AggregationStateSnapshot,
    ) -> List[DetectedConflict]:
        if snap.committee is None or snap.recommendation is None:
            return []
        from iios.investment.decision.committee.committee_constants import CommitteePosition

        pos    = getattr(snap.committee, "position", None)
        action = getattr(snap.recommendation, "recommendation_type", None)
        if pos is None or action is None:
            return []

        result = []
        is_blocked  = pos == CommitteePosition.BLOCKED
        is_bullish  = getattr(action, "is_bullish", False)
        is_bearish  = getattr(action, "is_bearish", False)

        if is_blocked and is_bullish:
            result.append(_conflict(
                ConflictType.COMMITTEE_RECOMMENDATION, ConflictSeverity.CRITICAL,
                "committee", "recommendation",
                "Committee BLOCKED but Recommendation is bullish",
                detail=f"committee.position={pos.value}, "
                       f"recommendation={action.value if hasattr(action,'value') else action}",
            ))
        return result

    # ── Subject mismatch ─────────────────────────────────────────────────────

    def _check_subject_mismatch(
        self, snap: _AggregationStateSnapshot,
    ) -> List[DetectedConflict]:
        from iios.investment.decision.integration.integration_constants import ComponentId
        sids: Dict[str, str] = {}
        for cid in ComponentId:
            val = getattr(snap, cid.value, None)
            if val is None:
                continue
            sid = getattr(val, "subject_id", None)
            if sid:
                sids[cid.value] = sid

        unique = set(sids.values())
        if len(unique) <= 1:
            return []

        return [_conflict(
            ConflictType.SUBJECT_MISMATCH, ConflictSeverity.CRITICAL,
            "multiple", "multiple",
            f"Subject ID differs across components: {unique}",
            detail=str(sids),
        )]

    # ── Staleness ────────────────────────────────────────────────────────────

    def _check_staleness(
        self, snap: _AggregationStateSnapshot,
    ) -> List[DetectedConflict]:
        from iios.investment.decision.integration.integration_constants import (
            COMPONENT_MAX_AGE_SECONDS, ComponentId,
        )
        from datetime import timezone
        import datetime as _dt
        now   = _dt.datetime.now(timezone.utc)
        stale = []
        for cid in ComponentId:
            val = getattr(snap, cid.value, None)
            if val is None:
                continue
            ts = getattr(val, "created_at", None)
            if ts is None:
                continue
            age = (now - ts).total_seconds()
            if age > COMPONENT_MAX_AGE_SECONDS:
                stale.append(_conflict(
                    ConflictType.DATA_STALENESS, ConflictSeverity.MEDIUM,
                    cid.value, "integration",
                    f"Component '{cid.value}' is stale ({age:.0f}s old)",
                    detail=f"max_age={COMPONENT_MAX_AGE_SECONDS}s, actual={age:.0f}s",
                    metric_a=age,
                    metric_b=COMPONENT_MAX_AGE_SECONDS,
                ))
        return stale
