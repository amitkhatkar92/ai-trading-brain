"""iios/investment/decision/integration/consistency_rules.py
Declarative consistency rule definitions for cross-engine validation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from iios.investment.decision.integration.aggregation_state import _AggregationStateSnapshot
from iios.investment.decision.integration.integration_constants import (
    COMMITTEE_CONFIDENCE_MAX_DELTA,
    CONFIDENCE_RISK_MAX_DELTA,
    EVIDENCE_CONFIDENCE_MIN_FOR_VALID,
    ValidationStatus,
)
from iios.investment.decision.integration.validation_report import (
    ValidationCheck,
    _make_check,
)


@dataclass(frozen=True)
class ConsistencyRule:
    rule_id:     str
    name:        str
    description: str
    required_components: Tuple[str, ...]   # ComponentId values

    def check(self, snap: _AggregationStateSnapshot) -> Optional[ValidationCheck]:
        """Run the rule; return None if components are not present."""
        from iios.investment.decision.integration.integration_constants import ComponentId
        for cid_val in self.required_components:
            cid = ComponentId(cid_val)
            if getattr(snap, cid.value, None) is None:
                return None   # skip — can't validate without all components
        return self._evaluate(snap)

    def _evaluate(self, snap: _AggregationStateSnapshot) -> Optional[ValidationCheck]:
        raise NotImplementedError


# ─── Concrete rules ───────────────────────────────────────────────────────────

class EvidenceConfidenceRule(ConsistencyRule):
    """Evidence quality must meet minimum confidence threshold."""

    def _evaluate(self, snap: _AggregationStateSnapshot) -> Optional[ValidationCheck]:
        ev_conf = snap.evidence.overall_confidence
        if ev_conf >= EVIDENCE_CONFIDENCE_MIN_FOR_VALID:
            return _make_check(
                self.rule_id, self.name, ValidationStatus.VALID,
                f"Evidence confidence {ev_conf:.1f} meets minimum",
                component_a="evidence",
            )
        return _make_check(
            self.rule_id, self.name, ValidationStatus.WARNING,
            f"Evidence confidence {ev_conf:.1f} below minimum {EVIDENCE_CONFIDENCE_MIN_FOR_VALID}",
            detail=f"Confidence: {ev_conf:.1f}, minimum: {EVIDENCE_CONFIDENCE_MIN_FOR_VALID}",
            component_a="evidence",
        )


class EvidenceReasoningSubjectRule(ConsistencyRule):
    """Evidence and Reasoning must refer to the same subject."""

    def _evaluate(self, snap: _AggregationStateSnapshot) -> Optional[ValidationCheck]:
        ev_sid = snap.evidence.subject_id
        rs_sid = snap.reasoning.subject_id
        if ev_sid == rs_sid:
            return _make_check(
                self.rule_id, self.name, ValidationStatus.VALID,
                "Evidence and Reasoning refer to the same subject",
                component_a="evidence", component_b="reasoning",
            )
        return _make_check(
            self.rule_id, self.name, ValidationStatus.INVALID,
            f"Subject mismatch: evidence='{ev_sid}' vs reasoning='{rs_sid}'",
            detail=f"evidence.subject_id={ev_sid}, reasoning.subject_id={rs_sid}",
            component_a="evidence", component_b="reasoning",
        )


class ReasoningQualityRule(ConsistencyRule):
    """Reasoning must be complete and logically usable."""

    def _evaluate(self, snap: _AggregationStateSnapshot) -> Optional[ValidationCheck]:
        rs = snap.reasoning
        if rs.is_complete and rs.is_usable:
            return _make_check(
                self.rule_id, self.name, ValidationStatus.VALID,
                "Reasoning is complete and logically valid",
                component_a="reasoning",
            )
        if not rs.is_complete:
            return _make_check(
                self.rule_id, self.name, ValidationStatus.WARNING,
                "Reasoning is incomplete",
                detail=f"status={rs.status.value}",
                component_a="reasoning",
            )
        return _make_check(
            self.rule_id, self.name, ValidationStatus.INVALID,
            "Reasoning has logic validation failure",
            detail=f"logic_status={rs.logic_result.status.value}",
            component_a="reasoning",
        )


class ConfidenceRiskAlignmentRule(ConsistencyRule):
    """
    High confidence + high risk is a potential inconsistency.
    Flag when |confidence + risk| deviates from expected inverse relationship.
    """

    def _evaluate(self, snap: _AggregationStateSnapshot) -> Optional[ValidationCheck]:
        conf = snap.confidence.overall_confidence
        risk = snap.risk.overall_risk
        # Ideal: conf + risk ≈ 100 (they are rough inverses)
        delta = abs((conf + risk) - 100.0)
        if delta <= CONFIDENCE_RISK_MAX_DELTA:
            return _make_check(
                self.rule_id, self.name, ValidationStatus.VALID,
                f"Confidence ({conf:.1f}) and Risk ({risk:.1f}) are aligned (Δ={delta:.1f})",
                component_a="confidence", component_b="risk",
            )
        sev = ValidationStatus.WARNING if delta <= CONFIDENCE_RISK_MAX_DELTA * 1.5 else ValidationStatus.INVALID
        return _make_check(
            self.rule_id, self.name, sev,
            f"Confidence ({conf:.1f}) and Risk ({risk:.1f}) are misaligned (Δ={delta:.1f})",
            detail=f"Expected |conf + risk - 100| ≤ {CONFIDENCE_RISK_MAX_DELTA}, got {delta:.1f}",
            component_a="confidence", component_b="risk",
        )


class CommitteeConfidenceAlignmentRule(ConsistencyRule):
    """Committee confidence should be roughly aligned with overall engine confidence."""

    def _evaluate(self, snap: _AggregationStateSnapshot) -> Optional[ValidationCheck]:
        committee_conf = getattr(snap.committee, "committee_confidence", None)
        if committee_conf is None:
            return None
        overall_conf = snap.confidence.overall_confidence
        delta = abs(committee_conf - overall_conf)
        if delta <= COMMITTEE_CONFIDENCE_MAX_DELTA:
            return _make_check(
                self.rule_id, self.name, ValidationStatus.VALID,
                f"Committee confidence ({committee_conf:.1f}) aligns with overall ({overall_conf:.1f})",
                component_a="committee", component_b="confidence",
            )
        return _make_check(
            self.rule_id, self.name, ValidationStatus.WARNING,
            f"Committee confidence ({committee_conf:.1f}) diverges from overall ({overall_conf:.1f})",
            detail=f"Delta={delta:.1f}, threshold={COMMITTEE_CONFIDENCE_MAX_DELTA}",
            component_a="committee", component_b="confidence",
        )


class RiskPolicyRule(ConsistencyRule):
    """Risk policy must not be in VIOLATION state."""

    def _evaluate(self, snap: _AggregationStateSnapshot) -> Optional[ValidationCheck]:
        from iios.investment.decision.risk.risk_constants import RiskPolicyStatus
        ps = snap.risk.policy_status
        if ps == RiskPolicyStatus.VIOLATION:
            return _make_check(
                self.rule_id, self.name, ValidationStatus.INVALID,
                "Risk policy VIOLATION detected — decision cannot proceed",
                detail=f"policy_status={ps.value}",
                component_a="risk",
            )
        if ps == RiskPolicyStatus.WARNING:
            return _make_check(
                self.rule_id, self.name, ValidationStatus.WARNING,
                "Risk policy WARNING — review required",
                detail=f"policy_status={ps.value}",
                component_a="risk",
            )
        return _make_check(
            self.rule_id, self.name, ValidationStatus.VALID,
            "Risk policy is COMPLIANT",
            component_a="risk",
        )


class SubjectConsistencyRule(ConsistencyRule):
    """All present snapshots must refer to the same subject_id."""

    def _evaluate(self, snap: _AggregationStateSnapshot) -> Optional[ValidationCheck]:
        from iios.investment.decision.integration.integration_constants import ComponentId
        subjects = {}
        for cid in ComponentId:
            val = getattr(snap, cid.value, None)
            if val is None:
                continue
            sid = getattr(val, "subject_id", None)
            if sid:
                subjects[cid.value] = sid

        unique = set(subjects.values())
        if len(unique) <= 1:
            return _make_check(
                self.rule_id, self.name, ValidationStatus.VALID,
                "All components refer to the same subject",
            )
        return _make_check(
            self.rule_id, self.name, ValidationStatus.INVALID,
            f"Subject inconsistency across components: {subjects}",
            detail=str(subjects),
        )


class CommitteePositionRule(ConsistencyRule):
    """Committee position BLOCKED must be reflected in risk or compliance."""

    def _evaluate(self, snap: _AggregationStateSnapshot) -> Optional[ValidationCheck]:
        from iios.investment.decision.committee.committee_constants import CommitteePosition
        pos = getattr(snap.committee, "position", None)
        if pos is None:
            return None

        if pos == CommitteePosition.BLOCKED:
            if snap.risk.blocks_execution:
                return _make_check(
                    self.rule_id, self.name, ValidationStatus.VALID,
                    "Committee BLOCKED position is consistent with risk blocks_execution=True",
                    component_a="committee", component_b="risk",
                )
            return _make_check(
                self.rule_id, self.name, ValidationStatus.WARNING,
                "Committee BLOCKED but risk does not block execution — review required",
                detail="committee.position=BLOCKED, risk.blocks_execution=False",
                component_a="committee", component_b="risk",
            )
        return _make_check(
            self.rule_id, self.name, ValidationStatus.VALID,
            f"Committee position {pos.value} — no rule triggered",
            component_a="committee",
        )


# ─── Default rule set ─────────────────────────────────────────────────────────

DEFAULT_RULES: List[ConsistencyRule] = [
    EvidenceConfidenceRule(
        "R001", "EvidenceConfidence",
        "Evidence quality meets minimum confidence threshold",
        ("evidence",),
    ),
    EvidenceReasoningSubjectRule(
        "R002", "SubjectAlignment_EvidenceReasoning",
        "Evidence and Reasoning must share the same subject_id",
        ("evidence", "reasoning"),
    ),
    ReasoningQualityRule(
        "R003", "ReasoningQuality",
        "Reasoning is complete and logically valid",
        ("reasoning",),
    ),
    ConfidenceRiskAlignmentRule(
        "R004", "ConfidenceRiskAlignment",
        "Confidence and Risk form a consistent inverse relationship",
        ("confidence", "risk"),
    ),
    CommitteeConfidenceAlignmentRule(
        "R005", "CommitteeConfidenceAlignment",
        "Committee confidence aligns with overall engine confidence",
        ("committee", "confidence"),
    ),
    RiskPolicyRule(
        "R006", "RiskPolicy",
        "Risk policy must be COMPLIANT or WARNING — never VIOLATION",
        ("risk",),
    ),
    SubjectConsistencyRule(
        "R007", "CrossEngineSubjectConsistency",
        "All component snapshots must refer to the same subject",
        ("evidence",),   # always runs if evidence is present
    ),
    CommitteePositionRule(
        "R008", "CommitteePositionConsistency",
        "Committee BLOCKED position must be consistent with risk assessment",
        ("committee", "risk"),
    ),
]
