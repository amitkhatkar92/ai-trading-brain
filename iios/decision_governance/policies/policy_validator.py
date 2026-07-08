"""iios/decision_governance/policies/policy_validator.py

Validates that a GovernancePolicy is well-formed before registration.
"""
from __future__ import annotations

from iios.decision_governance.governance_exceptions import PolicyInvalidError
from iios.decision_governance.policies.governance_policy import GovernancePolicy


class PolicyValidator:
    """Validates a GovernancePolicy is structurally correct."""

    def validate(self, policy: GovernancePolicy) -> None:
        """Raise PolicyInvalidError if the policy is malformed."""
        if not isinstance(policy, GovernancePolicy):
            raise PolicyInvalidError(
                f"Object is not a GovernancePolicy: {type(policy)!r}",
            )
        if not policy.policy_id or not isinstance(policy.policy_id, str):
            raise PolicyInvalidError("policy_id must be a non-empty string")
        if not policy.name or not isinstance(policy.name, str):
            raise PolicyInvalidError("name must be a non-empty string")
        # tags must be a list of strings (if provided)
        if not isinstance(policy.tags, list):
            raise PolicyInvalidError("tags must be a list")

    def is_valid(self, policy: GovernancePolicy) -> bool:
        """Return True if valid, False otherwise."""
        try:
            self.validate(policy)
            return True
        except PolicyInvalidError:
            return False
