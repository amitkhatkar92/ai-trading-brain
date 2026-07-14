"""iios/investment/decision/explainability/decision_trace.py
DecisionTrace — full traceability graph from evidence → outcome.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class EvidenceTraceNode:
    """Contribution of one evidence item to the final assessment."""
    item_key:        str
    source_type:     str
    confidence:      float    # 0–100
    freshness_score: float    # 0–1
    impact_score:    float    # 0–100 estimated influence on evidence quality
    reasoning_referenced: bool  # was this item referenced in reasoning?


@dataclass(frozen=True)
class ReasoningTraceNode:
    """Contribution of one reasoning step to the final assessment."""
    step_index:        int
    conclusion:        str
    confidence:        float    # 0–100 step-level confidence
    evidence_refs:     Tuple[str, ...]  # evidence item keys this step used
    logic_valid:       bool


@dataclass(frozen=True)
class DecisionTrace:
    """
    Complete, immutable traceability graph.
    Links every evidence item → reasoning step → confidence → risk → outcome.
    """
    decision_id:            str
    subject_id:             str

    # ── Evidence layer ───────────────────────────────────────────────────────
    evidence_nodes:         Tuple[EvidenceTraceNode, ...]

    # ── Reasoning layer ──────────────────────────────────────────────────────
    reasoning_nodes:        Tuple[ReasoningTraceNode, ...]
    reasoning_conclusion:   str

    # ── Confidence layer ────────────────────────────────────────────────────
    evidence_confidence:    float    # from DecisionConfidence
    reasoning_confidence:   float
    overall_confidence:     float
    confidence_level:       str

    # ── Risk layer ───────────────────────────────────────────────────────────
    market_risk:            float
    company_risk:           float
    strategy_risk:          float
    execution_risk:         float
    confidence_risk_score:  float
    overall_risk:           float
    risk_level:             str

    # ── Outcome ──────────────────────────────────────────────────────────────
    outcome:                str

    @property
    def evidence_node_count(self) -> int:
        return len(self.evidence_nodes)

    @property
    def reasoning_node_count(self) -> int:
        return len(self.reasoning_nodes)

    @property
    def traced_evidence_fraction(self) -> float:
        if not self.evidence_nodes:
            return 0.0
        referenced = sum(1 for n in self.evidence_nodes if n.reasoning_referenced)
        return referenced / len(self.evidence_nodes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id":           self.decision_id,
            "subject_id":            self.subject_id,
            "evidence_node_count":   self.evidence_node_count,
            "reasoning_node_count":  self.reasoning_node_count,
            "traced_evidence_frac":  round(self.traced_evidence_fraction, 4),
            "reasoning_conclusion":  self.reasoning_conclusion,
            "evidence_confidence":   round(self.evidence_confidence, 2),
            "reasoning_confidence":  round(self.reasoning_confidence, 2),
            "overall_confidence":    round(self.overall_confidence, 2),
            "confidence_level":      self.confidence_level,
            "market_risk":           round(self.market_risk, 2),
            "company_risk":          round(self.company_risk, 2),
            "strategy_risk":         round(self.strategy_risk, 2),
            "execution_risk":        round(self.execution_risk, 2),
            "confidence_risk_score": round(self.confidence_risk_score, 2),
            "overall_risk":          round(self.overall_risk, 2),
            "risk_level":            self.risk_level,
            "outcome":               self.outcome,
            "evidence_nodes": [
                {"key": n.item_key, "source": n.source_type,
                 "confidence": round(n.confidence, 2), "impact": round(n.impact_score, 2),
                 "freshness": round(n.freshness_score, 4), "reasoning_ref": n.reasoning_referenced}
                for n in self.evidence_nodes
            ],
            "reasoning_nodes": [
                {"step": n.step_index, "conclusion": n.conclusion,
                 "confidence": round(n.confidence, 2), "logic_valid": n.logic_valid,
                 "evidence_refs": list(n.evidence_refs)}
                for n in self.reasoning_nodes
            ],
        }
