"""
ai_governance_policy.py — iios.supervisor.policies
----------------------------------------------------
Immutable AI governance policy value object.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    VERSION,
    AIGovernancePolicyAction,
    AIGovernancePolicyType,
    DEFAULT_GOVERNANCE_ACTION,
    EvaluationMode,
    PolicyPriority,
)
from .ai_governance_policy_rule import AIGovernancePolicyRule


@dataclass(frozen=True)
class AIGovernancePolicy:
    """
    Immutable AI governance policy.

    A policy binds together a set of :class:`AIGovernancePolicyRule` objects
    under a declared type and priority.  When none of the rules match, the
    ``default_action`` is applied.

    Fields
    ------
    policy_id :         Unique identifier.
    name :              Human-readable label.
    policy_type :       Governance domain this policy belongs to.
    priority :          Enforcement priority (lower integer = higher priority).
    version :           Policy schema version.
    rules :             Ordered tuple of rules.
    evaluation_mode :   How rules are evaluated (SEQUENTIAL / PARALLEL / …).
    default_action :    Action when no rule matches.
    enabled :           Whether the policy is active.
    description :       Optional explanation.
    tags :              Searchable string tags.
    metadata :          Arbitrary extension metadata.
    created_at :        Wall-clock creation time.
    framework_version : Framework version string.
    """
    policy_id:         str
    name:              str
    policy_type:       AIGovernancePolicyType
    priority:          PolicyPriority
    version:           str
    rules:             Tuple[AIGovernancePolicyRule, ...]
    evaluation_mode:   EvaluationMode
    default_action:    AIGovernancePolicyAction
    enabled:           bool
    description:       str              = ""
    tags:              Tuple[str, ...]  = field(default_factory=tuple)
    metadata:          Dict[str, Any]   = field(default_factory=dict)
    created_at:        float            = field(default_factory=time.time)
    framework_version: str              = VERSION

    @classmethod
    def create(
        cls,
        name:        str,
        policy_type: AIGovernancePolicyType,
        priority:    PolicyPriority,
        rules:       List[AIGovernancePolicyRule],
        *,
        version:          str                           = "1.0.0",
        policy_id:        Optional[str]                 = None,
        evaluation_mode:  EvaluationMode                = EvaluationMode.SEQUENTIAL,
        default_action:   AIGovernancePolicyAction      = DEFAULT_GOVERNANCE_ACTION,
        enabled:          bool                          = True,
        description:      str                           = "",
        tags:             Optional[List[str]]           = None,
        metadata:         Optional[Dict[str, Any]]      = None,
    ) -> "AIGovernancePolicy":
        return cls(
            policy_id       = policy_id or str(uuid.uuid4()),
            name            = name,
            policy_type     = policy_type,
            priority        = priority,
            version         = version,
            rules           = tuple(rules),
            evaluation_mode = evaluation_mode,
            default_action  = default_action,
            enabled         = enabled,
            description     = description,
            tags            = tuple(tags or []),
            metadata        = metadata or {},
        )

    @property
    def rule_count(self) -> int:
        """Number of rules in this policy."""
        return len(self.rules)

    @property
    def is_enabled(self) -> bool:
        """True when the policy is active."""
        return self.enabled

    def with_enabled(self, enabled: bool) -> "AIGovernancePolicy":
        """Return a new policy with the given enabled state."""
        return AIGovernancePolicy(
            policy_id       = self.policy_id,
            name            = self.name,
            policy_type     = self.policy_type,
            priority        = self.priority,
            version         = self.version,
            rules           = self.rules,
            evaluation_mode = self.evaluation_mode,
            default_action  = self.default_action,
            enabled         = enabled,
            description     = self.description,
            tags            = self.tags,
            metadata        = self.metadata,
            created_at      = self.created_at,
            framework_version = self.framework_version,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id":         self.policy_id,
            "name":              self.name,
            "policy_type":       self.policy_type.value,
            "priority":          self.priority.value,
            "version":           self.version,
            "rule_count":        self.rule_count,
            "evaluation_mode":   self.evaluation_mode.value,
            "default_action":    self.default_action.value,
            "enabled":           self.enabled,
            "description":       self.description,
            "tags":              list(self.tags),
            "created_at":        self.created_at,
            "framework_version": self.framework_version,
        }
