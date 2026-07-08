"""
iios/decisions/models/decision_candidate.py
============================================
DecisionCandidate — a DecisionOption under active evaluation.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..decision_constants import CandidateStatus, PolicyOutcome
from .decision_option import DecisionOption


@dataclass
class PolicyResult:
    """Outcome of one policy applied to a candidate."""
    policy_name: str
    outcome:     PolicyOutcome
    reason:      str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_name": self.policy_name,
            "outcome":     self.outcome.value,
            "reason":      self.reason,
        }


@dataclass
class DecisionCandidate:
    """
    A DecisionOption that has been admitted into the evaluation pipeline.

    Attributes
    ----------
    candidate_id      : Unique identifier.
    request_id        : Parent DecisionRequest.
    option            : The wrapped DecisionOption.
    dimension_scores  : Per-dimension evaluation scores [0, 1].
    composite_score   : Weighted aggregate of dimension_scores.
    status            : Lifecycle state.
    policy_results    : Policy evaluation outcomes.
    rank              : Final rank (1 = best).  0 = not yet ranked.
    selected          : True if this candidate was chosen.
    evaluation_ms     : Time spent evaluating this candidate.
    metadata          : Caller extras.
    evaluated_at      : Unix timestamp of scoring completion.
    """

    candidate_id:     str                   = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:       str                   = ""
    option:           DecisionOption        = field(default_factory=DecisionOption)
    dimension_scores: dict[str, float]      = field(default_factory=dict)
    composite_score:  float                 = 0.0
    status:           CandidateStatus       = CandidateStatus.PENDING
    policy_results:   list[PolicyResult]    = field(default_factory=list)
    rank:             int                   = 0
    selected:         bool                  = False
    evaluation_ms:    float                 = 0.0
    metadata:         dict[str, Any]        = field(default_factory=dict)
    evaluated_at:     float                 = 0.0

    @property
    def passed_all_policies(self) -> bool:
        return all(
            pr.outcome in (PolicyOutcome.PASS, PolicyOutcome.ABSTAIN, PolicyOutcome.OVERRIDE)
            for pr in self.policy_results
        )

    @property
    def has_policy_failure(self) -> bool:
        return any(pr.outcome == PolicyOutcome.FAIL for pr in self.policy_results)

    def add_policy_result(self, policy_name: str, outcome: PolicyOutcome, reason: str = "") -> None:
        self.policy_results.append(PolicyResult(policy_name=policy_name, outcome=outcome, reason=reason))

    def mark_evaluated(self, composite_score: float, dimension_scores: dict[str, float]) -> None:
        self.composite_score  = composite_score
        self.dimension_scores = dimension_scores
        self.status           = CandidateStatus.EVALUATED
        self.evaluated_at     = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id":     self.candidate_id,
            "request_id":       self.request_id,
            "option":           self.option.to_dict(),
            "dimension_scores": {k: round(v, 4) for k, v in self.dimension_scores.items()},
            "composite_score":  round(self.composite_score, 4),
            "status":           self.status.value,
            "policy_results":   [pr.to_dict() for pr in self.policy_results],
            "rank":             self.rank,
            "selected":         self.selected,
            "evaluation_ms":    round(self.evaluation_ms, 2),
            "evaluated_at":     self.evaluated_at,
        }
