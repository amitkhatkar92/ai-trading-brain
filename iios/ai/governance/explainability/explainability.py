"""
explainability.py -- iios.ai.governance.explainability
========================================================
:class:`EvidenceReference`    — immutable reference to supporting evidence.
:class:`DecisionTrace`        — immutable step-by-step reasoning trace.
:class:`Explanation`          — full human-readable explanation of a decision.
:class:`ExplainabilityManager` — generates and stores explanations.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from ..core.governance_decision import GovernanceDecision
from ..exceptions.governance_exceptions import AIExplanationNotFoundError


@dataclass(frozen=True)
class EvidenceReference:
    """Immutable reference to a piece of evidence supporting a decision."""

    evidence_id:   str
    source_type:   str    # "policy", "risk_score", "audit_record", "metric", etc.
    source_id:     str
    description:   str
    weight:        float  # 0.0–1.0 relevance weight
    metadata:      FrozenSet[Tuple[str, Any]]

    @classmethod
    def create(
        cls,
        source_type: str,
        source_id:   str,
        description: str   = "",
        weight:      float = 1.0,
        **metadata: Any,
    ) -> "EvidenceReference":
        return cls(
            evidence_id = str(uuid.uuid4()),
            source_type = source_type,
            source_id   = source_id,
            description = description,
            weight      = max(0.0, min(1.0, weight)),
            metadata    = frozenset(metadata.items()),
        )


@dataclass(frozen=True)
class DecisionTrace:
    """Immutable step-by-step reasoning trace for one governance decision."""

    trace_id:   str
    decision_id: str
    steps:      tuple          # Tuple[str, ...]  ordered reasoning steps
    confidence: float          # 0.0–1.0
    evidence:   FrozenSet[EvidenceReference]
    traced_at:  float

    @classmethod
    def build(
        cls,
        decision_id: str,
        steps:       List[str],
        evidence:    List[EvidenceReference] = None,
        confidence:  float = 1.0,
    ) -> "DecisionTrace":
        return cls(
            trace_id    = str(uuid.uuid4()),
            decision_id = decision_id,
            steps       = tuple(steps),
            confidence  = max(0.0, min(1.0, confidence)),
            evidence    = frozenset(evidence or []),
            traced_at   = time.time(),
        )


@dataclass(frozen=True)
class Explanation:
    """
    Full human-readable explanation of a governance decision.

    ``summary``   — one-sentence summary.
    ``detail``    — multi-line narrative.
    ``trace``     — :class:`DecisionTrace` with step-by-step reasoning.
    """

    explanation_id: str
    decision_id:    str
    subject_id:     str
    summary:        str
    detail:         str
    trace:          DecisionTrace
    generated_at:   float
    metadata:       FrozenSet[Tuple[str, Any]]

    @classmethod
    def generate(
        cls,
        decision:   GovernanceDecision,
        subject_id: str,
        steps:      List[str]               = None,
        evidence:   List[EvidenceReference] = None,
        confidence: float                   = 1.0,
        detail:     str                     = "",
        **metadata: Any,
    ) -> "Explanation":
        default_steps = [
            f"Action: {decision.context_id}",
            f"Decision type: {decision.decision_type.value}",
            f"Rationale: {decision.rationale}",
            f"Severity: {decision.severity.value}",
            f"Policies applied: {', '.join(decision.policy_ids) or 'none'}",
        ]
        trace = DecisionTrace.build(
            decision_id = decision.decision_id,
            steps       = steps or default_steps,
            evidence    = evidence or [],
            confidence  = confidence,
        )
        summary = (
            f"Decision {decision.decision_type.value.upper()}: {decision.rationale}"
        )
        return cls(
            explanation_id = str(uuid.uuid4()),
            decision_id    = decision.decision_id,
            subject_id     = subject_id,
            summary        = summary,
            detail         = detail or summary,
            trace          = trace,
            generated_at   = time.time(),
            metadata       = frozenset(metadata.items()),
        )


class ExplainabilityManager:
    """Thread-safe store for :class:`Explanation` objects."""

    def __init__(self) -> None:
        self._lock:         threading.Lock           = threading.Lock()
        self._explanations: Dict[str, Explanation]   = {}

    def add(self, explanation: Explanation) -> None:
        with self._lock:
            self._explanations[explanation.explanation_id] = explanation

    def get(self, explanation_id: str) -> Explanation:
        with self._lock:
            ex = self._explanations.get(explanation_id)
        if ex is None:
            raise AIExplanationNotFoundError(
                f"Explanation {explanation_id!r} not found"
            )
        return ex

    def for_decision(self, decision_id: str) -> List[Explanation]:
        with self._lock:
            return [e for e in self._explanations.values()
                    if e.decision_id == decision_id]

    def generate_and_store(
        self,
        decision:   GovernanceDecision,
        subject_id: str,
        **kwargs: Any,
    ) -> Explanation:
        ex = Explanation.generate(decision, subject_id, **kwargs)
        self.add(ex)
        return ex

    def total_count(self) -> int:
        with self._lock:
            return len(self._explanations)
