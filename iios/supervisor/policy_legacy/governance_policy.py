"""
governance_policy.py — iios.supervisor.policy
----------------------------------------------
Immutable governance policy value object.

A policy is a versioned, named collection of
:class:`GovernancePolicyRule` objects that governs a particular
enterprise governance domain.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    DEFAULT_POLICY_ACTION,
    VERSION,
    EvaluationMode,
    GovernancePolicyType,
    PolicyAction,
    PolicyPriority,
)
from .governance_policy_rule import GovernancePolicyRule


@dataclass(frozen=True)
class GovernancePolicy:
    """
    Immutable versioned enterprise governance policy.

    Fields
    ------
    policy_id :         Unique identifier.
    name :              Human-readable name.
    policy_type :       Governance domain this policy governs.
    priority :          Evaluation priority (lower integer = higher priority).
    version :           Semantic version string.
    rules :             Ordered tuple of policy rules.
    evaluation_mode :   How rules are evaluated.
    default_action :    Action taken when no rule matches.
    enabled :           Whether this policy participates in evaluation.
    description :       Optional human-readable description.
    tags :              Categorisation tags.
    metadata :          Supplementary metadata.
    created_at :        Wall-clock creation time.
    framework_version : Framework version string.
    """
    policy_id:         str
    name:              str
    policy_type:       GovernancePolicyType
    priority:          PolicyPriority
    version:           str
    rules:             Tuple[GovernancePolicyRule, ...]
    evaluation_mode:   EvaluationMode  = EvaluationMode.SEQUENTIAL
    default_action:    PolicyAction    = DEFAULT_POLICY_ACTION
    enabled:           bool            = True
    description:       str             = ""
    tags:              Tuple[str, ...] = field(default_factory=tuple)
    metadata:          Dict[str, Any]  = field(default_factory=dict)
    created_at:        float           = field(default_factory=time.time)
    framework_version: str             = VERSION

    @classmethod
    def create(
        cls,
        name:            str,
        policy_type:     GovernancePolicyType,
        priority:        PolicyPriority,
        rules:           List[GovernancePolicyRule],
        *,
        version:         str                      = "1.0.0",
        policy_id:       Optional[str]            = None,
        evaluation_mode: EvaluationMode           = EvaluationMode.SEQUENTIAL,
        default_action:  PolicyAction             = DEFAULT_POLICY_ACTION,
        enabled:         bool                     = True,
        description:     str                      = "",
        tags:            Optional[List[str]]      = None,
        metadata:        Optional[Dict[str, Any]] = None,
    ) -> "GovernancePolicy":
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
            metadata        = dict(metadata or {}),
        )

    @property
    def rule_count(self) -> int:
        return len(self.rules)

    @property
    def is_enabled(self) -> bool:
        return self.enabled

    def with_enabled(self, enabled: bool) -> "GovernancePolicy":
        """Return a new policy with the enabled flag changed."""
        return GovernancePolicy(
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
            "rules":             [r.to_dict() for r in self.rules],
            "evaluation_mode":   self.evaluation_mode.value,
            "default_action":    self.default_action.value,
            "enabled":           self.enabled,
            "description":       self.description,
            "tags":              list(self.tags),
            "created_at":        self.created_at,
            "framework_version": self.framework_version,
        }
