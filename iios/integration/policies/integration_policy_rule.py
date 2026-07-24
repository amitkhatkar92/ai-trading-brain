"""
integration_policy_rule.py — iios.integration.policies
--------------------------------------------------------
IntegrationPolicyRule — a single governance rule within a policy.

A rule contains one or more conditions and, when the conditions are
satisfied, produces a PolicyAction.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .constants import PolicyAction, PolicyEvaluationMode
from .integration_policy_condition import IntegrationPolicyCondition


@dataclass(frozen=True)
class IntegrationPolicyRule:
    """
    A governance rule containing conditions and an action.

    All conditions are evaluated according to the evaluation_mode:
    - ALL_MUST_PASS → AND semantics
    - ANY_MUST_PASS → OR  semantics
    - NONE_MUST_PASS→ NOR semantics

    A rule with no conditions always fires.
    """

    rule_id:         str
    name:            str
    conditions:      Tuple[IntegrationPolicyCondition, ...]
    action:          PolicyAction
    evaluation_mode: PolicyEvaluationMode
    description:     str
    reason_template: str        # human-readable reason for the fired action
    metadata:        Dict[str, Any]
    created_at:      str

    # ── factory ───────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        name:            str,
        action:          PolicyAction,
        conditions:      Optional[List[IntegrationPolicyCondition]] = None,
        evaluation_mode: PolicyEvaluationMode = PolicyEvaluationMode.ALL_MUST_PASS,
        *,
        description:     str                       = "",
        reason_template: str                       = "",
        metadata:        Optional[Dict[str, Any]]  = None,
        rule_id:         Optional[str]             = None,
    ) -> "IntegrationPolicyRule":
        return cls(
            rule_id         = rule_id or f"rule-{uuid.uuid4().hex[:12]}",
            name            = name,
            conditions      = tuple(conditions or []),
            action          = (
                PolicyAction(action) if isinstance(action, str) else action
            ),
            evaluation_mode = evaluation_mode,
            description     = description,
            reason_template = reason_template or f"Rule '{name}' produced action {action}",
            metadata        = dict(metadata or {}),
            created_at      = datetime.now(timezone.utc).isoformat(),
        )

    # ── evaluation ────────────────────────────────────────────────────

    def evaluate(self, context_data: Dict[str, Any]) -> Optional[PolicyAction]:
        """
        Evaluate this rule against context data.

        Returns the configured action if the rule fires, else None.
        """
        if not self.conditions:
            # No conditions — unconditionally fires
            return self.action

        results = [c.evaluate(context_data) for c in self.conditions]
        mode    = self.evaluation_mode

        if mode == PolicyEvaluationMode.ALL_MUST_PASS:
            fired = all(results)
        elif mode == PolicyEvaluationMode.ANY_MUST_PASS:
            fired = any(results)
        else:  # NONE_MUST_PASS
            fired = not any(results)

        return self.action if fired else None

    # ── serialisation ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id":         self.rule_id,
            "name":            self.name,
            "conditions":      [c.to_dict() for c in self.conditions],
            "action":          self.action.value,
            "evaluation_mode": self.evaluation_mode.value,
            "description":     self.description,
            "reason_template": self.reason_template,
            "metadata":        self.metadata,
            "created_at":      self.created_at,
        }
