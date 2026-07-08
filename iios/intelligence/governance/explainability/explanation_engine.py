"""
iios/intelligence/governance/explainability/explanation_engine.py
=================================================================
ExplanationEngine — generates and stores all explanation artefacts.
"""
from __future__ import annotations

import threading
from typing import Any

from .decision_trace import DecisionTraceRecord
from .evidence_trace import EvidenceItem, EvidenceTraceRecord
from .explanation_formatter import ExplanationFormatter
from .proof_chain import GovernanceProofChain
from .reasoning_trace import ReasoningTraceRecord
from ..quality_constants import ExplanationType, ApprovalStatus
from ..quality_exceptions import TraceNotFoundError
from ..quality_result import QualityRecord


class ExplanationEngine:
    """
    Builds, stores, and retrieves explanation artefacts for QualityRecords.
    """

    def __init__(self) -> None:
        self._reasoning:  dict[str, ReasoningTraceRecord]  = {}
        self._decisions:  dict[str, DecisionTraceRecord]   = {}
        self._evidence:   dict[str, EvidenceTraceRecord]   = {}
        self._proofs:     dict[str, GovernanceProofChain]  = {}
        self._formatter:  ExplanationFormatter             = ExplanationFormatter()
        self._lock:       threading.RLock                  = threading.RLock()

    # -- Generate ──────────────────────────────────────────────────────────────

    def explain(self, record: QualityRecord) -> dict[str, Any]:
        """
        Auto-generate all trace artefacts for a QualityRecord and
        return a machine-readable explanation dict.
        """
        reasoning = self._build_reasoning(record)
        decision  = self._build_decision(record)
        evidence  = self._build_evidence(record)
        proof     = self._build_proof(record)

        with self._lock:
            self._reasoning[record.record_id] = reasoning
            self._decisions[record.record_id] = decision
            self._evidence[record.record_id]  = evidence
            self._proofs[record.record_id]    = proof

        return self._formatter.to_machine_readable(
            record, reasoning, decision, evidence, proof
        )

    def explain_text(self, record: QualityRecord) -> str:
        """Human-readable explanation of a QualityRecord."""
        with self._lock:
            reasoning = self._reasoning.get(record.record_id)
            decision  = self._decisions.get(record.record_id)
            evidence  = self._evidence.get(record.record_id)
            proof     = self._proofs.get(record.record_id)
        return self._formatter.to_human_readable(
            record, reasoning, decision, evidence, proof
        )

    def summary(self, record: QualityRecord) -> str:
        return self._formatter.to_summary(record)

    # -- Retrieve ──────────────────────────────────────────────────────────────

    def get_reasoning(self, record_id: str) -> ReasoningTraceRecord:
        with self._lock:
            t = self._reasoning.get(record_id)
        if t is None:
            raise TraceNotFoundError(f"reasoning:{record_id}")
        return t

    def get_decision(self, record_id: str) -> DecisionTraceRecord:
        with self._lock:
            t = self._decisions.get(record_id)
        if t is None:
            raise TraceNotFoundError(f"decision:{record_id}")
        return t

    def get_evidence(self, record_id: str) -> EvidenceTraceRecord:
        with self._lock:
            t = self._evidence.get(record_id)
        if t is None:
            raise TraceNotFoundError(f"evidence:{record_id}")
        return t

    def get_proof(self, record_id: str) -> GovernanceProofChain:
        with self._lock:
            t = self._proofs.get(record_id)
        if t is None:
            raise TraceNotFoundError(f"proof:{record_id}")
        return t

    # -- Private builders ──────────────────────────────────────────────────────

    @staticmethod
    def _build_reasoning(record: QualityRecord) -> ReasoningTraceRecord:
        trace = ReasoningTraceRecord(
            record_id  = record.record_id,
            product_id = record.product_id,
        )
        trace.add_step(
            "Dimension scoring",
            input_     = {"product_type": record.product_type.value},
            output     = record.dimension_scores,
            confidence = record.quality_score,
        )
        trace.add_step(
            "Composite aggregation",
            input_     = {"dimension_scores": record.dimension_scores},
            output     = {"quality_score": record.quality_score},
            confidence = record.quality_score,
        )
        trace.add_step(
            "Threshold comparison",
            input_     = {"quality_score": record.quality_score,
                          "threshold":     0.60},
            output     = {"decision": record.approval_status.value},
            confidence = abs(record.quality_score - 0.60) + 0.5,
        )
        trace.summary = (
            f"Product scored {record.quality_score:.3f} via "
            f"{len(record.dimension_scores)} dimensions"
        )
        return trace

    @staticmethod
    def _build_decision(record: QualityRecord) -> DecisionTraceRecord:
        trace = DecisionTraceRecord(
            record_id     = record.record_id,
            product_id    = record.product_id,
            decision      = record.approval_status,
            quality_score = record.quality_score,
            quality_level = record.quality_level,
        )
        trace.add_factor(
            "quality_score",
            record.quality_score,
            weight       = 1.0,
            contribution = record.quality_score - 0.60,
        )
        if record.warnings:
            trace.add_factor(
                "warnings",
                len(record.warnings),
                weight       = 0.3,
                contribution = -0.05 * len(record.warnings),
            )
        trace.rationale = (
            f"Quality score {record.quality_score:.3f} "
            + ("meets" if record.is_approved else "fails")
            + " the minimum threshold of 0.60."
        )
        trace.rules_applied = ["MINIMUM_QUALITY_THRESHOLD"]
        return trace

    @staticmethod
    def _build_evidence(record: QualityRecord) -> EvidenceTraceRecord:
        trace = EvidenceTraceRecord(
            record_id  = record.record_id,
            product_id = record.product_id,
        )
        for dim_name, score in record.dimension_scores.items():
            direction = "supporting" if score >= 0.6 else "opposing"
            trace.add_item(EvidenceItem(
                evidence_id   = f"dim:{dim_name}",
                evidence_type = "dimension_score",
                source        = "quality_evaluator",
                strength      = score,
                direction     = direction,
                description   = f"{dim_name} score={score:.3f}",
            ))
        trace.summary = (
            f"{trace.supporting_count} supporting, "
            f"{trace.opposing_count} opposing dimensions"
        )
        return trace

    @staticmethod
    def _build_proof(record: QualityRecord) -> GovernanceProofChain:
        chain = GovernanceProofChain(
            record_id  = record.record_id,
            product_id = record.product_id,
        )
        chain.add_step(
            premise    = f"quality_score = {record.quality_score:.3f}",
            conclusion = f"level = {record.quality_level.value}",
            rule       = "LEVEL_ASSIGNMENT",
            confidence = 1.0,
        )
        passed = record.quality_score >= 0.60
        chain.add_step(
            premise    = f"{record.quality_score:.3f} {'≥' if passed else '<'} 0.60",
            conclusion = record.approval_status.value,
            rule       = "MINIMUM_QUALITY_THRESHOLD",
            confidence = 1.0,
            valid      = True,
        )
        chain.conclusion = record.approval_status.value
        return chain

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "reasoning_traces": len(self._reasoning),
                "decision_traces":  len(self._decisions),
                "evidence_traces":  len(self._evidence),
                "proof_chains":     len(self._proofs),
            }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK:   threading.Lock            = threading.Lock()
_ENGINE: ExplanationEngine | None = None


def get_explanation_engine() -> ExplanationEngine:
    global _ENGINE
    if _ENGINE is None:
        with _LOCK:
            if _ENGINE is None:
                _ENGINE = ExplanationEngine()
    return _ENGINE


def reset_explanation_engine() -> None:
    global _ENGINE
    with _LOCK:
        _ENGINE = None
