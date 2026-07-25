"""
workflow_policy.py — iios.workflow.policies
--------------------------------------------
WorkflowPolicy — a versioned, named governance policy consisting
of ordered rules evaluated against a WorkflowPolicyContext.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import PolicyAction, PolicyDomain, PolicyPriorityLevel, PolicyType
from .workflow_policy_condition import PolicyCondition
from .workflow_policy_context import WorkflowPolicyContext
from .workflow_policy_rule import PolicyRule


@dataclass(frozen=True)
class WorkflowPolicy:
    """
    A versioned enterprise governance policy.

    A policy contains an ordered list of rules.  During evaluation,
    rules are assessed in priority order (lowest priority value first).
    The first rule whose conditions are all satisfied determines the
    policy action.

    If no rules fire, the `default_action` is used (APPROVE by default).
    """
    policy_id:      str
    name:           str
    description:    str
    policy_type:    PolicyType
    domain:         PolicyDomain
    priority:       PolicyPriorityLevel
    rules:          tuple                      # Tuple[PolicyRule, ...]
    default_action: PolicyAction
    enabled:        bool
    version:        str
    created_at:     str
    metadata:       Dict[str, Any]

    @classmethod
    def create(
        cls,
        name:           str,
        policy_type:    PolicyType,
        *,
        domain:         PolicyDomain            = PolicyDomain.WORKFLOW_GOVERNANCE,
        priority:       PolicyPriorityLevel     = PolicyPriorityLevel.MEDIUM,
        rules:          Optional[List[PolicyRule]] = None,
        default_action: PolicyAction            = PolicyAction.APPROVE,
        description:    str                     = "",
        enabled:        bool                    = True,
        version:        str                     = "1.0.0",
        metadata:       Optional[Dict[str, Any]] = None,
        policy_id:      Optional[str]           = None,
    ) -> "WorkflowPolicy":
        # Sort rules by priority (lower value = evaluated first)
        sorted_rules = sorted(rules or [], key=lambda r: r.priority.value)
        return cls(
            policy_id      = policy_id or f"pol-{uuid.uuid4().hex[:12]}",
            name           = name,
            description    = description,
            policy_type    = policy_type,
            domain         = domain,
            priority       = priority,
            rules          = tuple(sorted_rules),
            default_action = default_action,
            enabled        = enabled,
            version        = version,
            created_at     = datetime.now(tz=timezone.utc).isoformat(),
            metadata       = dict(metadata or {}),
        )

    # ----------------------------------------------------------------
    # Evaluation
    # ----------------------------------------------------------------

    def evaluate(
        self,
        context: WorkflowPolicyContext,
    ) -> tuple:   # (PolicyAction, str, str | None)
        """
        Evaluate the policy against the context.

        Returns:
            (action, reasoning, matched_rule_id)
        """
        if not self.enabled:
            return (self.default_action, "Policy is disabled — default action applied", None)

        flat = context.to_flat_dict()
        for rule in self.rules:
            if rule.applies(flat):
                reasoning = (
                    f"Rule {rule.name!r} matched "
                    f"({len(rule.conditions)} condition(s)) → {rule.action.value}"
                )
                return (rule.action, reasoning, rule.rule_id)

        reasoning = (
            f"No rules matched — default action {self.default_action.value!r} applied"
        )
        return (self.default_action, reasoning, None)

    # ----------------------------------------------------------------
    # Introspection
    # ----------------------------------------------------------------

    @property
    def rule_count(self) -> int:
        return len(self.rules)

    @property
    def is_critical(self) -> bool:
        return self.priority == PolicyPriorityLevel.CRITICAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id":      self.policy_id,
            "name":           self.name,
            "description":    self.description,
            "policy_type":    self.policy_type.value,
            "domain":         self.domain.value,
            "priority":       self.priority.name,
            "default_action": self.default_action.value,
            "enabled":        self.enabled,
            "version":        self.version,
            "rule_count":     self.rule_count,
            "created_at":     self.created_at,
        }
