"""
ai_governance_policy_priority.py — iios.supervisor.policies
-------------------------------------------------------------
Priority configuration and resolution for AI governance policies.

Enriches the bare :class:`PolicyPriority` IntEnum with enterprise
behaviour attributes such as whether a priority level requires
immediate action, human oversight, or mandatory auditing.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict

from .constants import PolicyPriority

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Priority configuration dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AIGovernancePolicyPriorityConfig:
    """
    Enterprise configuration for a single :class:`PolicyPriority` level.

    Fields
    ------
    priority :                  The priority level this config describes.
    label :                     Short human-readable name (e.g. ``"Critical"``).
    description :               Explanation of when this priority applies.
    requires_immediate_action : Action must be taken without deferral.
    human_oversight_required :  A human must review the governance decision.
    audit_required :            All evaluations at this level must be audited.
    can_be_deferred :           Whether evaluation may be queued rather than synchronous.
    max_evaluation_timeout_s :  Maximum seconds allowed for evaluation at this level.
    """
    priority:                  PolicyPriority
    label:                     str
    description:               str
    requires_immediate_action: bool
    human_oversight_required:  bool
    audit_required:            bool
    can_be_deferred:           bool
    max_evaluation_timeout_s:  float


# ---------------------------------------------------------------------------
# Pre-built priority configs
# ---------------------------------------------------------------------------

PRIORITY_CONFIGS: Dict[PolicyPriority, AIGovernancePolicyPriorityConfig] = {
    PolicyPriority.CRITICAL: AIGovernancePolicyPriorityConfig(
        priority                  = PolicyPriority.CRITICAL,
        label                     = "Critical",
        description               = "System safety or regulatory mandate — overrides all other priorities",
        requires_immediate_action = True,
        human_oversight_required  = True,
        audit_required            = True,
        can_be_deferred           = False,
        max_evaluation_timeout_s  = 5.0,
    ),
    PolicyPriority.HIGH: AIGovernancePolicyPriorityConfig(
        priority                  = PolicyPriority.HIGH,
        label                     = "High",
        description               = "Important governance constraint — must be honoured before proceeding",
        requires_immediate_action = True,
        human_oversight_required  = False,
        audit_required            = True,
        can_be_deferred           = False,
        max_evaluation_timeout_s  = 10.0,
    ),
    PolicyPriority.MEDIUM: AIGovernancePolicyPriorityConfig(
        priority                  = PolicyPriority.MEDIUM,
        label                     = "Medium",
        description               = "Standard governance control — evaluated in normal flow",
        requires_immediate_action = False,
        human_oversight_required  = False,
        audit_required            = True,
        can_be_deferred           = False,
        max_evaluation_timeout_s  = 20.0,
    ),
    PolicyPriority.LOW: AIGovernancePolicyPriorityConfig(
        priority                  = PolicyPriority.LOW,
        label                     = "Low",
        description               = "Advisory control — evaluated opportunistically",
        requires_immediate_action = False,
        human_oversight_required  = False,
        audit_required            = False,
        can_be_deferred           = True,
        max_evaluation_timeout_s  = 30.0,
    ),
    PolicyPriority.INFORMATIONAL: AIGovernancePolicyPriorityConfig(
        priority                  = PolicyPriority.INFORMATIONAL,
        label                     = "Informational",
        description               = "Telemetry and logging — no action implications",
        requires_immediate_action = False,
        human_oversight_required  = False,
        audit_required            = False,
        can_be_deferred           = True,
        max_evaluation_timeout_s  = 30.0,
    ),
}


# ---------------------------------------------------------------------------
# Priority resolver
# ---------------------------------------------------------------------------

class AIGovernancePriorityResolver:
    """
    Utility class for querying enterprise priority configuration.

    All methods are static; no instance state is maintained.
    """

    @staticmethod
    def get_config(priority: PolicyPriority) -> AIGovernancePolicyPriorityConfig:
        """Return the :class:`AIGovernancePolicyPriorityConfig` for *priority*."""
        return PRIORITY_CONFIGS[priority]

    @staticmethod
    def requires_immediate_action(priority: PolicyPriority) -> bool:
        """True when the priority level mandates immediate handling."""
        return PRIORITY_CONFIGS[priority].requires_immediate_action

    @staticmethod
    def requires_human_oversight(priority: PolicyPriority) -> bool:
        """True when the priority level mandates human review of the decision."""
        return PRIORITY_CONFIGS[priority].human_oversight_required

    @staticmethod
    def requires_audit(priority: PolicyPriority) -> bool:
        """True when every evaluation at this priority level must be audited."""
        return PRIORITY_CONFIGS[priority].audit_required

    @staticmethod
    def can_be_deferred(priority: PolicyPriority) -> bool:
        """True when the evaluation may be deferred without violating governance."""
        return PRIORITY_CONFIGS[priority].can_be_deferred

    @staticmethod
    def max_evaluation_timeout_s(priority: PolicyPriority) -> float:
        """Maximum permitted evaluation latency in seconds for this priority level."""
        return PRIORITY_CONFIGS[priority].max_evaluation_timeout_s

    @staticmethod
    def effective_priority(*priorities: PolicyPriority) -> PolicyPriority:
        """
        Return the most critical (lowest integer value) of the supplied priorities.
        """
        if not priorities:
            return PolicyPriority.INFORMATIONAL
        return min(priorities, key=lambda p: p.value)
