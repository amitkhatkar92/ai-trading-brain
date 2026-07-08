"""
iios/ontology/reasoning/explanation/explanation_engine.py
=========================================================
Master explanation orchestrator.

Coordinates ProofGenerator, ReasoningExplainer, and DecisionTrace
into a single entry point for all explanation needs.

Singleton: get_explanation_engine() / reset_explanation_engine()
"""

from __future__ import annotations

import threading
from typing import Optional, Union

from ..reasoning_constants   import ExplanationType
from ..reasoning_result      import InferredFact, ReasoningResult
from ..reasoning_trace       import ReasoningTrace
from .decision_trace         import DecisionTrace
from .proof_generator        import ProofNode, ProofGenerator, get_proof_generator
from .reasoning_explainer    import ReasoningExplainer, get_reasoning_explainer

__all__ = [
    "ExplanationEngine",
    "get_explanation_engine",
    "reset_explanation_engine",
]


class ExplanationEngine:
    """
    Entry point for all explanation operations.

    Methods
    -------
    explain(result, trace, explanation_type)
        Returns str (human) or dict (machine) depending on explanation_type.

    explain_fact(fact, trace) -> DecisionTrace
        Build a DecisionTrace for a single InferredFact.

    generate_proof(fact, trace) -> ProofNode
        Build a full proof tree for a single InferredFact.
    """

    def __init__(
        self,
        generator: Optional[ProofGenerator]    = None,
        explainer: Optional[ReasoningExplainer] = None,
    ) -> None:
        self._generator = generator or get_proof_generator()
        self._explainer = explainer or get_reasoning_explainer()

    # ── Public API ────────────────────────────────────────────────────────────

    def explain(
        self,
        result:           ReasoningResult,
        trace:            ReasoningTrace,
        explanation_type: ExplanationType = ExplanationType.HUMAN_READABLE,
    ) -> Union[str, dict]:
        if explanation_type == ExplanationType.MACHINE_READABLE:
            return self._explainer.explain_machine(result, trace)
        return self._explainer.explain_result(result, trace)

    def explain_fact(
        self,
        fact:  InferredFact,
        trace: ReasoningTrace,
    ) -> DecisionTrace:
        """Construct a DecisionTrace (evidence chain) for *fact*."""
        supporting_rules:  list[str]   = list(fact.rule_ids)
        evidence_uris:     list[str]   = [fact.subject_uri]
        confidence_path:   list[float] = [fact.confidence]

        # Enrich from trace entries that produced this fact
        for entry in trace.entries:
            for of in entry.output_facts:
                if (
                    of.get("subject_uri") == fact.subject_uri
                    and of.get("predicate") == fact.predicate
                ):
                    for rid in (entry.rule_id,):
                        if rid and rid not in supporting_rules:
                            supporting_rules.append(rid)
                    for inf in entry.input_facts:
                        sub = inf.get("subject_uri", "")
                        if sub and sub not in evidence_uris:
                            evidence_uris.append(sub)
                            confidence_path.append(float(inf.get("confidence", 1.0)))
                    break

        return DecisionTrace(
            fact             = fact,
            supporting_rules = supporting_rules,
            evidence_uris    = evidence_uris,
            confidence_path  = confidence_path,
            depth            = len(confidence_path) - 1,
        )

    def generate_proof(
        self,
        fact:  InferredFact,
        trace: ReasoningTrace,
    ) -> ProofNode:
        return self._generator.generate(fact, trace)

    def explain_consistency(self, result: ReasoningResult) -> str:
        return self._explainer.explain_consistency(result.consistency_issues)


# ── Singleton ─────────────────────────────────────────────────────────────────

_ee_lock = threading.Lock()
_ee_inst: Optional[ExplanationEngine] = None


def get_explanation_engine() -> ExplanationEngine:
    global _ee_inst
    if _ee_inst is None:
        with _ee_lock:
            if _ee_inst is None:
                _ee_inst = ExplanationEngine()
    return _ee_inst


def reset_explanation_engine() -> None:
    global _ee_inst
    with _ee_lock:
        _ee_inst = None
