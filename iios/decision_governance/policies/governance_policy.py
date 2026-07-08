"""iios/decision_governance/policies/governance_policy.py

Abstract governance policy + built-in concrete implementations.
All domain-specific policy logic must be injected via subclassing or
the predicate-based factories — never hardcoded here.
"""
from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable

from iios.decision_governance.governance_constants import (
    PolicyType,
    PolicyViolationSeverity,
)
from iios.decision_governance.governance_context import GovernanceSubject


# ─────────────────────────────────────────────────────────────────────────────
# PolicyViolation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PolicyViolation:
    """A single policy violation record."""

    violation_id:  str                    = field(default_factory=lambda: str(uuid.uuid4()))
    policy_id:     str                    = ""
    policy_name:   str                    = ""
    severity:      PolicyViolationSeverity = PolicyViolationSeverity.ERROR
    message:       str                    = ""
    is_blocking:   bool                   = True  # True → blocks approval in STRICT mode
    metadata:      dict                   = field(default_factory=dict)
    timestamp:     float                  = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "violation_id": self.violation_id,
            "policy_id":    self.policy_id,
            "policy_name":  self.policy_name,
            "severity":     self.severity.value,
            "message":      self.message,
            "is_blocking":  self.is_blocking,
            "metadata":     self.metadata,
            "timestamp":    self.timestamp,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Abstract base
# ─────────────────────────────────────────────────────────────────────────────

class GovernancePolicy(ABC):
    """Abstract base for all governance policies."""

    @property
    @abstractmethod
    def policy_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def policy_type(self) -> PolicyType:
        return PolicyType.GOVERNANCE

    @property
    def tags(self) -> list[str]:
        return []

    @property
    def is_blocking(self) -> bool:
        """Whether a violation from this policy blocks approval in STRICT mode."""
        return True

    @abstractmethod
    def validate(self, subject: GovernanceSubject) -> PolicyViolation | None:
        """Return a PolicyViolation if validation fails, None if it passes."""

    def to_dict(self) -> dict:
        return {
            "policy_id":   self.policy_id,
            "name":        self.name,
            "policy_type": self.policy_type.value,
            "is_blocking": self.is_blocking,
            "tags":        self.tags,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Concrete implementations
# ─────────────────────────────────────────────────────────────────────────────

class ScoreThresholdPolicy(GovernancePolicy):
    """Passes only subjects whose score meets a minimum threshold."""

    def __init__(
        self,
        policy_id: str,
        name: str,
        threshold: float,
        severity: PolicyViolationSeverity = PolicyViolationSeverity.ERROR,
        policy_type: PolicyType = PolicyType.GOVERNANCE,
        tags: list[str] | None = None,
        blocking: bool = True,
    ) -> None:
        self._policy_id  = policy_id
        self._name       = name
        self._threshold  = threshold
        self._severity   = severity
        self._policy_type = policy_type
        self._tags       = tags or []
        self._blocking   = blocking

    @property
    def policy_id(self) -> str:
        return self._policy_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def policy_type(self) -> PolicyType:
        return self._policy_type

    @property
    def tags(self) -> list[str]:
        return self._tags

    @property
    def is_blocking(self) -> bool:
        return self._blocking

    def validate(self, subject: GovernanceSubject) -> PolicyViolation | None:
        if subject.score < self._threshold:
            return PolicyViolation(
                policy_id=self._policy_id,
                policy_name=self._name,
                severity=self._severity,
                message=(
                    f"Score {subject.score:.4f} below threshold {self._threshold:.4f}"
                ),
                is_blocking=self._blocking,
            )
        return None


class PredicatePolicy(GovernancePolicy):
    """Policy driven by a user-supplied predicate function."""

    def __init__(
        self,
        policy_id: str,
        name: str,
        predicate: Callable[[GovernanceSubject], bool],
        violation_message: str = "Predicate check failed",
        severity: PolicyViolationSeverity = PolicyViolationSeverity.ERROR,
        policy_type: PolicyType = PolicyType.GOVERNANCE,
        tags: list[str] | None = None,
        blocking: bool = True,
    ) -> None:
        self._policy_id  = policy_id
        self._name       = name
        self._predicate  = predicate
        self._message    = violation_message
        self._severity   = severity
        self._policy_type = policy_type
        self._tags       = tags or []
        self._blocking   = blocking

    @property
    def policy_id(self) -> str:
        return self._policy_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def policy_type(self) -> PolicyType:
        return self._policy_type

    @property
    def tags(self) -> list[str]:
        return self._tags

    @property
    def is_blocking(self) -> bool:
        return self._blocking

    def validate(self, subject: GovernanceSubject) -> PolicyViolation | None:
        try:
            passed = bool(self._predicate(subject))
        except Exception:  # noqa: BLE001
            passed = False
        if not passed:
            return PolicyViolation(
                policy_id=self._policy_id,
                policy_name=self._name,
                severity=self._severity,
                message=self._message,
                is_blocking=self._blocking,
            )
        return None


class CompositePolicy(GovernancePolicy):
    """Aggregates multiple sub-policies. Fails if any sub-policy fails."""

    def __init__(
        self,
        policy_id: str,
        name: str,
        sub_policies: list[GovernancePolicy],
        policy_type: PolicyType = PolicyType.GOVERNANCE,
        tags: list[str] | None = None,
        blocking: bool = True,
    ) -> None:
        self._policy_id   = policy_id
        self._name        = name
        self._sub_policies = sub_policies
        self._policy_type  = policy_type
        self._tags         = tags or []
        self._blocking     = blocking

    @property
    def policy_id(self) -> str:
        return self._policy_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def policy_type(self) -> PolicyType:
        return self._policy_type

    @property
    def tags(self) -> list[str]:
        return self._tags

    @property
    def is_blocking(self) -> bool:
        return self._blocking

    def validate(self, subject: GovernanceSubject) -> PolicyViolation | None:
        for sp in self._sub_policies:
            violation = sp.validate(subject)
            if violation is not None:
                # Surface first failure with composite identity
                return PolicyViolation(
                    policy_id=self._policy_id,
                    policy_name=self._name,
                    severity=violation.severity,
                    message=f"[sub:{sp.policy_id}] {violation.message}",
                    is_blocking=self._blocking,
                )
        return None
