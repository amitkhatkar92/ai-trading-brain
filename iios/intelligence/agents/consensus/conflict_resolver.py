"""
iios/intelligence/agents/consensus/conflict_resolver.py
=======================================================
ConflictResolver — identifies and resolves conflicts between
agent decisions when they disagree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..agent_constants import ConsensusMethod
from ..core.base_agent import AgentDecision

__all__ = ["ConflictReport", "ConflictResolver"]


@dataclass
class ConflictReport:
    """Report of detected conflicts and chosen resolution."""
    has_conflict:    bool
    conflicting:     list[str]           # agent_ids in conflict
    decision_groups: dict[str, list[str]] # decision_key → [agent_ids]
    resolution:      Optional[Any]
    resolution_basis: str
    conflict_score:  float               # 0 = full agreement, 1 = max disagreement
    metadata:        dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "has_conflict":     self.has_conflict,
            "conflicting":      self.conflicting,
            "decision_groups":  self.decision_groups,
            "resolution":       self.resolution,
            "resolution_basis": self.resolution_basis,
            "conflict_score":   round(self.conflict_score, 4),
        }


class ConflictResolver:
    """
    Detects and resolves conflicts between agent decisions.

    Resolution strategies (applied in order):
      1. If all agree → no conflict
      2. If confidence gap > 2× → pick highest-confidence decision
      3. If weights differ significantly → pick highest-weighted group
      4. Fallback → pick the most popular decision
    """

    CONFIDENCE_DOMINATION_RATIO = 2.0   # top:second >= ratio → top wins

    def detect(self, decisions: list[AgentDecision]) -> ConflictReport:
        """Detect whether there is a conflict among decisions."""
        if not decisions:
            return ConflictReport(
                has_conflict=False, conflicting=[], decision_groups={},
                resolution=None, resolution_basis="no decisions",
                conflict_score=0.0,
            )

        # Group agent_ids by decision
        groups: dict[str, list[str]] = {}
        for d in decisions:
            key = self._key(d.decision)
            groups.setdefault(key, []).append(d.agent_id)

        if len(groups) == 1:
            return ConflictReport(
                has_conflict=False, conflicting=[], decision_groups=groups,
                resolution=decisions[0].decision, resolution_basis="unanimous",
                conflict_score=0.0,
            )

        # Conflict exists — compute conflict score
        n      = len(decisions)
        counts = [len(v) for v in groups.values()]
        # Normalised entropy-based conflict score
        from math import log2
        entropy = -sum((c / n) * log2(c / n) for c in counts if c > 0)
        max_entropy = log2(n) if n > 1 else 1
        conflict_score = entropy / max_entropy if max_entropy > 0 else 0.0

        conflicting = [a for agents in groups.values() for a in agents]

        return ConflictReport(
            has_conflict=True,
            conflicting=conflicting,
            decision_groups=groups,
            resolution=None,
            resolution_basis="unresolved",
            conflict_score=conflict_score,
        )

    def resolve(self, decisions: list[AgentDecision]) -> ConflictReport:
        """Detect and attempt to resolve a conflict."""
        report = self.detect(decisions)
        if not report.has_conflict:
            return report

        # Strategy 1: confidence domination
        by_conf = sorted(decisions, key=lambda d: d.confidence * d.weight, reverse=True)
        if len(by_conf) >= 2:
            top    = by_conf[0]
            second = by_conf[1]
            if second.confidence * second.weight > 0:
                ratio = (top.confidence * top.weight) / (second.confidence * second.weight)
                if ratio >= self.CONFIDENCE_DOMINATION_RATIO:
                    report.resolution       = top.decision
                    report.resolution_basis = (
                        f"confidence domination (ratio={ratio:.2f}) "
                        f"agent={top.agent_id!r}"
                    )
                    return report

        # Strategy 2: highest-weighted group
        groups = report.decision_groups
        total_weights: dict[str, float] = {}
        for d in decisions:
            key = self._key(d.decision)
            total_weights[key] = total_weights.get(key, 0.0) + d.weight

        best_key = max(total_weights, key=total_weights.__getitem__)
        winner   = next(d.decision for d in decisions if self._key(d.decision) == best_key)
        report.resolution       = winner
        report.resolution_basis = (
            f"highest total weight ({total_weights[best_key]:.2f}) "
            f"for decision {best_key!r}"
        )
        return report

    @staticmethod
    def _key(decision: Any) -> str:
        if isinstance(decision, str):
            return decision
        if isinstance(decision, (int, float, bool)):
            return str(decision)
        try:
            import json
            return json.dumps(decision, sort_keys=True, default=str)
        except Exception:
            return repr(decision)
