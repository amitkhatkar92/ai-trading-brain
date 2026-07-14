"""iios/investment/decision/reasoning/relationship_mapper.py
RelationshipMapper — maps cross-evidence relationships (corroborating, contradicting, complementary).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.decision.reasoning.evidence_interpreter import InterpretedSignal
from iios.investment.decision.reasoning.reasoning_constants import (
    RelationshipType,
    ReasoningStepType,
    SignalDirection,
)
from iios.investment.decision.reasoning.reasoning_step import ReasoningStep, make_step


@dataclass(frozen=True)
class Relationship:
    signal_a_id:       str
    signal_b_id:       str
    trace_id_a:        str
    trace_id_b:        str
    key_a:             str
    key_b:             str
    relationship_type: RelationshipType
    strength:          float           # 0–1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_a_id":       self.signal_a_id,
            "signal_b_id":       self.signal_b_id,
            "trace_id_a":        self.trace_id_a,
            "trace_id_b":        self.trace_id_b,
            "key_a":             self.key_a,
            "key_b":             self.key_b,
            "relationship_type": self.relationship_type.value,
            "strength":          round(self.strength, 4),
        }


@dataclass(frozen=True)
class RelationshipMap:
    relationships:         Tuple[Relationship, ...]
    corroborating_count:   int
    contradicting_count:   int
    complementary_count:   int
    cross_domain_count:    int   # relationships across different source_types

    @property
    def conflict_fraction(self) -> float:
        total = len(self.relationships)
        return self.contradicting_count / total if total else 0.0

    def by_type(self, rtype: RelationshipType) -> List[Relationship]:
        return [r for r in self.relationships if r.relationship_type == rtype]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total":              len(self.relationships),
            "corroborating":      self.corroborating_count,
            "contradicting":      self.contradicting_count,
            "complementary":      self.complementary_count,
            "cross_domain":       self.cross_domain_count,
            "conflict_fraction":  round(self.conflict_fraction, 3),
        }


class RelationshipMapper:
    """
    Finds structural relationships between interpreted signals.
    Relationships are determined purely from signal direction and source type —
    no investment judgement is applied.
    """

    def map(
        self,
        signals: List[InterpretedSignal],
        order:   int = 3,
    ) -> Tuple[RelationshipMap, ReasoningStep]:
        relationships: List[Relationship] = []

        for i in range(len(signals)):
            for j in range(i + 1, len(signals)):
                a, b = signals[i], signals[j]
                rel = self._relate(a, b)
                if rel is not None:
                    relationships.append(rel)

        corr  = sum(1 for r in relationships if r.relationship_type == RelationshipType.CORROBORATING)
        cont  = sum(1 for r in relationships if r.relationship_type == RelationshipType.CONTRADICTING)
        comp  = sum(1 for r in relationships if r.relationship_type == RelationshipType.COMPLEMENTARY)
        cross = sum(1 for r in relationships if r.signal_a_id != r.signal_b_id and
                    # cross-domain: source types differ
                    any(s.signal_id == r.signal_a_id for s in signals if s.source_type !=
                        next((x.source_type for x in signals if x.signal_id == r.signal_b_id), None)))

        rmap = RelationshipMap(
            relationships=tuple(relationships),
            corroborating_count=corr,
            contradicting_count=cont,
            complementary_count=comp,
            cross_domain_count=cross,
        )

        step = make_step(
            step_type=ReasoningStepType.RELATIONSHIP_MAPPING,
            description=f"Mapped relationships among {len(signals)} signals: "
                        f"{corr} corroborating, {cont} contradicting, {comp} complementary.",
            intermediate_conclusion=(
                f"Relationship mapping complete. "
                f"Conflict fraction: {rmap.conflict_fraction:.0%}."
            ),
            evidence_trace_ids=tuple(s.trace_id for s in signals),
            confidence=70.0,
            order=order,
            module_name="RelationshipMapper",
        )
        return rmap, step

    def _relate(
        self,
        a: InterpretedSignal,
        b: InterpretedSignal,
    ) -> Optional[Relationship]:
        # same key from different sources → check direction
        if a.key == b.key:
            if a.direction == b.direction and a.direction != SignalDirection.NEUTRAL:
                rtype = RelationshipType.CORROBORATING
            elif (a.direction != b.direction and
                  a.direction != SignalDirection.NEUTRAL and
                  b.direction != SignalDirection.NEUTRAL):
                rtype = RelationshipType.CONTRADICTING
            else:
                return None
            strength = round((a.strength + b.strength) / 2, 4)
            return Relationship(
                signal_a_id=a.signal_id, signal_b_id=b.signal_id,
                trace_id_a=a.trace_id, trace_id_b=b.trace_id,
                key_a=a.key, key_b=b.key,
                relationship_type=rtype, strength=strength,
            )

        # different keys, same source type, same direction → complementary
        if (a.source_type == b.source_type and
                a.direction == b.direction and
                a.direction != SignalDirection.NEUTRAL):
            return Relationship(
                signal_a_id=a.signal_id, signal_b_id=b.signal_id,
                trace_id_a=a.trace_id, trace_id_b=b.trace_id,
                key_a=a.key, key_b=b.key,
                relationship_type=RelationshipType.COMPLEMENTARY,
                strength=round((a.strength + b.strength) / 2, 4),
            )

        return None
