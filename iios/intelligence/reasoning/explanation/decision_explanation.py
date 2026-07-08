"""
iios/intelligence/reasoning/explanation/decision_explanation.py
===============================================================
DecisionExplanation — complete human + machine explanation for a conclusion.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..reasoning_constants import ConfidenceLevel, ExplanationType
from .reasoning_trace import ReasoningTrace
from .proof_chain import ProofChain

if TYPE_CHECKING:
    from ..debate.debate_summary import DebateSummary


@dataclass
class DecisionExplanation:
    """
    Complete explanation for a reasoned conclusion.

    Both human-readable (summary, detailed) and machine-readable (dict)
    representations are carried alongside trace and proof artefacts.
    """

    explanation_id:   str                  = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    session_id:       str                  = ""
    conclusion:       Any                  = None
    confidence:       float                = 0.0
    confidence_level: ConfidenceLevel      = ConfidenceLevel.VERY_LOW
    summary:          str                  = ""   # One-sentence
    detailed:         str                  = ""   # Full narrative
    trace:            ReasoningTrace | None = None
    proof_chain:      ProofChain     | None = None
    evidence_summary: list[dict[str, Any]] = field(default_factory=list)
    debate_summary:   Any | None           = None  # DebateSummary | None
    machine_readable: dict[str, Any]       = field(default_factory=dict)
    created_at:       float                = field(default_factory=time.time)

    # -- Text generation ───────────────────────────────────────────────────────

    def to_text(
        self, explanation_type: ExplanationType = ExplanationType.SUMMARY
    ) -> str:
        if explanation_type == ExplanationType.SUMMARY:
            return self.summary or f"Conclusion: {self.conclusion!r}"

        if explanation_type == ExplanationType.DETAILED:
            return self.detailed or self.summary

        if explanation_type == ExplanationType.TRACE:
            if self.trace:
                return self.trace.to_text()
            return "(No reasoning trace available)"

        if explanation_type == ExplanationType.PROOF_CHAIN:
            if self.proof_chain:
                return self.proof_chain.to_text()
            return "(No proof chain available)"

        if explanation_type == ExplanationType.HUMAN_READABLE:
            parts = [
                f"Conclusion : {self.conclusion!r}",
                f"Confidence : {self.confidence:.2%} ({self.confidence_level.value})",
                f"Summary    : {self.summary}",
            ]
            if self.detailed:
                parts.append(f"\nDetails:\n{self.detailed}")
            if self.evidence_summary:
                parts.append(f"\nKey Evidence ({len(self.evidence_summary)} items):")
                for ev in self.evidence_summary[:5]:
                    parts.append(
                        f"  - [{ev.get('evidence_type', '?')}] "
                        f"{ev.get('claim', '(no claim)')}"
                        f"  (strength={ev.get('strength', '?')}, "
                        f"confidence={ev.get('confidence', 0.0):.2f})"
                    )
            if self.debate_summary and hasattr(self.debate_summary, "to_dict"):
                ds = self.debate_summary
                parts.append(
                    f"\nDebate: {ds.total_arguments} arguments, "
                    f"{ds.supporting_count} supporting / {ds.opposing_count} opposing, "
                    f"consensus={ds.consensus_score:.2f}"
                )
            return "\n".join(parts)

        if explanation_type == ExplanationType.MACHINE_READABLE:
            import json
            return json.dumps(self.machine_readable, default=str, indent=2)

        return self.summary

    # -- Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "explanation_id":   self.explanation_id,
            "session_id":       self.session_id,
            "conclusion":       self.conclusion,
            "confidence":       round(self.confidence, 4),
            "confidence_level": self.confidence_level.value,
            "summary":          self.summary,
            "detailed":         self.detailed,
            "has_trace":        self.trace is not None,
            "has_proof_chain":  self.proof_chain is not None,
            "evidence_count":   len(self.evidence_summary),
            "has_debate":       self.debate_summary is not None,
            "machine_readable": self.machine_readable,
            "created_at":       self.created_at,
        }
