"""
ai_governance_policy_result.py — iios.supervisor.policies
-----------------------------------------------------------
Immutable per-policy evaluation result value object.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .constants import (
    VERSION,
    AIGovernancePolicyAction,
    AIGovernancePolicyType,
    DENY_ACTIONS,
    HUMAN_REVIEW_ACTIONS,
    PERMISSIVE_ACTIONS,
    STOP_ACTIONS,
    PolicyPriority,
)


@dataclass(frozen=True)
class AIGovernancePolicyResult:
    """
    Immutable result of evaluating a single :class:`AIGovernancePolicy`.

    Fields
    ------
    result_id :             Unique identifier.
    policy_id :             Evaluated policy identifier.
    policy_name :           Evaluated policy name.
    policy_type :           Governance domain.
    priority :              Policy enforcement priority.
    action :                Governance action prescribed by the policy.
    triggered_rule_id :     Rule that determined the action (empty = default).
    triggered_rule_name :   Human-readable rule name.
    conditions_met :        IDs of conditions that evaluated True.
    conditions_failed :     IDs of conditions that evaluated False.
    rationale :             Human-readable explanation.
    evaluated_at :          Wall-clock evaluation time.
    evaluation_elapsed_s :  Evaluation duration in seconds.
    metadata :              Arbitrary extension metadata.
    framework_version :     Framework version string.
    """
    result_id:             str
    policy_id:             str
    policy_name:           str
    policy_type:           AIGovernancePolicyType
    priority:              PolicyPriority
    action:                AIGovernancePolicyAction
    triggered_rule_id:     str             = ""
    triggered_rule_name:   str             = ""
    conditions_met:        Tuple[str, ...] = field(default_factory=tuple)
    conditions_failed:     Tuple[str, ...] = field(default_factory=tuple)
    rationale:             str             = ""
    evaluated_at:          float           = field(default_factory=time.time)
    evaluation_elapsed_s:  float           = 0.0
    metadata:              Dict[str, Any]  = field(default_factory=dict)
    framework_version:     str             = VERSION

    @classmethod
    def create(
        cls,
        policy_id:   str,
        policy_name: str,
        policy_type: AIGovernancePolicyType,
        priority:    PolicyPriority,
        action:      AIGovernancePolicyAction,
        *,
        result_id:            Optional[str]      = None,
        triggered_rule_id:    str                = "",
        triggered_rule_name:  str                = "",
        conditions_met:       Tuple[str, ...]    = (),
        conditions_failed:    Tuple[str, ...]    = (),
        rationale:            str                = "",
        evaluation_elapsed_s: float              = 0.0,
        metadata:             Optional[Dict]     = None,
    ) -> "AIGovernancePolicyResult":
        return cls(
            result_id            = result_id or str(uuid.uuid4()),
            policy_id            = policy_id,
            policy_name          = policy_name,
            policy_type          = policy_type,
            priority             = priority,
            action               = action,
            triggered_rule_id    = triggered_rule_id,
            triggered_rule_name  = triggered_rule_name,
            conditions_met       = conditions_met,
            conditions_failed    = conditions_failed,
            rationale            = rationale,
            evaluation_elapsed_s = evaluation_elapsed_s,
            metadata             = metadata or {},
        )

    # ------------------------------------------------------------------
    # Action classification properties
    # ------------------------------------------------------------------

    @property
    def is_permissive(self) -> bool:
        """True when the action permits the autonomous operation."""
        return self.action in PERMISSIVE_ACTIONS

    @property
    def is_denying(self) -> bool:
        """True when the action blocks or rejects the operation."""
        return self.action in DENY_ACTIONS

    @property
    def requires_human_approval(self) -> bool:
        """True when the action requires human review or approval."""
        return self.action in HUMAN_REVIEW_ACTIONS

    @property
    def is_emergency_stop(self) -> bool:
        """True when the action is an emergency stop."""
        return self.action in STOP_ACTIONS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id":             self.result_id,
            "policy_id":             self.policy_id,
            "policy_name":           self.policy_name,
            "policy_type":           self.policy_type.value,
            "priority":              self.priority.value,
            "action":                self.action.value,
            "triggered_rule_id":     self.triggered_rule_id,
            "triggered_rule_name":   self.triggered_rule_name,
            "conditions_met":        list(self.conditions_met),
            "conditions_failed":     list(self.conditions_failed),
            "rationale":             self.rationale,
            "is_permissive":         self.is_permissive,
            "is_denying":            self.is_denying,
            "requires_human_approval": self.requires_human_approval,
            "is_emergency_stop":     self.is_emergency_stop,
            "evaluation_elapsed_s":  self.evaluation_elapsed_s,
            "evaluated_at":          self.evaluated_at,
            "framework_version":     self.framework_version,
        }
