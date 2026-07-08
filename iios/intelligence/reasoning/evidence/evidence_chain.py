"""
iios/intelligence/reasoning/evidence/evidence_chain.py
======================================================
Linear chain of evidence building incrementally toward a conclusion.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from ..reasoning_constants import EvidenceRelation
from .evidence_registry import Evidence
from .evidence_graph import EvidenceGraph


@dataclass
class ChainLink:
    """One link in an evidence chain: evidence → strengthens → next claim."""
    link_id:     str   = field(default_factory=lambda: str(uuid.uuid4()))
    evidence_id: str   = ""
    claim:       str   = ""          # Claim this link establishes
    contribution: float = 1.0        # How much this link contributes [0,1]

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_id":      self.link_id,
            "evidence_id":  self.evidence_id,
            "claim":        self.claim,
            "contribution": round(self.contribution, 4),
        }


class EvidenceChain:
    """
    An ordered sequence of Evidence items that collectively support a conclusion.

    Also maintains an EvidenceGraph of the support relationships.
    """

    def __init__(self, session_id: str, initial_claim: str = "") -> None:
        self.chain_id:     str               = str(uuid.uuid4())
        self.session_id:   str               = session_id
        self.initial_claim: str              = initial_claim
        self._links:       list[ChainLink]   = []
        self._graph:       EvidenceGraph     = EvidenceGraph()

    # -- Building ──────────────────────────────────────────────────────────────

    def add_link(
        self,
        evidence: Evidence,
        claim:    str   = "",
        contribution: float = 1.0,
    ) -> ChainLink:
        link = ChainLink(
            evidence_id  = evidence.evidence_id,
            claim        = claim or evidence.claim,
            contribution = contribution,
        )
        self._links.append(link)

        # Wire into the graph
        self._graph.add_node(evidence.evidence_id, weight=contribution)
        if len(self._links) > 1:
            prev_eid = self._links[-2].evidence_id
            self._graph.add_edge(
                prev_eid,
                evidence.evidence_id,
                EvidenceRelation.SUPPORTS,
                weight=contribution,
            )
        return link

    # -- Query ─────────────────────────────────────────────────────────────────

    @property
    def length(self) -> int:
        return len(self._links)

    @property
    def evidence_ids(self) -> list[str]:
        return [lnk.evidence_id for lnk in self._links]

    def is_empty(self) -> bool:
        return not self._links

    def final_claim(self) -> str:
        if not self._links:
            return self.initial_claim
        return self._links[-1].claim

    def cumulative_confidence(self, evidence_items: list[Evidence]) -> float:
        """
        Geometric mean of evidence confidences weighted by chain contributions.
        Returns 0.0 if chain is empty.
        """
        if not self._links:
            return 0.0
        conf_map = {e.evidence_id: e.confidence for e in evidence_items}
        total_w  = 0.0
        score    = 0.0
        for lnk in self._links:
            conf = conf_map.get(lnk.evidence_id, 0.5)
            w    = lnk.contribution
            score   += conf * w
            total_w += w
        return score / total_w if total_w > 0 else 0.0

    # -- Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id":      self.chain_id,
            "session_id":    self.session_id,
            "initial_claim": self.initial_claim,
            "final_claim":   self.final_claim(),
            "length":        self.length,
            "links":         [lnk.to_dict() for lnk in self._links],
            "graph":         self._graph.to_dict(),
        }
