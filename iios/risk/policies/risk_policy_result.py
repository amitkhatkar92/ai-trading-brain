"""
risk_policy_result.py — iios.risk.policies
============================================
Immutable per-policy evaluation result value object.

C11 Risk Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import VERSION, PolicyAction, PolicyPriority, PolicyType


@dataclass(frozen=True)
class RiskPolicyResult:
    """
    Immutable result of evaluating a single policy against an evaluation request.

    Fields
    ------
    result_id :           Unique identifier.
    policy_id :           Evaluated policy identifier.
    policy_name :         Policy human-readable name.
    policy_type :         Risk domain of the policy.
    priority :            Policy priority at evaluation time.
    action :              Governance outcome determined by this policy.
    triggered_rule_id :   Identifier of the rule that determined the action
                          (empty when default action applied).
    triggered_rule_name : Human-readable rule name.
    conditions_met :      Condition IDs that evaluated to True.
    conditions_failed :   Condition IDs that evaluated to False.
    rationale :           Human-readable explanation of the outcome.
    evaluated_at :        Wall-clock evaluation time.
    evaluation_elapsed_s : Time taken to evaluate this policy.
    metadata :            Supplementary metadata.
    framework_version :   Framework version string.
    """
    result_id:             str
    policy_id:             str
    policy_name:           str
    policy_type:           PolicyType
    priority:              PolicyPriority
    action:                PolicyAction
    triggered_rule_id:     str                    = ""
    triggered_rule_name:   str                    = ""
    conditions_met:        Tuple[str, ...]        = field(default_factory=tuple)
    conditions_failed:     Tuple[str, ...]        = field(default_factory=tuple)
    rationale:             str                    = ""
    evaluated_at:          float                  = field(default_factory=time.time)
    evaluation_elapsed_s:  float                  = 0.0
    metadata:              Dict[str, Any]         = field(default_factory=dict)
    framework_version:     str                    = VERSION

    @classmethod
    def create(
        cls,
        policy_id:   str,
        policy_name: str,
        policy_type: PolicyType,
        priority:    PolicyPriority,
        action:      PolicyAction,
        *,
        result_id:            Optional[str]      = None,
        triggered_rule_id:    str                = "",
        triggered_rule_name:  str                = "",
        conditions_met:       Tuple[str, ...]    = (),
        conditions_failed:    Tuple[str, ...]    = (),
        rationale:            str                = "",
        evaluation_elapsed_s: float              = 0.0,
        metadata:             Optional[Dict[str, Any]] = None,
    ) -> "RiskPolicyResult":
        return cls(
            result_id             = result_id or str(uuid.uuid4()),
            policy_id             = policy_id,
            policy_name           = policy_name,
            policy_type           = policy_type,
            priority              = priority,
            action                = action,
            triggered_rule_id     = triggered_rule_id,
            triggered_rule_name   = triggered_rule_name,
            conditions_met        = tuple(conditions_met),
            conditions_failed     = tuple(conditions_failed),
            rationale             = rationale,
            evaluation_elapsed_s  = evaluation_elapsed_s,
            metadata              = dict(metadata or {}),
        )

    @property
    def is_permissive(self) -> bool:
        from .constants import PERMISSIVE_ACTIONS
        return self.action in PERMISSIVE_ACTIONS

    @property
    def is_denying(self) -> bool:
        from .constants import DENY_ACTIONS
        return self.action in DENY_ACTIONS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id":            self.result_id,
            "policy_id":            self.policy_id,
            "policy_name":          self.policy_name,
            "policy_type":          self.policy_type.value,
            "priority":             self.priority.value,
            "action":               self.action.value,
            "triggered_rule_id":    self.triggered_rule_id,
            "triggered_rule_name":  self.triggered_rule_name,
            "conditions_met":       list(self.conditions_met),
            "conditions_failed":    list(self.conditions_failed),
            "rationale":            self.rationale,
            "evaluated_at":         self.evaluated_at,
            "evaluation_elapsed_s": self.evaluation_elapsed_s,
            "framework_version":    self.framework_version,
        }
