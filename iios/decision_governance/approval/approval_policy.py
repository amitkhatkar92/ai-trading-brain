"""iios/decision_governance/approval/approval_policy.py

Abstract ApprovalPolicy + built-in concrete implementations.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Callable

from iios.decision_governance.governance_constants import (
    ApprovalLevel,
    ApprovalMode,
    ApprovalStatus,
    DEFAULT_APPROVAL_TTL_SEC,
)
from iios.decision_governance.governance_context import GovernanceSubject
from iios.decision_governance.approval.approval_result import ApprovalRecord


class ApprovalPolicy(ABC):
    """Abstract base for all approval policies."""

    @property
    @abstractmethod
    def policy_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def level(self) -> ApprovalLevel:
        return ApprovalLevel.AUTO

    @property
    def mode(self) -> ApprovalMode:
        return ApprovalMode.AUTOMATIC

    @property
    def ttl_seconds(self) -> float:
        return DEFAULT_APPROVAL_TTL_SEC

    @abstractmethod
    def evaluate(self, subject: GovernanceSubject) -> ApprovalRecord:
        """Evaluate the subject and return an ApprovalRecord."""

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "name":      self.name,
            "level":     self.level.value,
            "mode":      self.mode.value,
        }

    def _make_record(
        self,
        subject: GovernanceSubject,
        status: ApprovalStatus,
        reason: str = "",
        approver: str = "system",
    ) -> ApprovalRecord:
        return ApprovalRecord(
            decision_id=subject.decision_id,
            policy_id=self.policy_id,
            policy_name=self.name,
            level=self.level,
            mode=self.mode,
            status=status,
            approver=approver,
            reason=reason,
            expires_at=time.time() + self.ttl_seconds if self.ttl_seconds > 0 else None,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Built-in implementations
# ─────────────────────────────────────────────────────────────────────────────

class AutoApprovalPolicy(ApprovalPolicy):
    """Always approves automatically. Use for low-risk or already-validated subjects."""

    def __init__(
        self,
        policy_id: str,
        name: str,
        ttl_seconds: float = DEFAULT_APPROVAL_TTL_SEC,
    ) -> None:
        self._policy_id  = policy_id
        self._name       = name
        self._ttl        = ttl_seconds

    @property
    def policy_id(self) -> str:
        return self._policy_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def mode(self) -> ApprovalMode:
        return ApprovalMode.AUTOMATIC

    @property
    def ttl_seconds(self) -> float:
        return self._ttl

    def evaluate(self, subject: GovernanceSubject) -> ApprovalRecord:
        return self._make_record(subject, ApprovalStatus.APPROVED, "Auto-approved")


class ScoreThresholdApprovalPolicy(ApprovalPolicy):
    """Approves if subject.score >= threshold, rejects otherwise."""

    def __init__(
        self,
        policy_id: str,
        name: str,
        threshold: float,
        ttl_seconds: float = DEFAULT_APPROVAL_TTL_SEC,
    ) -> None:
        self._policy_id  = policy_id
        self._name       = name
        self._threshold  = threshold
        self._ttl        = ttl_seconds

    @property
    def policy_id(self) -> str:
        return self._policy_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def level(self) -> ApprovalLevel:
        return ApprovalLevel.SINGLE

    @property
    def mode(self) -> ApprovalMode:
        return ApprovalMode.CONDITIONAL

    @property
    def ttl_seconds(self) -> float:
        return self._ttl

    def evaluate(self, subject: GovernanceSubject) -> ApprovalRecord:
        if subject.score >= self._threshold:
            return self._make_record(
                subject,
                ApprovalStatus.APPROVED,
                f"Score {subject.score:.4f} >= threshold {self._threshold:.4f}",
            )
        return self._make_record(
            subject,
            ApprovalStatus.REJECTED,
            f"Score {subject.score:.4f} < threshold {self._threshold:.4f}",
        )


class ConditionalApprovalPolicy(ApprovalPolicy):
    """Approval driven by a user-supplied predicate."""

    def __init__(
        self,
        policy_id: str,
        name: str,
        predicate: Callable[[GovernanceSubject], bool],
        reject_reason: str = "Condition not met",
        ttl_seconds: float = DEFAULT_APPROVAL_TTL_SEC,
    ) -> None:
        self._policy_id    = policy_id
        self._name         = name
        self._predicate    = predicate
        self._reject_reason = reject_reason
        self._ttl          = ttl_seconds

    @property
    def policy_id(self) -> str:
        return self._policy_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def level(self) -> ApprovalLevel:
        return ApprovalLevel.SINGLE

    @property
    def mode(self) -> ApprovalMode:
        return ApprovalMode.CONDITIONAL

    @property
    def ttl_seconds(self) -> float:
        return self._ttl

    def evaluate(self, subject: GovernanceSubject) -> ApprovalRecord:
        try:
            passed = bool(self._predicate(subject))
        except Exception:  # noqa: BLE001
            passed = False
        if passed:
            return self._make_record(subject, ApprovalStatus.APPROVED, "Condition met")
        return self._make_record(subject, ApprovalStatus.REJECTED, self._reject_reason)


class EscalationApprovalPolicy(ApprovalPolicy):
    """Always escalates — forces manual review."""

    def __init__(
        self,
        policy_id: str,
        name: str,
        escalation_reason: str = "Manual review required",
        ttl_seconds: float = DEFAULT_APPROVAL_TTL_SEC,
    ) -> None:
        self._policy_id = policy_id
        self._name      = name
        self._reason    = escalation_reason
        self._ttl       = ttl_seconds

    @property
    def policy_id(self) -> str:
        return self._policy_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def level(self) -> ApprovalLevel:
        return ApprovalLevel.ESCALATION

    @property
    def mode(self) -> ApprovalMode:
        return ApprovalMode.MANUAL

    @property
    def ttl_seconds(self) -> float:
        return self._ttl

    def evaluate(self, subject: GovernanceSubject) -> ApprovalRecord:
        return self._make_record(
            subject, ApprovalStatus.ESCALATED, self._reason, approver="escalation"
        )
