"""
knowledge_policy_response.py — iios.knowledge.policies
--------------------------------------------------------
KnowledgePolicyResponse — the output of a governance framework evaluation.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import GovernanceDecision, PolicyDomain, PolicyType
from .knowledge_policy_result import PolicyEvaluationResult


@dataclass(frozen=True)
class GovernanceDecisionRecord:
    """
    A structured record of a single policy's governance decision.
    Builds the per-policy component of an audit trail.
    """
    knowledge_id:  str
    subsystem_id:  str
    decision:      GovernanceDecision
    policy_id:     str
    policy_name:   str
    policy_type:   PolicyType
    domain:        PolicyDomain
    conditions:    int            # total conditions evaluated across all rules
    reason:        str
    is_blocking:   bool           # True if BLOCKED or REJECTED
    evaluated_at:  str            # ISO-8601

    @classmethod
    def from_evaluation_result(
        cls,
        result:       PolicyEvaluationResult,
        knowledge_id: str,
        subsystem_id: str,
    ) -> "GovernanceDecisionRecord":
        total_conditions = sum(r.conditions_total for r in result.rule_results)
        is_blocking = result.decision in (
            GovernanceDecision.BLOCKED,
            GovernanceDecision.REJECTED,
        )
        return cls(
            knowledge_id = knowledge_id,
            subsystem_id = subsystem_id,
            decision     = result.decision,
            policy_id    = result.policy_id,
            policy_name  = result.policy_name,
            policy_type  = result.policy_type,
            domain       = result.domain,
            conditions   = total_conditions,
            reason       = result.reason,
            is_blocking  = is_blocking,
            evaluated_at = result.evaluated_at,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "subsystem_id": self.subsystem_id,
            "decision":     self.decision.value,
            "policy_id":    self.policy_id,
            "policy_name":  self.policy_name,
            "policy_type":  self.policy_type.value,
            "domain":       self.domain.value,
            "conditions":   self.conditions,
            "reason":       self.reason,
            "is_blocking":  self.is_blocking,
            "evaluated_at": self.evaluated_at,
        }


@dataclass(frozen=True)
class KnowledgePolicyResponse:
    """
    Immutable governance response returned by the KnowledgeGovernancePolicyEngine.
    """
    response_id:   str
    request_id:    str
    knowledge_id:  str
    decision:      GovernanceDecision       # aggregate decision
    decisions:     tuple                    # Tuple[GovernanceDecisionRecord]
    passed:        bool                     # True if approved / approved_with_conditions
    errors:        tuple                    # Tuple[str]
    warnings:      tuple                    # Tuple[str]
    evaluation_ms: float
    audit_trail:   tuple                    # Tuple[dict]
    responded_at:  str                      # ISO-8601

    # ------------------------------------------------------------------
    # Convenience property
    # ------------------------------------------------------------------

    @property
    def is_approved(self) -> bool:
        return self.passed

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def success(
        cls,
        *,
        request_id:    str,
        knowledge_id:  str,
        decision:      GovernanceDecision,
        decisions:     Optional[List[GovernanceDecisionRecord]] = None,
        warnings:      Optional[List[str]]                      = None,
        evaluation_ms: float                                    = 0.0,
        audit_trail:   Optional[List[Dict[str, Any]]]           = None,
    ) -> "KnowledgePolicyResponse":
        passed = decision in (
            GovernanceDecision.APPROVED,
            GovernanceDecision.APPROVED_WITH_CONDITIONS,
        )
        return cls(
            response_id   = f"resp-{uuid.uuid4().hex[:12]}",
            request_id    = request_id,
            knowledge_id  = knowledge_id,
            decision      = decision,
            decisions     = tuple(decisions or []),
            passed        = passed,
            errors        = (),
            warnings      = tuple(warnings or []),
            evaluation_ms = evaluation_ms,
            audit_trail   = tuple(audit_trail or []),
            responded_at  = datetime.now(tz=timezone.utc).isoformat(),
        )

    @classmethod
    def failure(
        cls,
        *,
        request_id:    str,
        knowledge_id:  str,
        errors:        List[str],
        decision:      GovernanceDecision = GovernanceDecision.REJECTED,
        evaluation_ms: float              = 0.0,
    ) -> "KnowledgePolicyResponse":
        return cls(
            response_id   = f"resp-{uuid.uuid4().hex[:12]}",
            request_id    = request_id,
            knowledge_id  = knowledge_id,
            decision      = decision,
            decisions     = (),
            passed        = False,
            errors        = tuple(errors),
            warnings      = (),
            evaluation_ms = evaluation_ms,
            audit_trail   = (),
            responded_at  = datetime.now(tz=timezone.utc).isoformat(),
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id":   self.response_id,
            "request_id":    self.request_id,
            "knowledge_id":  self.knowledge_id,
            "decision":      self.decision.value,
            "decisions":     [d.to_dict() for d in self.decisions],
            "passed":        self.passed,
            "is_approved":   self.is_approved,
            "errors":        list(self.errors),
            "warnings":      list(self.warnings),
            "evaluation_ms": self.evaluation_ms,
            "audit_trail":   list(self.audit_trail),
            "responded_at":  self.responded_at,
        }
