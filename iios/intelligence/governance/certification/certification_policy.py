"""
iios/intelligence/governance/certification/certification_policy.py
==================================================================
Abstract CertificationPolicy and built-in concrete implementations.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..quality_constants import (
    ApprovalStatus,
    IntelligenceType,
    MIN_CERTIFIABLE_SCORE,
)
from ..quality_result import QualityRecord


class CertificationPolicy(ABC):
    """
    Abstract base for certification policies.
    Every concrete policy implements ``check()`` and exposes a ``name``.
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def check(self, record: QualityRecord) -> tuple[bool, str]:
        """
        Returns
        -------
        (passed, reason)
            passed : True  → policy satisfied
            reason : human-readable explanation
        """
        ...


# ── Built-in policies ─────────────────────────────────────────────────────────

class MinQualityPolicy(CertificationPolicy):
    """Passes when quality_score ≥ threshold."""

    def __init__(self, threshold: float = MIN_CERTIFIABLE_SCORE) -> None:
        self._threshold = threshold

    @property
    def name(self) -> str:
        return f"min_quality:{self._threshold:.2f}"

    def check(self, record: QualityRecord) -> tuple[bool, str]:
        passed = record.quality_score >= self._threshold
        reason = (
            f"score {record.quality_score:.4f} {'≥' if passed else '<'} "
            f"threshold {self._threshold:.2f}"
        )
        return passed, reason


class ApprovalRequiredPolicy(CertificationPolicy):
    """
    Passes only when the record has already been approved.
    Ensures approval precedes certification.
    """

    @property
    def name(self) -> str:
        return "approval_required"

    def check(self, record: QualityRecord) -> tuple[bool, str]:
        passed = record.approval_status == ApprovalStatus.APPROVED
        reason = (
            "record is APPROVED"
            if passed
            else f"record status is {record.approval_status.value}, not APPROVED"
        )
        return passed, reason


class TypeAllowlistPolicy(CertificationPolicy):
    """Passes only if the product's IntelligenceType is in the allowlist."""

    def __init__(self, allowed: list[IntelligenceType]) -> None:
        self._allowed: frozenset[IntelligenceType] = frozenset(allowed)

    @property
    def name(self) -> str:
        names = ",".join(sorted(t.value for t in self._allowed))
        return f"type_allowlist:[{names}]"

    def check(self, record: QualityRecord) -> tuple[bool, str]:
        passed = record.product_type in self._allowed
        reason = (
            f"{record.product_type.value} is in allowlist"
            if passed
            else f"{record.product_type.value} not in allowlist {[t.value for t in self._allowed]}"
        )
        return passed, reason


class NoRejectionReasonsPolicy(CertificationPolicy):
    """Fails if the record carries any hard rejection reason."""

    @property
    def name(self) -> str:
        return "no_rejection_reasons"

    def check(self, record: QualityRecord) -> tuple[bool, str]:
        passed = len(record.rejection_reasons) == 0
        reason = (
            "no rejection reasons"
            if passed
            else f"{len(record.rejection_reasons)} rejection reason(s): {record.rejection_reasons[:2]}"
        )
        return passed, reason
