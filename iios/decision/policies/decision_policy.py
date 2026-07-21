"""
decision_policy.py — iios.decision.policies
============================================
A named, versioned institutional policy.

A policy is a container of :class:`PolicyRule` objects.  When evaluated
against a :class:`PolicyEvaluationContext`, it returns a
:class:`SinglePolicyResult` that captures the triggered action, the
matched rules, and the evaluation rationale.

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from .constants import (
    VERSION,
    PolicyAction,
    PolicyPriority,
    PolicyStatus,
    PolicyType,
)
from .decision_policy_context import PolicyEvaluationContext
from .decision_policy_result   import PolicyRuleResult, SinglePolicyResult
from .decision_policy_rule     import PolicyRule


@dataclass
class DecisionPolicy:
    """
    An institutional decision policy.

    Evaluation algorithm
    --------------------
    1. Evaluate every rule against the context.
    2. Collect triggered rules (in definition order).
    3. The **first triggered rule's action** is the policy's action.
    4. If no rule triggers, fall back to ``default_action``.

    Parameters
    ----------
    policy_id :      Unique identifier.
    name :           Human-readable name.
    policy_type :    Categorises the policy (risk, compliance, etc.).
    priority :       Urgency level; governs conflict resolution.
    default_action : Action taken when no rule triggers.
    description :    Optional explanation.
    version :        Policy version string.
    status :         Lifecycle status (active, inactive, draft, deprecated).
    rules :          Ordered list of :class:`PolicyRule` objects.
    tags :           Searchable tags.
    metadata :       Arbitrary metadata.
    weight :         Relative importance for WEIGHTED chain mode.
    """

    policy_id:      str
    name:           str
    policy_type:    PolicyType
    priority:       PolicyPriority
    default_action: PolicyAction
    description:    str              = ""
    version:        str              = "1.0.0"
    status:         PolicyStatus     = PolicyStatus.ACTIVE
    rules:          List[PolicyRule] = field(default_factory=list)
    tags:           List[str]        = field(default_factory=list)
    metadata:       dict             = field(default_factory=dict)
    weight:         float            = 1.0

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def is_active(self) -> bool:
        return self.status == PolicyStatus.ACTIVE

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, context: PolicyEvaluationContext) -> SinglePolicyResult:
        """
        Evaluate the policy against *context* and return a
        :class:`SinglePolicyResult`.
        """
        t_start      = time.time()
        context_data = context.to_dict()

        rule_results:      List[PolicyRuleResult] = []
        triggered_action:  Optional[PolicyAction]  = None
        triggered_reason:  str                     = ""
        conditions_met    = 0
        conditions_total  = 0

        for rule in self.rules:
            rr = rule.evaluate(context_data)
            rule_results.append(rr)
            conditions_total += rr.conditions_evaluated
            conditions_met   += rr.conditions_met

            if rr.triggered and triggered_action is None:
                triggered_action = rr.action
                triggered_reason = rr.reason

        final_action = triggered_action if triggered_action is not None else self.default_action
        if not triggered_reason:
            triggered_reason = (
                f"No rules triggered; default action '{self.default_action.value}' applied"
            )

        return SinglePolicyResult(
            result_id         = str(uuid.uuid4()),
            policy_id         = self.policy_id,
            policy_name       = self.name,
            policy_type       = self.policy_type,
            priority          = self.priority,
            action            = final_action,
            conditions_met    = conditions_met,
            conditions_total  = conditions_total,
            rule_results      = tuple(rule_results),
            reason            = triggered_reason,
            evaluation_time_s = time.time() - t_start,
            evaluated_at      = datetime.now(timezone.utc),
            metadata          = {},
        )

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        name:           str,
        policy_type:    PolicyType,
        priority:       PolicyPriority,
        default_action: PolicyAction,
        *,
        policy_id:      Optional[str]        = None,
        description:    str                  = "",
        version:        str                  = "1.0.0",
        status:         PolicyStatus          = PolicyStatus.ACTIVE,
        rules:          Optional[List[PolicyRule]] = None,
        tags:           Optional[List[str]]   = None,
        metadata:       Optional[dict]        = None,
        weight:         float                 = 1.0,
    ) -> "DecisionPolicy":
        """Create a new :class:`DecisionPolicy`."""
        return cls(
            policy_id      = policy_id or str(uuid.uuid4()),
            name           = name,
            policy_type    = policy_type,
            priority       = priority,
            default_action = default_action,
            description    = description,
            version        = version,
            status         = status,
            rules          = list(rules or []),
            tags           = list(tags or []),
            metadata       = metadata or {},
            weight         = weight,
        )
