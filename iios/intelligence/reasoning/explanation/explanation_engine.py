"""
iios/intelligence/reasoning/explanation/explanation_engine.py
=============================================================
ExplanationEngine — creates, stores, and renders explanations.
"""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from ..reasoning_constants import ConfidenceLevel, ExplanationType, TraceStepType
from ..reasoning_exceptions import ExplanationNotFoundError, TraceNotFoundError
from .reasoning_trace import ReasoningTrace, TraceStep
from .proof_chain import ProofChain
from .decision_explanation import DecisionExplanation

if TYPE_CHECKING:
    from ..reasoning_result import ReasoningResult
    from ..debate.debate_summary import DebateSummary
    from ..evidence.evidence_registry import Evidence
    from ..confidence.confidence_model import ConfidenceModel


class ExplanationEngine:
    """
    Central service for generating and retrieving explanations.

    Responsibilities
    ----------------
    - Maintain one ReasoningTrace per session.
    - Maintain one ProofChain per chain_id.
    - Build DecisionExplanation from session artefacts.
    - Render explanations in multiple formats.
    """

    def __init__(self) -> None:
        self._traces:       dict[str, ReasoningTrace]      = {}   # session_id → trace
        self._proofs:       dict[str, ProofChain]           = {}   # chain_id   → proof
        self._explanations: dict[str, DecisionExplanation] = {}   # explanation_id
        self._by_session:   dict[str, str]                  = {}   # session_id → explanation_id
        self._lock:         threading.RLock                 = threading.RLock()

    # -- Trace management ──────────────────────────────────────────────────────

    def create_trace(self, session_id: str) -> ReasoningTrace:
        trace = ReasoningTrace(session_id=session_id)
        with self._lock:
            self._traces[session_id] = trace
        return trace

    def get_trace(self, session_id: str) -> ReasoningTrace:
        with self._lock:
            trace = self._traces.get(session_id)
        if trace is None:
            raise TraceNotFoundError(session_id)
        return trace

    def get_or_create_trace(self, session_id: str) -> ReasoningTrace:
        with self._lock:
            if session_id not in self._traces:
                self._traces[session_id] = ReasoningTrace(session_id=session_id)
            return self._traces[session_id]

    def record_trace_step(
        self,
        session_id:  str,
        step_type:   TraceStepType,
        description: str              = "",
        inputs:      dict[str, Any]   | None = None,
        outputs:     dict[str, Any]   | None = None,
        evidence_ids: list[str]       | None = None,
        duration_ms: float            = 0.0,
    ) -> TraceStep:
        trace = self.get_or_create_trace(session_id)
        return trace.add_step(
            step_type    = step_type,
            description  = description,
            inputs       = inputs,
            outputs      = outputs,
            evidence_ids = evidence_ids,
            duration_ms  = duration_ms,
        )

    # -- Proof chain management ────────────────────────────────────────────────

    def create_proof_chain(
        self,
        session_id:       str,
        initial_premises: list[str] | None = None,
    ) -> ProofChain:
        chain = ProofChain(
            session_id=session_id, initial_premises=initial_premises
        )
        with self._lock:
            self._proofs[chain.chain_id] = chain
        return chain

    def get_proof_chain(self, chain_id: str) -> ProofChain | None:
        with self._lock:
            return self._proofs.get(chain_id)

    # -- Explanation creation ──────────────────────────────────────────────────

    def create_explanation(
        self,
        *,
        session_id:      str,
        conclusion:      Any,
        confidence:      float,
        evidence_items:  list[Evidence]  | None = None,
        debate_summary:  DebateSummary   | None = None,
        confidence_model: ConfidenceModel | None = None,
        proof_chain:     ProofChain      | None = None,
    ) -> DecisionExplanation:
        """
        Build a DecisionExplanation from all available artefacts.
        """
        from ..reasoning_constants import (
            CONFIDENCE_THRESHOLD_VERY_HIGH,
            CONFIDENCE_THRESHOLD_HIGH,
            CONFIDENCE_THRESHOLD_MODERATE,
        )
        from ..confidence.confidence_model import ConfidenceModel as _CM

        level = _CM.score_to_level(confidence) if confidence_model is None else \
            _CM.score_to_level(confidence_model.final_score)

        # Build evidence summary
        ev_summary: list[dict[str, Any]] = []
        for ev in (evidence_items or []):
            ev_summary.append({
                "evidence_id":   ev.evidence_id,
                "evidence_type": ev.evidence_type.value,
                "claim":         ev.claim,
                "strength":      ev.strength.name,
                "confidence":    round(ev.confidence, 4),
                "source":        ev.source,
            })

        # Short human summary
        summary_parts = [f"Conclusion: {conclusion!r}"]
        summary_parts.append(f"Confidence: {confidence:.1%} ({level.value})")
        if debate_summary and debate_summary.consensus_reached:
            summary_parts.append(
                f"Consensus reached in {debate_summary.total_rounds} round(s)"
            )
        summary = " | ".join(summary_parts)

        # Detailed narrative
        lines = [summary]
        n_ev = len(ev_summary)
        lines.append(f"Evidence basis: {n_ev} item(s)")
        if debate_summary:
            lines.append(
                f"Debate: {debate_summary.total_arguments} argument(s), "
                f"consensus={debate_summary.consensus_score:.2f}"
            )
            if debate_summary.minority_opinions:
                lines.append(
                    f"Minority opinions preserved: "
                    f"{len(debate_summary.minority_opinions)}"
                )
        detailed = "\n".join(lines)

        # Machine-readable payload
        machine: dict[str, Any] = {
            "session_id":    session_id,
            "conclusion":    conclusion,
            "confidence":    round(confidence, 4),
            "level":         level.value,
            "evidence_ids":  [e["evidence_id"] for e in ev_summary],
            "debate_id":     debate_summary.debate_id if debate_summary else None,
            "proof_chain_id": proof_chain.chain_id if proof_chain else None,
        }
        if confidence_model:
            machine["confidence_model"] = confidence_model.to_dict()

        # Retrieve cached trace
        with self._lock:
            trace = self._traces.get(session_id)

        exp = DecisionExplanation(
            session_id       = session_id,
            conclusion       = conclusion,
            confidence       = confidence,
            confidence_level = level,
            summary          = summary,
            detailed         = detailed,
            trace            = trace,
            proof_chain      = proof_chain,
            evidence_summary = ev_summary,
            debate_summary   = debate_summary,
            machine_readable = machine,
        )
        with self._lock:
            self._explanations[exp.explanation_id] = exp
            self._by_session[session_id]           = exp.explanation_id
        return exp

    # -- Retrieval ─────────────────────────────────────────────────────────────

    def get_explanation(self, explanation_id: str) -> DecisionExplanation:
        with self._lock:
            exp = self._explanations.get(explanation_id)
        if exp is None:
            raise ExplanationNotFoundError(explanation_id)
        return exp

    def get_by_session(self, session_id: str) -> DecisionExplanation | None:
        with self._lock:
            eid = self._by_session.get(session_id)
            return self._explanations.get(eid) if eid else None

    def generate_text(
        self,
        explanation_id: str,
        explanation_type: ExplanationType = ExplanationType.SUMMARY,
    ) -> str:
        return self.get_explanation(explanation_id).to_text(explanation_type)

    # -- Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "explanations": len(self._explanations),
                "traces":       len(self._traces),
                "proof_chains": len(self._proofs),
            }


# ── Singleton ──────────────────────────────────────────────────────────────────

_LOCK   = threading.Lock()
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
