"""
iios/ontology/reasoning/explanation/proof_generator.py
======================================================
Builds a rule-derivation tree (proof tree) for an inferred fact.

A ProofNode is a tree where:
  - the root holds the target fact
  - each child node holds a premise fact that was used to derive the parent
  - leaves are ground-truth facts (inferred=False)

ProofGenerator uses the ReasoningTrace to reconstruct the derivation.

Singleton: get_proof_generator() / reset_proof_generator()
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Optional

from ..reasoning_result import InferredFact
from ..reasoning_trace  import ReasoningTrace

__all__ = [
    "ProofNode",
    "ProofGenerator",
    "get_proof_generator",
    "reset_proof_generator",
]


@dataclass
class ProofNode:
    """One node in a proof tree."""
    fact:      InferredFact
    rule_id:   str                     = ""
    premises:  list["ProofNode"]       = field(default_factory=list)
    depth:     int                     = 0

    def is_leaf(self) -> bool:
        return len(self.premises) == 0

    def to_dict(self) -> dict:
        return {
            "fact":      self.fact.to_dict(),
            "rule_id":   self.rule_id,
            "depth":     self.depth,
            "premises":  [p.to_dict() for p in self.premises],
        }


class ProofGenerator:
    """Builds proof trees from a fact + trace pair."""

    def generate(
        self,
        fact:  InferredFact,
        trace: ReasoningTrace,
    ) -> ProofNode:
        """
        Build a proof tree rooted at *fact*.

        The trace is used to find which rules produced this fact and
        what inputs those rules consumed.
        """
        return self._build(fact, trace, depth=0, visited=set())

    def _build(
        self,
        fact:    InferredFact,
        trace:   ReasoningTrace,
        depth:   int,
        visited: set[str],
    ) -> ProofNode:
        key = f"{fact.subject_uri}|{fact.predicate}|{fact.object_value}"
        node = ProofNode(fact=fact, rule_id=fact.rule_ids[0] if fact.rule_ids else "", depth=depth)

        # Avoid infinite recursion for cyclic proofs
        if key in visited or not fact.inferred:
            return node

        visited = visited | {key}

        # Find trace entries that produced this fact
        for entry in trace.entries:
            for of in entry.output_facts:
                # output_facts are stored as dicts in TraceEntry
                s  = of.get("subject_uri",  "")
                p  = of.get("predicate",    "")
                o  = str(of.get("object_value", ""))
                if s == fact.subject_uri and p == fact.predicate and o == str(fact.object_value):
                    # For each premise (input_fact) in this step, recurse
                    for inf in entry.input_facts:
                        premise_fact = InferredFact(
                            subject_uri  = inf.get("subject_uri",  ""),
                            predicate    = inf.get("predicate",    ""),
                            object_value = inf.get("object_value", ""),
                            confidence   = float(inf.get("confidence", 1.0)),
                            rule_ids     = [entry.rule_id],
                            inferred     = bool(inf.get("inferred", True)),
                        )
                        child = self._build(premise_fact, trace, depth + 1, visited)
                        node.premises.append(child)
                    break  # Only use the first matching trace entry
        return node

    def to_human_readable(self, proof: ProofNode, indent: int = 0) -> str:
        prefix  = "  " * indent
        f       = proof.fact
        rule    = f"via [{proof.rule_id}]" if proof.rule_id else "(ground truth)"
        lines   = [
            f"{prefix}{f.subject_uri} --[{f.predicate}]--> {f.object_value}"
            f"  (conf={f.confidence:.2f})  {rule}"
        ]
        for child in proof.premises:
            lines.append(self.to_human_readable(child, indent + 1))
        return "\n".join(lines)

    def to_dict(self, proof: ProofNode) -> dict:
        return proof.to_dict()


# ── Singleton ─────────────────────────────────────────────────────────────────

_pg_lock = threading.Lock()
_pg_inst: Optional[ProofGenerator] = None


def get_proof_generator() -> ProofGenerator:
    global _pg_inst
    if _pg_inst is None:
        with _pg_lock:
            if _pg_inst is None:
                _pg_inst = ProofGenerator()
    return _pg_inst


def reset_proof_generator() -> None:
    global _pg_inst
    with _pg_lock:
        _pg_inst = None
