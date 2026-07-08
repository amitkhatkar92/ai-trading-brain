"""
iios/intelligence/reasoning/explanation/proof_chain.py
======================================================
ProofChain — logical chain from premises to final conclusion.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from ..reasoning_constants import MAX_PROOF_CHAIN_STEPS


@dataclass
class ProofStep:
    """One deductive step in the proof chain."""
    step_id:        str       = field(default_factory=lambda: str(uuid.uuid4()))
    premise:        str       = ""         # Starting assumption for this step
    inference_rule: str       = ""         # Named rule applied (e.g., "modus ponens")
    conclusion:     str       = ""         # Derived conclusion
    evidence_ids:   list[str] = field(default_factory=list)
    confidence:     float     = 1.0        # Confidence that the step is valid

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id":        self.step_id,
            "premise":        self.premise,
            "inference_rule": self.inference_rule,
            "conclusion":     self.conclusion,
            "evidence_ids":   self.evidence_ids,
            "confidence":     round(self.confidence, 4),
        }


class ProofChain:
    """
    An ordered sequence of ProofStep objects leading from initial premises
    to a final conclusion.

    Validity check: each step's conclusion must appear as the premise of
    the next step (or be the final conclusion).
    """

    def __init__(
        self,
        session_id:        str,
        initial_premises:  list[str] | None = None,
    ) -> None:
        self.chain_id:         str            = str(uuid.uuid4())
        self.session_id:       str            = session_id
        self.initial_premises: list[str]      = initial_premises or []
        self._steps:           list[ProofStep] = []

    # -- Building ──────────────────────────────────────────────────────────────

    def add_step(
        self,
        premise:        str,
        inference_rule: str,
        conclusion:     str,
        evidence_ids:   list[str] | None = None,
        confidence:     float            = 1.0,
    ) -> ProofStep:
        if len(self._steps) >= MAX_PROOF_CHAIN_STEPS:
            raise OverflowError(
                f"Proof chain for session {self.session_id!r} "
                f"exceeds MAX_PROOF_CHAIN_STEPS ({MAX_PROOF_CHAIN_STEPS})"
            )
        step = ProofStep(
            premise        = premise,
            inference_rule = inference_rule,
            conclusion     = conclusion,
            evidence_ids   = evidence_ids or [],
            confidence     = confidence,
        )
        self._steps.append(step)
        return step

    # -- Validation ────────────────────────────────────────────────────────────

    def is_valid(self) -> bool:
        """
        A chain is valid if it is non-empty and each step's conclusion
        is connected to the next step's premise (case-insensitive substring match).
        """
        if not self._steps:
            return False
        for i in range(len(self._steps) - 1):
            curr_conc  = self._steps[i].conclusion.lower()
            next_prem  = self._steps[i + 1].premise.lower()
            if curr_conc not in next_prem and next_prem not in curr_conc:
                return False
        return True

    # -- Query ─────────────────────────────────────────────────────────────────

    def final_conclusion(self) -> str:
        if not self._steps:
            return ""
        return self._steps[-1].conclusion

    def cumulative_confidence(self) -> float:
        """
        Product of all step confidences (min-propagation of uncertainty).
        Returns 0.0 for an empty chain.
        """
        if not self._steps:
            return 0.0
        result = 1.0
        for s in self._steps:
            result *= max(0.0, min(1.0, s.confidence))
        return result

    @property
    def length(self) -> int:
        return len(self._steps)

    # -- Rendering ─────────────────────────────────────────────────────────────

    def to_text(self) -> str:
        lines = [
            f"Proof Chain  [chain={self.chain_id}  session={self.session_id}]",
            f"Premises: {self.initial_premises}",
        ]
        for i, s in enumerate(self._steps, 1):
            lines.append(
                f"  {i:3d}. {s.premise!r}  "
                f"--[{s.inference_rule}]-->  {s.conclusion!r}"
                f"  (conf={s.confidence:.2f})"
            )
        lines.append(f"Final: {self.final_conclusion()!r}")
        return "\n".join(lines)

    # -- Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id":              self.chain_id,
            "session_id":            self.session_id,
            "initial_premises":      self.initial_premises,
            "final_conclusion":      self.final_conclusion(),
            "length":                self.length,
            "is_valid":              self.is_valid(),
            "cumulative_confidence": round(self.cumulative_confidence(), 4),
            "steps":                 [s.to_dict() for s in self._steps],
        }
