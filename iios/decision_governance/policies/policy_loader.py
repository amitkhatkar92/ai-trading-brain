"""iios/decision_governance/policies/policy_loader.py

Loads GovernancePolicies from configuration dictionaries.
All policy types are pluggable — no domain-specific logic here.
"""
from __future__ import annotations

from typing import Any

from iios.decision_governance.governance_constants import (
    PolicyType,
    PolicyViolationSeverity,
)
from iios.decision_governance.governance_exceptions import PolicyInvalidError
from iios.decision_governance.policies.governance_policy import (
    GovernancePolicy,
    PredicatePolicy,
    ScoreThresholdPolicy,
)


class PolicyLoader:
    """
    Instantiates GovernancePolicies from plain config dicts.

    Supported ``type`` keys in config:
    - ``score_threshold``  → ScoreThresholdPolicy
    - ``predicate``        → PredicatePolicy (requires "predicate" callable in extras)

    Custom types can be registered via ``register_type()``.
    """

    _registry: dict[str, type[GovernancePolicy]] = {}

    @classmethod
    def register_type(cls, type_key: str, policy_class: type[GovernancePolicy]) -> None:
        """Register a custom policy type for loading."""
        cls._registry[type_key] = policy_class

    @classmethod
    def load(cls, config: dict[str, Any], **extras: Any) -> GovernancePolicy:
        """
        Load a policy from a config dict.

        Required keys: ``policy_id``, ``name``, ``type``
        Optional keys: ``threshold``, ``severity``, ``policy_type``, ``tags``, ``blocking``
        """
        try:
            policy_id = config["policy_id"]
            name      = config["name"]
            type_key  = config["type"]
        except KeyError as k:
            raise PolicyInvalidError(f"Missing required config key: {k}") from k

        severity    = PolicyViolationSeverity(config.get("severity", "error"))
        policy_type = PolicyType(config.get("policy_type", "governance"))
        tags        = config.get("tags", [])
        blocking    = config.get("blocking", True)

        # Built-in types
        if type_key == "score_threshold":
            threshold = config.get("threshold")
            if threshold is None:
                raise PolicyInvalidError("score_threshold policy requires 'threshold'")
            return ScoreThresholdPolicy(
                policy_id=policy_id,
                name=name,
                threshold=float(threshold),
                severity=severity,
                policy_type=policy_type,
                tags=tags,
                blocking=blocking,
            )

        if type_key == "predicate":
            predicate = extras.get("predicate")
            if predicate is None or not callable(predicate):
                raise PolicyInvalidError(
                    "predicate policy requires a callable 'predicate' in extras"
                )
            return PredicatePolicy(
                policy_id=policy_id,
                name=name,
                predicate=predicate,
                violation_message=config.get("violation_message", "Predicate failed"),
                severity=severity,
                policy_type=policy_type,
                tags=tags,
                blocking=blocking,
            )

        # Custom registered types
        if type_key in cls._registry:
            klass = cls._registry[type_key]
            return klass(**{**config, **extras})  # type: ignore[arg-type]

        raise PolicyInvalidError(f"Unknown policy type: {type_key!r}")

    @classmethod
    def load_many(
        cls,
        configs: list[dict[str, Any]],
        **extras: Any,
    ) -> list[GovernancePolicy]:
        """Load multiple policies from a list of config dicts."""
        return [cls.load(c, **extras) for c in configs]
