"""
iios/execution/recovery/policies/recovery_policy.py
===================================================
Abstract RecoveryPolicy base class and all eight concrete implementations.

Policy evaluation result:
- PolicyEvaluationResult (mutable internal DTO returned from evaluate())

Concrete policies:
- RetryPolicy
- ResumePolicy
- RollbackPolicy
- RestartPolicy
- FailoverPolicy
- ManualInterventionPolicy   (fallback — applies to any failure)
- EmergencyShutdownPolicy   (highest priority, safety-critical)
- CompositePolicy           (chains member policies)

C7 Execution Recovery & Resilience — Phase 1, Module 3
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .constants import (
    CONFIDENCE_EMERGENCY_SHUTDOWN,
    CONFIDENCE_FAILOVER,
    CONFIDENCE_MANUAL,
    CONFIDENCE_RESTART,
    CONFIDENCE_RESUME,
    CONFIDENCE_RETRY,
    CONFIDENCE_ROLLBACK,
    FailureCategory,
    FailureSeverity,
    RecoveryStrategyType,
    RuleConditionOperator,
)
from .recovery_context import PolicyEvaluationContext
from .recovery_rule import RecoveryRule, RuleCondition, make_rule


# ── Internal evaluation result ────────────────────────────────────────────────

@dataclass
class PolicyEvaluationResult:
    """
    Mutable result returned by RecoveryPolicy.evaluate().

    Used only inside the engine — never exposed in the public API.
    """
    matched:           bool                  = False
    strategy_type:     RecoveryStrategyType  = RecoveryStrategyType.MANUAL_INTERVENTION
    confidence_score:  float                 = 0.0
    matched_rules:     List[str]             = field(default_factory=list)
    reasons:           List[str]             = field(default_factory=list)
    policy_name:       str                   = ""


# ── Abstract base ─────────────────────────────────────────────────────────────

class RecoveryPolicy(ABC):
    """
    Abstract base for all recovery policies.

    Subclasses set their applicable_categories and populate self.rules in
    __init__; then evaluate() iterates the rules against the context.
    """

    def __init__(
        self,
        name: str,
        policy_type: RecoveryStrategyType,
        priority: int,
        applicable_categories: Tuple[FailureCategory, ...],
        *,
        is_fallback: bool = False,
    ) -> None:
        self.name = name
        self.policy_type = policy_type
        self.priority = priority
        self.applicable_categories = applicable_categories
        self._is_fallback = is_fallback
        self.rules: Tuple[RecoveryRule, ...] = ()

    @property
    def is_fallback(self) -> bool:
        return self._is_fallback

    def can_apply(self, context: PolicyEvaluationContext) -> bool:
        """True if this policy can handle the failure category in *context*."""
        return (
            not self.applicable_categories
            or context.failure_category in self.applicable_categories
        )

    @abstractmethod
    def evaluate(self, context: PolicyEvaluationContext) -> PolicyEvaluationResult:
        """Evaluate all rules and return the best matching result."""

    def _evaluate_rules(self, context: PolicyEvaluationContext) -> PolicyEvaluationResult:
        """
        Default rule evaluation loop — can be reused by concrete classes.

        Returns the result of the first matching rule (highest-priority first).
        Rules are sorted by priority descending before evaluation.
        """
        result = PolicyEvaluationResult(policy_name=self.name)
        for rule in sorted(self.rules, key=lambda r: -r.priority):
            if rule.evaluate(context):
                result.matched          = True
                result.strategy_type    = rule.strategy_type
                result.confidence_score = rule.confidence_score
                result.matched_rules.append(rule.rule_id)
                result.reasons.append(
                    f"rule={rule.name}: matched for category="
                    f"{context.failure_category.value}"
                )
                break
        return result


# ── Concrete policy: Retry ────────────────────────────────────────────────────

class RetryPolicy(RecoveryPolicy):
    """
    Recommends retrying transient failures when retries are not exhausted
    and the severity is not critical.
    """

    def __init__(self) -> None:
        super().__init__(
            name="RetryPolicy",
            policy_type=RecoveryStrategyType.RETRY,
            priority=60,
            applicable_categories=(
                FailureCategory.TIMEOUT,
                FailureCategory.GATEWAY_FAILURE,
                FailureCategory.NETWORK_FAILURE,
            ),
        )
        self.rules = (
            make_rule(
                name="TransientFailureRetry",
                description="Retry if not exhausted and severity not critical",
                conditions=(
                    RuleCondition("is_retry_exhausted", RuleConditionOperator.IS_FALSE, None),
                    RuleCondition(
                        "failure_severity",
                        RuleConditionOperator.NOT_IN,
                        (FailureSeverity.CRITICAL,),
                    ),
                ),
                strategy_type=RecoveryStrategyType.RETRY,
                confidence_score=CONFIDENCE_RETRY,
                priority=10,
            ),
        )

    def evaluate(self, context: PolicyEvaluationContext) -> PolicyEvaluationResult:
        if not self.can_apply(context):
            return PolicyEvaluationResult(policy_name=self.name)
        return self._evaluate_rules(context)


# ── Concrete policy: Resume ───────────────────────────────────────────────────

class ResumePolicy(RecoveryPolicy):
    """
    Recommends resuming execution from the last checkpoint for non-critical
    execution failures when the subsystem is still healthy.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ResumePolicy",
            policy_type=RecoveryStrategyType.RESUME,
            priority=55,
            applicable_categories=(FailureCategory.EXECUTION_FAILURE,),
        )
        self.rules = (
            make_rule(
                name="ExecutionResume",
                description="Resume if subsystem healthy and severity is not high/critical",
                conditions=(
                    RuleCondition("is_subsystem_healthy", RuleConditionOperator.IS_TRUE, None),
                    RuleCondition(
                        "failure_severity",
                        RuleConditionOperator.NOT_IN,
                        (FailureSeverity.HIGH, FailureSeverity.CRITICAL),
                    ),
                ),
                strategy_type=RecoveryStrategyType.RESUME,
                confidence_score=CONFIDENCE_RESUME,
                priority=10,
            ),
        )

    def evaluate(self, context: PolicyEvaluationContext) -> PolicyEvaluationResult:
        if not self.can_apply(context):
            return PolicyEvaluationResult(policy_name=self.name)
        return self._evaluate_rules(context)


# ── Concrete policy: Rollback ─────────────────────────────────────────────────

class RollbackPolicy(RecoveryPolicy):
    """
    Recommends rolling back to a consistent state when rollback is available
    and the failure compromises data integrity.
    """

    def __init__(self) -> None:
        super().__init__(
            name="RollbackPolicy",
            policy_type=RecoveryStrategyType.ROLLBACK,
            priority=70,
            applicable_categories=(
                FailureCategory.DATA_INTEGRITY_FAILURE,
                FailureCategory.EXECUTION_FAILURE,
            ),
        )
        self.rules = (
            make_rule(
                name="DataIntegrityRollback",
                description="Rollback when rollback available and risk limits intact",
                conditions=(
                    RuleCondition("rollback_available", RuleConditionOperator.IS_TRUE, None),
                    RuleCondition("is_within_risk_limits", RuleConditionOperator.IS_TRUE, None),
                ),
                strategy_type=RecoveryStrategyType.ROLLBACK,
                confidence_score=CONFIDENCE_ROLLBACK,
                priority=10,
            ),
        )

    def evaluate(self, context: PolicyEvaluationContext) -> PolicyEvaluationResult:
        if not self.can_apply(context):
            return PolicyEvaluationResult(policy_name=self.name)
        return self._evaluate_rules(context)


# ── Concrete policy: Restart ──────────────────────────────────────────────────

class RestartPolicy(RecoveryPolicy):
    """
    Recommends restarting the failed subsystem when restart budget remains.
    """

    def __init__(self) -> None:
        super().__init__(
            name="RestartPolicy",
            policy_type=RecoveryStrategyType.RESTART,
            priority=65,
            applicable_categories=(
                FailureCategory.EXECUTION_FAILURE,
                FailureCategory.INFRASTRUCTURE_FAILURE,
            ),
        )
        self.rules = (
            make_rule(
                name="SubsystemRestart",
                description="Restart if restart budget remains",
                conditions=(
                    RuleCondition("restart_count", RuleConditionOperator.LESS_THAN, 3),
                    RuleCondition(
                        "failure_severity",
                        RuleConditionOperator.NOT_IN,
                        (FailureSeverity.CRITICAL,),
                    ),
                ),
                strategy_type=RecoveryStrategyType.RESTART,
                confidence_score=CONFIDENCE_RESTART,
                priority=10,
            ),
        )

    def evaluate(self, context: PolicyEvaluationContext) -> PolicyEvaluationResult:
        if not self.can_apply(context):
            return PolicyEvaluationResult(policy_name=self.name)
        return self._evaluate_rules(context)


# ── Concrete policy: Failover ─────────────────────────────────────────────────

class FailoverPolicy(RecoveryPolicy):
    """
    Recommends failing over to a redundant subsystem or broker for
    high-severity broker/gateway failures.
    """

    def __init__(self) -> None:
        super().__init__(
            name="FailoverPolicy",
            policy_type=RecoveryStrategyType.FAILOVER,
            priority=75,
            applicable_categories=(
                FailureCategory.BROKER_FAILURE,
                FailureCategory.GATEWAY_FAILURE,
                FailureCategory.INFRASTRUCTURE_FAILURE,
            ),
        )
        self.rules = (
            make_rule(
                name="HighSeverityFailover",
                description="Failover for high or critical severity broker/gateway failures",
                conditions=(
                    RuleCondition(
                        "failure_severity",
                        RuleConditionOperator.IN,
                        (FailureSeverity.HIGH, FailureSeverity.CRITICAL),
                    ),
                ),
                strategy_type=RecoveryStrategyType.FAILOVER,
                confidence_score=CONFIDENCE_FAILOVER,
                priority=20,
            ),
            make_rule(
                name="SubsystemUnavailableFailover",
                description="Failover when subsystem availability is very low",
                conditions=(
                    RuleCondition(
                        "subsystem_availability",
                        RuleConditionOperator.LESS_THAN,
                        0.3,
                    ),
                ),
                strategy_type=RecoveryStrategyType.FAILOVER,
                confidence_score=CONFIDENCE_FAILOVER - 0.05,
                priority=10,
            ),
        )

    def evaluate(self, context: PolicyEvaluationContext) -> PolicyEvaluationResult:
        if not self.can_apply(context):
            return PolicyEvaluationResult(policy_name=self.name)
        return self._evaluate_rules(context)


# ── Concrete policy: Manual Intervention ─────────────────────────────────────

class ManualInterventionPolicy(RecoveryPolicy):
    """
    Fallback policy — requires human operator review.  Applies to all failure
    categories; used when no other policy matches.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ManualInterventionPolicy",
            policy_type=RecoveryStrategyType.MANUAL_INTERVENTION,
            priority=10,
            applicable_categories=(),   # empty = applies to all
            is_fallback=True,
        )
        # No rules — always matches as the fallback
        self.rules = ()

    def evaluate(self, context: PolicyEvaluationContext) -> PolicyEvaluationResult:
        result = PolicyEvaluationResult(policy_name=self.name)
        result.matched          = True
        result.strategy_type    = RecoveryStrategyType.MANUAL_INTERVENTION
        result.confidence_score = CONFIDENCE_MANUAL
        result.reasons.append(
            f"fallback: manual intervention required for "
            f"category={context.failure_category.value}"
        )
        return result


# ── Concrete policy: Emergency Shutdown ──────────────────────────────────────

class EmergencyShutdownPolicy(RecoveryPolicy):
    """
    Safety-critical policy — HIGHEST PRIORITY.  Triggers an emergency
    shutdown for risk violations and when risk limits are breached.
    """

    def __init__(self) -> None:
        super().__init__(
            name="EmergencyShutdownPolicy",
            policy_type=RecoveryStrategyType.EMERGENCY_SHUTDOWN,
            priority=100,   # absolute highest
            applicable_categories=(FailureCategory.RISK_VIOLATION,),
        )
        self.rules = (
            make_rule(
                name="RiskLimitBreach",
                description="Emergency shutdown when risk limits are violated",
                conditions=(
                    RuleCondition("is_within_risk_limits", RuleConditionOperator.IS_FALSE, None),
                ),
                strategy_type=RecoveryStrategyType.EMERGENCY_SHUTDOWN,
                confidence_score=CONFIDENCE_EMERGENCY_SHUTDOWN,
                priority=30,
            ),
            make_rule(
                name="RiskBreachCount",
                description="Emergency shutdown when breach count is positive",
                conditions=(
                    RuleCondition("breach_count", RuleConditionOperator.GREATER_THAN, 0),
                ),
                strategy_type=RecoveryStrategyType.EMERGENCY_SHUTDOWN,
                confidence_score=CONFIDENCE_EMERGENCY_SHUTDOWN,
                priority=20,
            ),
            make_rule(
                name="RiskViolationCategory",
                description="Emergency shutdown for any risk violation",
                conditions=(
                    RuleCondition(
                        "failure_category",
                        RuleConditionOperator.EQUALS,
                        FailureCategory.RISK_VIOLATION,
                    ),
                ),
                strategy_type=RecoveryStrategyType.EMERGENCY_SHUTDOWN,
                confidence_score=CONFIDENCE_EMERGENCY_SHUTDOWN - 0.02,
                priority=10,
            ),
        )

    def can_apply(self, context: PolicyEvaluationContext) -> bool:
        """Also applies when risk limits are breached, regardless of failure category."""
        return (
            context.failure_category in self.applicable_categories
            or not context.is_within_risk_limits
            or context.breach_count > 0
        )

    def evaluate(self, context: PolicyEvaluationContext) -> PolicyEvaluationResult:
        return self._evaluate_rules(context)


# ── Concrete policy: Composite ────────────────────────────────────────────────

class CompositePolicy(RecoveryPolicy):
    """
    Chains multiple member policies and returns the result with the
    highest confidence score among all matched members.
    """

    def __init__(
        self,
        name: str,
        member_policies: Tuple[RecoveryPolicy, ...],
        priority: int = 50,
    ) -> None:
        # Derive applicable categories as the union of all member categories
        all_cats: set = set()
        for p in member_policies:
            all_cats.update(p.applicable_categories)
        super().__init__(
            name=name,
            policy_type=RecoveryStrategyType.COMPOSITE,
            priority=priority,
            applicable_categories=tuple(all_cats),
        )
        self.member_policies = member_policies

    def evaluate(self, context: PolicyEvaluationContext) -> PolicyEvaluationResult:
        best = PolicyEvaluationResult(policy_name=self.name)
        for policy in sorted(self.member_policies, key=lambda p: -p.priority):
            res = policy.evaluate(context)
            if res.matched and res.confidence_score > best.confidence_score:
                best = res
                best.policy_name = self.name   # attribute composite name
        return best
