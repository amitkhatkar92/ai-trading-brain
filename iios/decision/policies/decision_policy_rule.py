"""
decision_policy_rule.py — iios.decision.policies
==================================================
A policy rule: a combination of conditions that produces an action
when triggered.

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from .constants import PolicyAction, PolicyRuleLogic
from .decision_policy_condition import PolicyCondition
from .decision_policy_result import PolicyRuleResult


@dataclass
class PolicyRule:
    """
    A named rule that groups :class:`PolicyCondition` objects under a
    logical combinator and yields a :class:`PolicyAction` when triggered.

    Parameters
    ----------
    rule_id :     Unique identifier.
    name :        Human-readable name.
    conditions :  List of conditions to evaluate.
    action :      Action emitted when the rule triggers.
    logic :       How conditions are combined (AND / OR / NOT).
    description : Optional explanation.
    weight :      Relative importance (used by WEIGHTED chains).
    """

    rule_id:     str
    name:        str
    conditions:  List[PolicyCondition]
    action:      PolicyAction
    logic:       PolicyRuleLogic = PolicyRuleLogic.AND
    description: str              = ""
    weight:      float            = 1.0

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, context_data: dict) -> PolicyRuleResult:
        """
        Evaluate all conditions against *context_data* and return a
        :class:`PolicyRuleResult`.

        Logic semantics
        ---------------
        AND : All conditions must be True.
        OR  : At least one condition must be True.
        NOT : Negate the AND result (i.e. True if not all conditions met).
        """
        if not self.conditions:
            # Empty rule — never triggers
            return PolicyRuleResult(
                rule_id              = self.rule_id,
                rule_name            = self.name,
                triggered            = False,
                action               = None,
                reason               = "No conditions defined",
                conditions_met       = 0,
                conditions_evaluated = 0,
                weight               = self.weight,
            )

        results  = [c.evaluate(context_data) for c in self.conditions]
        met_count = sum(1 for r in results if r)
        total     = len(results)

        if self.logic == PolicyRuleLogic.AND:
            triggered = all(results)
        elif self.logic == PolicyRuleLogic.OR:
            triggered = any(results)
        elif self.logic == PolicyRuleLogic.NOT:
            triggered = not all(results)
        else:
            triggered = all(results)

        reason = ""
        if triggered:
            reason = self.description or f"Rule '{self.name}' triggered ({self.logic.value})"

        return PolicyRuleResult(
            rule_id              = self.rule_id,
            rule_name            = self.name,
            triggered            = triggered,
            action               = self.action if triggered else None,
            reason               = reason,
            conditions_met       = met_count,
            conditions_evaluated = total,
            weight               = self.weight,
        )

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        name:        str,
        conditions:  List[PolicyCondition],
        action:      PolicyAction,
        *,
        rule_id:     Optional[str]     = None,
        logic:       PolicyRuleLogic   = PolicyRuleLogic.AND,
        description: str               = "",
        weight:      float             = 1.0,
    ) -> "PolicyRule":
        """Create a new :class:`PolicyRule`."""
        return cls(
            rule_id     = rule_id or str(uuid.uuid4()),
            name        = name,
            conditions  = list(conditions),
            action      = action,
            logic       = logic,
            description = description,
            weight      = weight,
        )
