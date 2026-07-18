"""
iios/execution/recovery/policies/recovery_response.py
=====================================================
RecoveryPolicyDecision and PolicyEvaluationReport — outputs from the
Recovery Policy Engine.

C7 Execution Recovery & Resilience — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import (
    VERSION,
    FailureCategory,
    FailureSeverity,
    PolicyPriority,
    RecoveryRecommendation,
    RecoveryStrategyType,
)


@dataclass(frozen=True)
class PolicyEvaluationReport:
    """Detailed record of a policy evaluation run."""

    report_id:           str
    request_id:          str
    policies_evaluated:  int
    rules_evaluated:     int
    matched_policies:    Tuple[str, ...]
    rejected_policies:   Tuple[str, ...]
    selected_policy:     str
    selected_strategy:   RecoveryStrategyType
    confidence_score:    float
    evaluation_time_ms:  float
    reasons:             Tuple[str, ...]
    used_fallback:       bool             = False
    framework_version:   str              = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":           self.report_id,
            "request_id":          self.request_id,
            "policies_evaluated":  self.policies_evaluated,
            "rules_evaluated":     self.rules_evaluated,
            "matched_policies":    list(self.matched_policies),
            "rejected_policies":   list(self.rejected_policies),
            "selected_policy":     self.selected_policy,
            "selected_strategy":   self.selected_strategy.value,
            "confidence_score":    self.confidence_score,
            "evaluation_time_ms":  self.evaluation_time_ms,
            "reasons":             list(self.reasons),
            "used_fallback":       self.used_fallback,
        }


@dataclass(frozen=True)
class RecoveryPolicyDecision:
    """
    Immutable policy decision returned by the Recovery Policy Engine.

    Contains the selected strategy, priority, recommendation, and full
    evaluation report.
    """

    decision_id:                str
    request_id:                 str
    execution_session_id:       str
    subsystem_id:               str
    is_approved:                bool
    strategy_type:              RecoveryStrategyType
    priority:                   PolicyPriority
    recommendation:             RecoveryRecommendation
    failure_category:           FailureCategory
    failure_severity:           FailureSeverity
    confidence_score:           float
    policy_name:                str
    matched_rules:              Tuple[str, ...]
    evaluation_reasons:         Tuple[str, ...]
    requires_failover:          bool
    requires_manual_intervention: bool
    evaluation_report:          PolicyEvaluationReport
    evaluation_time_ms:         float
    decided_at:                 float
    version:                    str              = VERSION
    metadata:                   Dict[str, Any]   = field(default_factory=dict)

    @property
    def is_retry(self) -> bool:
        return self.strategy_type == RecoveryStrategyType.RETRY

    @property
    def is_failover(self) -> bool:
        return self.strategy_type == RecoveryStrategyType.FAILOVER

    @property
    def is_emergency_shutdown(self) -> bool:
        return self.strategy_type == RecoveryStrategyType.EMERGENCY_SHUTDOWN

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence_score >= 0.80

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id":                  self.decision_id,
            "request_id":                   self.request_id,
            "execution_session_id":         self.execution_session_id,
            "subsystem_id":                 self.subsystem_id,
            "is_approved":                  self.is_approved,
            "strategy_type":                self.strategy_type.value,
            "priority":                     self.priority.value,
            "recommendation":               self.recommendation.value,
            "failure_category":             self.failure_category.value,
            "failure_severity":             self.failure_severity.value,
            "confidence_score":             self.confidence_score,
            "policy_name":                  self.policy_name,
            "matched_rules":                list(self.matched_rules),
            "evaluation_reasons":           list(self.evaluation_reasons),
            "requires_failover":            self.requires_failover,
            "requires_manual_intervention": self.requires_manual_intervention,
            "evaluation_time_ms":           self.evaluation_time_ms,
            "decided_at":                   self.decided_at,
            "version":                      self.version,
        }


def make_policy_decision(
    request_id: str,
    execution_session_id: str,
    subsystem_id: str,
    is_approved: bool,
    strategy_type: RecoveryStrategyType,
    priority: PolicyPriority,
    recommendation: RecoveryRecommendation,
    failure_category: FailureCategory,
    failure_severity: FailureSeverity,
    confidence_score: float,
    policy_name: str,
    evaluation_report: PolicyEvaluationReport,
    *,
    matched_rules: Tuple[str, ...] = (),
    evaluation_reasons: Tuple[str, ...] = (),
    requires_failover: bool = False,
    requires_manual_intervention: bool = False,
    evaluation_time_ms: float = 0.0,
    metadata: Optional[Dict[str, Any]] = None,
    decision_id: Optional[str] = None,
) -> RecoveryPolicyDecision:
    """Factory for RecoveryPolicyDecision."""
    return RecoveryPolicyDecision(
        decision_id                  = decision_id or str(uuid.uuid4()),
        request_id                   = request_id,
        execution_session_id         = execution_session_id,
        subsystem_id                 = subsystem_id,
        is_approved                  = is_approved,
        strategy_type                = strategy_type,
        priority                     = priority,
        recommendation               = recommendation,
        failure_category             = failure_category,
        failure_severity             = failure_severity,
        confidence_score             = confidence_score,
        policy_name                  = policy_name,
        matched_rules                = matched_rules,
        evaluation_reasons           = evaluation_reasons,
        requires_failover            = requires_failover,
        requires_manual_intervention = requires_manual_intervention,
        evaluation_report            = evaluation_report,
        evaluation_time_ms           = evaluation_time_ms,
        decided_at                   = time.time(),
        metadata                     = dict(metadata) if metadata else {},
    )
