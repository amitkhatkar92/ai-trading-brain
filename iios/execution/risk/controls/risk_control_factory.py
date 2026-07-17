"""iios/execution/risk/controls/risk_control_factory.py
==================================================
RiskControlFactory — creates policy instances and pre-built registries.

C6 Execution Intelligence — Phase 4, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .constants import PolicyType
from .exceptions import ControlFrameworkError
from .risk_control_policy import (
    BasePolicy,
    ConfigurablePolicy,
    EmergencyPolicy,
    HighestSeverityPolicy,
    MajorityPolicy,
    SingleRulePolicy,
    WeightedSeverityPolicy,
)


class RiskControlFactory:
    """
    Stateless factory for creating control policy instances.

    All ``create_*`` methods return a new instance.
    """

    @staticmethod
    def create_single_rule_policy(**kw) -> SingleRulePolicy:
        return SingleRulePolicy(**kw)

    @staticmethod
    def create_majority_policy(**kw) -> MajorityPolicy:
        return MajorityPolicy(**kw)

    @staticmethod
    def create_highest_severity_policy(**kw) -> HighestSeverityPolicy:
        return HighestSeverityPolicy(**kw)

    @staticmethod
    def create_weighted_severity_policy(**kw) -> WeightedSeverityPolicy:
        return WeightedSeverityPolicy(**kw)

    @staticmethod
    def create_emergency_policy(**kw) -> EmergencyPolicy:
        return EmergencyPolicy(**kw)

    @staticmethod
    def create_configurable_policy(fn, *, description: str = "Configurable policy") -> ConfigurablePolicy:
        return ConfigurablePolicy(fn, description=description)

    @staticmethod
    def create_by_type(policy_type: PolicyType, **kw) -> BasePolicy:
        """Create a built-in policy by its PolicyType."""
        _map = {
            PolicyType.SINGLE_RULE:       SingleRulePolicy,
            PolicyType.MAJORITY:          MajorityPolicy,
            PolicyType.HIGHEST_SEVERITY:  HighestSeverityPolicy,
            PolicyType.WEIGHTED_SEVERITY: WeightedSeverityPolicy,
            PolicyType.EMERGENCY:         EmergencyPolicy,
        }
        cls = _map.get(policy_type)
        if cls is None:
            raise ControlFrameworkError(
                f"Cannot create policy for type '{policy_type}'. "
                "Use create_configurable_policy() for CONFIGURABLE."
            )
        return cls(**kw)

    @staticmethod
    def create_all_policies(**kw) -> List[BasePolicy]:
        """Create one instance of every built-in policy type."""
        return [
            SingleRulePolicy(),
            MajorityPolicy(**{k: v for k, v in kw.items() if k == "pass_threshold"}),
            HighestSeverityPolicy(),
            WeightedSeverityPolicy(**{
                k: v for k, v in kw.items()
                if k in ("category_weights", "emergency_threshold", "block_threshold",
                         "override_threshold", "pause_threshold", "warning_threshold")
            }),
            EmergencyPolicy(),
        ]

    @staticmethod
    def create_default_registry() -> "ControlPolicyRegistry":  # type: ignore[name-defined]  # noqa
        """
        Create a ControlPolicyRegistry pre-loaded with all built-in policies.

        The registry is NOT started.  Callers must call ``.start()`` before use.
        """
        from .risk_control_registry import ControlPolicyRegistry

        registry = ControlPolicyRegistry()
        registry.start()
        for policy in RiskControlFactory.create_all_policies():
            registry.register(policy)
        return registry

    @staticmethod
    def available_policy_types() -> List[PolicyType]:
        return [
            PolicyType.SINGLE_RULE,
            PolicyType.MAJORITY,
            PolicyType.HIGHEST_SEVERITY,
            PolicyType.WEIGHTED_SEVERITY,
            PolicyType.EMERGENCY,
            PolicyType.CONFIGURABLE,
        ]
