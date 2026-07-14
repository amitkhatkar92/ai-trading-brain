"""iios/investment/strategy/debate/argument_manager.py
Argument and rebuttal data types, plus ArgumentManager store.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.strategy.debate.debate_constants import (
    ArgumentType,
    ParticipantRole,
    RebuttalType,
)


@dataclass(frozen=True)
class Argument:
    """An individual argument submitted by a debate participant."""
    argument_id:   str
    session_id:    str
    participant_id: str
    role:          ParticipantRole
    argument_type: ArgumentType
    claim:         str
    reasoning:     str
    evidence_ids:  tuple[str, ...]
    confidence:    float          # 0–100
    weight:        float          # participant weight at time of submission
    submitted_at:  datetime
    tags:          tuple[str, ...] = ()
    metadata:      Dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "argument_id":    self.argument_id,
            "session_id":     self.session_id,
            "participant_id": self.participant_id,
            "role":           self.role.value,
            "argument_type":  self.argument_type.value,
            "claim":          self.claim,
            "reasoning":      self.reasoning,
            "evidence_ids":   list(self.evidence_ids),
            "confidence":     round(self.confidence, 2),
            "weight":         round(self.weight, 4),
            "submitted_at":   self.submitted_at.isoformat(),
            "tags":           list(self.tags),
        }


@dataclass(frozen=True)
class Rebuttal:
    """A rebuttal targeting a specific argument."""
    rebuttal_id:    str
    session_id:     str
    participant_id: str
    role:           ParticipantRole
    target_arg_id:  str
    rebuttal_type:  RebuttalType
    claim:          str
    reasoning:      str
    evidence_ids:   tuple[str, ...]
    confidence:     float
    weight:         float
    submitted_at:   datetime
    metadata:       Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rebuttal_id":    self.rebuttal_id,
            "session_id":     self.session_id,
            "participant_id": self.participant_id,
            "role":           self.role.value,
            "target_arg_id":  self.target_arg_id,
            "rebuttal_type":  self.rebuttal_type.value,
            "claim":          self.claim,
            "reasoning":      self.reasoning,
            "evidence_ids":   list(self.evidence_ids),
            "confidence":     round(self.confidence, 2),
            "weight":         round(self.weight, 4),
            "submitted_at":   self.submitted_at.isoformat(),
        }


def make_argument(
    session_id:    str,
    participant_id: str,
    role:          ParticipantRole,
    argument_type: ArgumentType,
    claim:         str,
    reasoning:     str,
    confidence:    float,
    weight:        float = 1.0,
    evidence_ids:  Optional[List[str]] = None,
    tags:          Optional[List[str]] = None,
) -> Argument:
    return Argument(
        argument_id=str(uuid.uuid4()),
        session_id=session_id,
        participant_id=participant_id,
        role=role,
        argument_type=argument_type,
        claim=claim,
        reasoning=reasoning,
        evidence_ids=tuple(evidence_ids or []),
        confidence=min(max(confidence, 0.0), 100.0),
        weight=weight,
        submitted_at=datetime.now(timezone.utc),
        tags=tuple(tags or []),
    )


def make_rebuttal(
    session_id:    str,
    participant_id: str,
    role:          ParticipantRole,
    target_arg_id: str,
    rebuttal_type: RebuttalType,
    claim:         str,
    reasoning:     str,
    confidence:    float,
    weight:        float = 1.0,
    evidence_ids:  Optional[List[str]] = None,
) -> Rebuttal:
    return Rebuttal(
        rebuttal_id=str(uuid.uuid4()),
        session_id=session_id,
        participant_id=participant_id,
        role=role,
        target_arg_id=target_arg_id,
        rebuttal_type=rebuttal_type,
        claim=claim,
        reasoning=reasoning,
        evidence_ids=tuple(evidence_ids or []),
        confidence=min(max(confidence, 0.0), 100.0),
        weight=weight,
        submitted_at=datetime.now(timezone.utc),
    )


class ArgumentManager:
    """Thread-safe store for all arguments and rebuttals in a session."""

    def __init__(self, session_id: str) -> None:
        self._session_id  = session_id
        self._lock        = threading.RLock()
        self._arguments:  Dict[str, Argument]  = {}
        self._rebuttals:  Dict[str, Rebuttal]  = {}
        self._by_round:   Dict[int, List[str]] = {}  # round → argument_ids

    def add_argument(self, arg: Argument, round_num: int = 1) -> None:
        with self._lock:
            self._arguments[arg.argument_id] = arg
            self._by_round.setdefault(round_num, []).append(arg.argument_id)

    def add_rebuttal(self, rebuttal: Rebuttal) -> None:
        with self._lock:
            self._rebuttals[rebuttal.rebuttal_id] = rebuttal

    def get_argument(self, arg_id: str) -> Optional[Argument]:
        with self._lock:
            return self._arguments.get(arg_id)

    def all_arguments(self) -> List[Argument]:
        with self._lock:
            return list(self._arguments.values())

    def arguments_by_type(self, argument_type: ArgumentType) -> List[Argument]:
        with self._lock:
            return [a for a in self._arguments.values() if a.argument_type == argument_type]

    def arguments_by_participant(self, participant_id: str) -> List[Argument]:
        with self._lock:
            return [a for a in self._arguments.values() if a.participant_id == participant_id]

    def arguments_by_round(self, round_num: int) -> List[Argument]:
        with self._lock:
            ids = self._by_round.get(round_num, [])
            return [self._arguments[i] for i in ids if i in self._arguments]

    def rebuttals_for(self, arg_id: str) -> List[Rebuttal]:
        with self._lock:
            return [r for r in self._rebuttals.values() if r.target_arg_id == arg_id]

    def all_rebuttals(self) -> List[Rebuttal]:
        with self._lock:
            return list(self._rebuttals.values())

    def argument_count(self) -> int:
        with self._lock:
            return len(self._arguments)

    def rebuttal_count(self) -> int:
        with self._lock:
            return len(self._rebuttals)

    def supporting_arguments(self) -> List[Argument]:
        return self.arguments_by_type(ArgumentType.SUPPORTING)

    def opposing_arguments(self) -> List[Argument]:
        return self.arguments_by_type(ArgumentType.OPPOSING)

    def weighted_support_score(self) -> float:
        """Net weighted support score (-100 to +100)."""
        with self._lock:
            total_weight = sum(a.weight for a in self._arguments.values())
            if total_weight == 0:
                return 0.0
            score = 0.0
            for a in self._arguments.values():
                sign = 1.0 if a.argument_type == ArgumentType.SUPPORTING else (
                    -1.0 if a.argument_type == ArgumentType.OPPOSING else 0.0
                )
                score += sign * (a.confidence / 100) * a.weight
            return round((score / total_weight) * 100, 2)
