"""
collaboration_result.py -- iios.ai.collaboration.core
======================================================
:class:`CollaborationOutcome` — terminal outcome types.
:class:`CollaborationResult`  — immutable final result of a session.

A6 Multi-Agent Collaboration Framework — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Optional


class CollaborationOutcome(str, Enum):
    """Terminal outcome of a collaboration session."""

    CONSENSUS_REACHED = "consensus_reached"
    MAJORITY_VOTE     = "majority_vote"
    ESCALATED         = "escalated"
    TIMEOUT           = "timeout"
    FAILED            = "failed"
    CANCELLED         = "cancelled"


@dataclass(frozen=True)
class CollaborationResult:
    """
    Immutable final result produced when a :class:`CollaborationSession`
    closes.

    ``decision`` carries the winning position value (e.g. ``"for"``).
    ``confidence`` is 0.0–1.0.
    ``dissenting_agents`` contains agent_ids that voted against the decision.
    """

    result_id:           str
    session_id:          str
    outcome:             CollaborationOutcome
    decision:            Optional[Any]
    confidence:          float
    participating_agents: int
    rounds_completed:    int
    dissenting_agents:   FrozenSet[str]
    reasoning:           str
    completed_at:        float

    @classmethod
    def consensus(
        cls,
        session_id:          str,
        decision:            Any,
        confidence:          float,
        participating_agents: int,
        rounds_completed:    int,
        dissenting_agents:   FrozenSet[str] = frozenset(),
        reasoning:           str            = "",
    ) -> "CollaborationResult":
        return cls(
            result_id            = str(uuid.uuid4()),
            session_id           = session_id,
            outcome              = CollaborationOutcome.CONSENSUS_REACHED,
            decision             = decision,
            confidence           = confidence,
            participating_agents = participating_agents,
            rounds_completed     = rounds_completed,
            dissenting_agents    = dissenting_agents,
            reasoning            = reasoning,
            completed_at         = time.time(),
        )

    @classmethod
    def majority(
        cls,
        session_id:          str,
        decision:            Any,
        confidence:          float,
        participating_agents: int,
        rounds_completed:    int,
        dissenting_agents:   FrozenSet[str] = frozenset(),
        reasoning:           str            = "",
    ) -> "CollaborationResult":
        return cls(
            result_id            = str(uuid.uuid4()),
            session_id           = session_id,
            outcome              = CollaborationOutcome.MAJORITY_VOTE,
            decision             = decision,
            confidence           = confidence,
            participating_agents = participating_agents,
            rounds_completed     = rounds_completed,
            dissenting_agents    = dissenting_agents,
            reasoning            = reasoning,
            completed_at         = time.time(),
        )

    @classmethod
    def escalated(
        cls,
        session_id:          str,
        reason:              str,
        participating_agents: int,
        rounds_completed:    int,
    ) -> "CollaborationResult":
        return cls(
            result_id            = str(uuid.uuid4()),
            session_id           = session_id,
            outcome              = CollaborationOutcome.ESCALATED,
            decision             = None,
            confidence           = 0.0,
            participating_agents = participating_agents,
            rounds_completed     = rounds_completed,
            dissenting_agents    = frozenset(),
            reasoning            = reason,
            completed_at         = time.time(),
        )

    @classmethod
    def failed(
        cls,
        session_id:          str,
        reason:              str,
        participating_agents: int = 0,
        rounds_completed:    int  = 0,
    ) -> "CollaborationResult":
        return cls(
            result_id            = str(uuid.uuid4()),
            session_id           = session_id,
            outcome              = CollaborationOutcome.FAILED,
            decision             = None,
            confidence           = 0.0,
            participating_agents = participating_agents,
            rounds_completed     = rounds_completed,
            dissenting_agents    = frozenset(),
            reasoning            = reason,
            completed_at         = time.time(),
        )

    def is_decided(self) -> bool:
        return self.outcome in (
            CollaborationOutcome.CONSENSUS_REACHED,
            CollaborationOutcome.MAJORITY_VOTE,
        )
