"""
iios/ontology/reasoning/explanation/decision_trace.py
======================================================
Evidence chain for a single inferred fact.

A DecisionTrace captures the lineage of one fact:
  - which rules produced it
  - which supporting evidence URIs contributed
  - the confidence at each hop
  - the depth (number of inference steps from ground truth)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..reasoning_result import InferredFact

__all__ = ["DecisionTrace"]


@dataclass
class DecisionTrace:
    """Human-inspectable lineage for a single InferredFact."""
    fact:               InferredFact
    supporting_rules:   list[str]       = field(default_factory=list)
    evidence_uris:      list[str]       = field(default_factory=list)
    confidence_path:    list[float]     = field(default_factory=list)
    depth:              int             = 0
    notes:              list[str]       = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "fact":              self.fact.to_dict(),
            "supporting_rules":  self.supporting_rules,
            "evidence_uris":     self.evidence_uris,
            "confidence_path":   [round(c, 4) for c in self.confidence_path],
            "depth":             self.depth,
            "notes":             self.notes,
        }

    def human_readable(self) -> str:
        lines = [
            f"Fact:       {self.fact.subject_uri} --[{self.fact.predicate}]--> {self.fact.object_value}",
            f"Confidence: {self.fact.confidence:.2f}",
            f"Depth:      {self.depth}",
        ]
        if self.supporting_rules:
            lines.append(f"Rules:      {', '.join(self.supporting_rules)}")
        if self.evidence_uris:
            lines.append(f"Evidence:   {', '.join(self.evidence_uris)}")
        if self.confidence_path:
            path_str = " → ".join(f"{c:.2f}" for c in self.confidence_path)
            lines.append(f"Conf path:  {path_str}")
        if self.notes:
            for note in self.notes:
                lines.append(f"Note:       {note}")
        return "\n".join(lines)
