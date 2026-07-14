"""iios/investment/decision/integration/decision_summary.py
DecisionSummary — lightweight per-engine summaries for quick downstream access.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from iios.investment.decision.integration.aggregation_state import _AggregationStateSnapshot


@dataclass(frozen=True)
class EvidenceSummary:
    snapshot_id:       str
    item_count:        int
    quality_score:     float
    confidence:        float
    coverage_fraction: float
    required_met:      bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":       self.snapshot_id,
            "item_count":        self.item_count,
            "quality_score":     round(self.quality_score, 2),
            "confidence":        round(self.confidence, 2),
            "coverage_fraction": round(self.coverage_fraction, 3),
            "required_met":      self.required_met,
        }


@dataclass(frozen=True)
class ReasoningSummary:
    snapshot_id:    str
    is_complete:    bool
    is_usable:      bool
    hypothesis_count: int
    conclusion:     Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":      self.snapshot_id,
            "is_complete":      self.is_complete,
            "is_usable":        self.is_usable,
            "hypothesis_count": self.hypothesis_count,
            "conclusion":       self.conclusion,
        }


@dataclass(frozen=True)
class ConfidenceSummary:
    snapshot_id:       str
    overall_confidence: float
    confidence_level:  str
    uncertainty:       float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":        self.snapshot_id,
            "overall_confidence": round(self.overall_confidence, 2),
            "confidence_level":   self.confidence_level,
            "uncertainty":        round(self.uncertainty, 3),
        }


@dataclass(frozen=True)
class RiskSummary:
    snapshot_id:    str
    overall_risk:   float
    risk_level:     str
    policy_status:  str
    blocks_execution: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":     self.snapshot_id,
            "overall_risk":    round(self.overall_risk, 2),
            "risk_level":      self.risk_level,
            "policy_status":   self.policy_status,
            "blocks_execution": self.blocks_execution,
        }


@dataclass(frozen=True)
class ExplanationSummary:
    snapshot_id:          str
    explainability_score: float
    explainability_grade: str
    transparency_score:   float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":          self.snapshot_id,
            "explainability_score": round(self.explainability_score, 2),
            "explainability_grade": self.explainability_grade,
            "transparency_score":   round(self.transparency_score, 2),
        }


@dataclass(frozen=True)
class CommitteeSummary:
    report_id:            str
    position:             str
    committee_score:      float
    committee_grade:      str
    committee_confidence: float
    support_fraction:     float
    minority_count:       int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":            self.report_id,
            "position":             self.position,
            "committee_score":      round(self.committee_score, 2),
            "committee_grade":      self.committee_grade,
            "committee_confidence": round(self.committee_confidence, 2),
            "support_fraction":     round(self.support_fraction, 3),
            "minority_count":       self.minority_count,
        }


@dataclass(frozen=True)
class RecommendationSummary:
    snapshot_id:      str
    recommendation:   str
    conviction:       float
    confidence:       float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":    self.snapshot_id,
            "recommendation": self.recommendation,
            "conviction":     round(self.conviction, 2),
            "confidence":     round(self.confidence, 2),
        }


class DecisionSummaryBuilder:
    """Extracts lightweight summary objects from a full AggregationStateSnapshot."""

    def evidence(self, snap: _AggregationStateSnapshot) -> Optional[EvidenceSummary]:
        ev = snap.evidence
        if ev is None:
            return None
        return EvidenceSummary(
            snapshot_id       = ev.snapshot_id,
            item_count        = ev.item_count,
            quality_score     = ev.quality_score,
            confidence        = ev.overall_confidence,
            coverage_fraction = ev.coverage_fraction,
            required_met      = ev.required_items_met,
        )

    def reasoning(self, snap: _AggregationStateSnapshot) -> Optional[ReasoningSummary]:
        rs = snap.reasoning
        if rs is None:
            return None
        conclusion = getattr(rs.reasoning_chain, "final_conclusion", None)
        return ReasoningSummary(
            snapshot_id      = rs.snapshot_id,
            is_complete      = rs.is_complete,
            is_usable        = rs.is_usable,
            hypothesis_count = len(rs.hypotheses),
            conclusion       = conclusion,
        )

    def confidence(self, snap: _AggregationStateSnapshot) -> Optional[ConfidenceSummary]:
        cs = snap.confidence
        if cs is None:
            return None
        level = getattr(cs.confidence_level, "value", str(cs.confidence_level))
        unc   = getattr(getattr(cs, "decision_confidence", None), "uncertainty", 0.0)
        return ConfidenceSummary(
            snapshot_id        = cs.snapshot_id,
            overall_confidence = cs.overall_confidence,
            confidence_level   = level,
            uncertainty        = unc,
        )

    def risk(self, snap: _AggregationStateSnapshot) -> Optional[RiskSummary]:
        ri = snap.risk
        if ri is None:
            return None
        rl = getattr(ri.risk_level, "value", str(ri.risk_level))
        ps = getattr(ri.policy_status, "value", str(ri.policy_status))
        return RiskSummary(
            snapshot_id      = ri.snapshot_id,
            overall_risk     = ri.overall_risk,
            risk_level       = rl,
            policy_status    = ps,
            blocks_execution = ri.blocks_execution,
        )

    def explanation(self, snap: _AggregationStateSnapshot) -> Optional[ExplanationSummary]:
        ex = snap.explanation
        if ex is None:
            return None
        grade = getattr(ex.explainability_grade, "value", str(ex.explainability_grade))
        return ExplanationSummary(
            snapshot_id          = ex.snapshot_id,
            explainability_score = ex.explainability_score,
            explainability_grade = grade,
            transparency_score   = ex.transparency_score,
        )

    def committee(self, snap: _AggregationStateSnapshot) -> Optional[CommitteeSummary]:
        cm = snap.committee
        if cm is None:
            return None
        pos   = getattr(getattr(cm, "position", None), "value", str(getattr(cm, "position", "")))
        grade = getattr(getattr(cm, "committee_grade", None), "value",
                        str(getattr(cm, "committee_grade", "")))
        vs    = getattr(cm, "vote_summary", None)
        sf    = getattr(vs, "support_fraction", 0.0) if vs else 0.0
        return CommitteeSummary(
            report_id            = getattr(cm, "report_id",            ""),
            position             = pos,
            committee_score      = getattr(cm, "committee_score",      0.0),
            committee_grade      = grade,
            committee_confidence = getattr(cm, "committee_confidence", 0.0),
            support_fraction     = sf,
            minority_count       = getattr(cm, "minority_count",       0),
        )

    def recommendation(self, snap: _AggregationStateSnapshot) -> Optional[RecommendationSummary]:
        rec = snap.recommendation
        if rec is None:
            return None
        rt = getattr(rec, "recommendation_type", None)
        rec_str = getattr(rt, "value", str(rt)) if rt else "unknown"
        return RecommendationSummary(
            snapshot_id    = getattr(rec, "snapshot_id", ""),
            recommendation = rec_str,
            conviction     = getattr(rec, "conviction",  0.0),
            confidence     = getattr(rec, "confidence",  0.0),
        )
