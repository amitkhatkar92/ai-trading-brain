"""
risk_governance.py -- iios.ai.governance.risk
==============================================
:class:`RiskCategory`          — risk taxonomy.
:class:`RiskThreshold`         — immutable threshold definition.
:class:`RiskPolicy`            — immutable risk governance policy.
:class:`RiskViolation`         — immutable record of a risk threshold breach.
:class:`GovernanceRiskManager` — thread-safe risk evaluation engine.

A8 AI Governance Platform — Phase 3, Module 8
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Tuple

from ..core.governance_metadata import GovernanceSeverity
from ..exceptions.governance_exceptions import (
    AIEscalationRequiredError,
    AIRiskPolicyNotFoundError,
    AIRiskThresholdExceededError,
)


class RiskCategory(str, Enum):
    """Classification of AI risk types."""
    SAFETY      = "safety"
    SECURITY    = "security"
    PRIVACY     = "privacy"
    RELIABILITY = "reliability"
    FAIRNESS    = "fairness"
    FINANCIAL   = "financial"
    OPERATIONAL = "operational"
    REPUTATIONAL = "reputational"


@dataclass(frozen=True)
class RiskThreshold:
    """Immutable threshold definition for a named risk metric."""

    threshold_id:    str
    name:            str
    category:        RiskCategory
    metric_key:      str          # key in risk context dict
    max_value:       float        # values above this breach the threshold
    severity:        GovernanceSeverity
    requires_escalation: bool
    description:     str

    @classmethod
    def create(
        cls,
        name:                str,
        category:            RiskCategory,
        metric_key:          str,
        max_value:           float,
        severity:            GovernanceSeverity = GovernanceSeverity.HIGH,
        requires_escalation: bool              = False,
        description:         str               = "",
    ) -> "RiskThreshold":
        return cls(
            threshold_id         = str(uuid.uuid4()),
            name                 = name,
            category             = category,
            metric_key           = metric_key,
            max_value            = max_value,
            severity             = severity,
            requires_escalation  = requires_escalation,
            description          = description,
        )

    def is_exceeded(self, value: float) -> bool:
        return value > self.max_value


@dataclass(frozen=True)
class RiskPolicy:
    """
    Immutable risk governance policy.

    Associates a set of :class:`RiskThreshold` objects with response actions.
    """

    policy_id:   str
    name:        str
    category:    RiskCategory
    thresholds:  FrozenSet[RiskThreshold]
    auto_block:  bool    # if True, exceeding any threshold blocks the action
    description: str
    created_at:  float

    @classmethod
    def create(
        cls,
        name:        str,
        category:    RiskCategory,
        thresholds:  FrozenSet[RiskThreshold] = frozenset(),
        auto_block:  bool = True,
        description: str  = "",
    ) -> "RiskPolicy":
        return cls(
            policy_id   = str(uuid.uuid4()),
            name        = name,
            category    = category,
            thresholds  = frozenset(thresholds),
            auto_block  = auto_block,
            description = description,
            created_at  = time.time(),
        )


@dataclass(frozen=True)
class RiskViolation:
    """Immutable record of a risk threshold breach."""

    violation_id:    str
    threshold_id:    str
    threshold_name:  str
    subject_id:      str
    metric_key:      str
    actual_value:    float
    threshold_value: float
    severity:        GovernanceSeverity
    occurred_at:     float
    notes:           str

    @classmethod
    def create(
        cls,
        threshold:    RiskThreshold,
        subject_id:   str,
        actual_value: float,
        notes:        str = "",
    ) -> "RiskViolation":
        return cls(
            violation_id    = str(uuid.uuid4()),
            threshold_id    = threshold.threshold_id,
            threshold_name  = threshold.name,
            subject_id      = subject_id,
            metric_key      = threshold.metric_key,
            actual_value    = actual_value,
            threshold_value = threshold.max_value,
            severity        = threshold.severity,
            occurred_at     = time.time(),
            notes           = notes,
        )


class GovernanceRiskManager:
    """
    Thread-safe risk governance engine.

    Evaluates a risk context dict against registered :class:`RiskPolicy` objects
    and produces :class:`RiskViolation` records.
    """

    def __init__(self) -> None:
        self._lock:      threading.Lock           = threading.Lock()
        self._policies:  Dict[str, RiskPolicy]    = {}
        self._violations: List[RiskViolation]     = []

    # ── policy management ─────────────────────────────────────────────────────

    def add_policy(self, policy: RiskPolicy) -> None:
        with self._lock:
            self._policies[policy.policy_id] = policy

    def remove_policy(self, policy_id: str) -> None:
        with self._lock:
            self._policies.pop(policy_id, None)

    def get_policy(self, policy_id: str) -> RiskPolicy:
        with self._lock:
            p = self._policies.get(policy_id)
        if p is None:
            raise AIRiskPolicyNotFoundError(f"Risk policy {policy_id!r} not found")
        return p

    def list_policies(self) -> List[RiskPolicy]:
        with self._lock:
            return list(self._policies.values())

    # ── evaluation ────────────────────────────────────────────────────────────

    def evaluate(
        self,
        subject_id:    str,
        risk_context:  Dict[str, float],
        raise_on_exceed: bool = False,
        raise_on_escalation: bool = False,
    ) -> List[RiskViolation]:
        """
        Evaluate ``risk_context`` against all registered risk policies.

        :param risk_context: dict of ``{metric_key: value}``.
        :param raise_on_exceed: raise :class:`AIRiskThresholdExceededError` on first violation.
        :param raise_on_escalation: raise :class:`AIEscalationRequiredError` on escalation-required breach.
        :returns: list of :class:`RiskViolation` objects (empty if all pass).
        """
        with self._lock:
            policies = list(self._policies.values())

        new_violations: List[RiskViolation] = []
        for policy in policies:
            for threshold in policy.thresholds:
                value = risk_context.get(threshold.metric_key)
                if value is None:
                    continue
                if threshold.is_exceeded(value):
                    v = RiskViolation.create(threshold, subject_id, value)
                    new_violations.append(v)

        if new_violations:
            with self._lock:
                self._violations.extend(new_violations)

            escalation_required = any(
                v.severity in (GovernanceSeverity.HIGH, GovernanceSeverity.CRITICAL)
                for v in new_violations
            )
            if raise_on_escalation and escalation_required:
                names = [v.threshold_name for v in new_violations]
                raise AIEscalationRequiredError(
                    f"Escalation required for {subject_id!r}: {names}"
                )
            if raise_on_exceed:
                names = [v.threshold_name for v in new_violations]
                raise AIRiskThresholdExceededError(
                    f"Risk thresholds exceeded for {subject_id!r}: {names}"
                )

        return new_violations

    # ── history ───────────────────────────────────────────────────────────────

    def violations(
        self,
        subject_id: Optional[str] = None,
        limit:      int           = 500,
    ) -> List[RiskViolation]:
        with self._lock:
            vs = list(self._violations)
        if subject_id:
            vs = [v for v in vs if v.subject_id == subject_id]
        return vs[-limit:]

    def violation_count(self) -> int:
        with self._lock:
            return len(self._violations)

    def clear_violations(self) -> None:
        with self._lock:
            self._violations.clear()
